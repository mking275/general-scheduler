"""IdentityService — the identity flows (FR-001/006/007/008/011/012/015).

All cross-tenant lookups by unique key (login, refresh, invite acceptance) run in
the broker posture and ONLY there; every other operation runs strictly tenant-
scoped. Every mutation is audited. The broker context (``_broker_context``) is
entered by exactly three methods — ``exchange_external_token``, ``refresh``, and
``accept_invitation`` — which is asserted by a test (D1/R1).
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional

from . import roles as roles_mod
from .audit import AuditLog
from .errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from .models import (
    AuditRecord,
    Invitation,
    RefreshToken,
    SessionPair,
    SupportAssignment,
    Tenant,
    User,
    VerifiedIdentity,
)
from .settings import IdentitySettings
from .tenancy import _broker_context, tenant_context
from .tokens import (
    REFRESH,
    TokenError,
    hash_refresh_token,
    mint_access_token,
    mint_refresh_token,
    verify_token,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class IdentityService:
    """Orchestrates identity flows over a :class:`Store` and pluggable ports."""

    def __init__(
        self,
        store,
        provider,
        settings: IdentitySettings,
        *,
        invite_delivery=None,
        entitlements_hook=None,
        product_hooks=None,
    ) -> None:
        self.store = store
        self.provider = provider
        self.settings = settings
        self.invite_delivery = invite_delivery
        self.entitlements_hook = entitlements_hook
        self.product_hooks = product_hooks
        self.audit = AuditLog(store)
        # In-memory, per-process escape-hatch limiter (D8; documented limitation).
        self._escape_attempts: Dict[str, List[float]] = defaultdict(list)

    # ── helpers ────────────────────────────────────────────────────────────

    def _tenant_ctx(self, conn, *, user_role: str, tenant_key: Optional[str],
                    user_id: Optional[str] = None, cs_admin_scope: Optional[List[str]] = None):
        return tenant_context(
            conn, role=self.settings.app_role, tenant_key=tenant_key,
            user_role=user_role, user_id=user_id, cs_admin_scope=cs_admin_scope,
        )

    def _broker_ctx(self, conn):
        return _broker_context(conn, role=self.settings.auth_role)

    async def _resolve_entitlements(self, user: User, tenant: Optional[Tenant]) -> Dict[str, Any]:
        if self.entitlements_hook is None:
            return {}
        return dict(await self.entitlements_hook.resolve(user, tenant))

    async def _scope_for(self, conn, user: User) -> List[str]:
        """Support scope for a cs_admin; empty for everyone else (superuser=any)."""
        if user.role == roles_mod.CS_ADMIN:
            return await self.store.get_support_scope(conn, user.id)
        return []

    async def _build_session(
        self, conn, user: User, tenant: Optional[Tenant], cs_admin_scope: List[str],
        *, entitlements: Optional[Mapping[str, Any]] = None, audit_sign_in: bool = True,
    ) -> SessionPair:
        """Mint the internal pair, persist the hashed refresh, optionally audit."""
        if entitlements is None:
            entitlements = await self._resolve_entitlements(user, tenant)
        access = mint_access_token(
            self.settings, user_id=str(user.id), email=user.email, role=user.role,
            customer_id=user.tenant_key, customer_name=(tenant.display_name if tenant else None),
            customer_role=user.customer_role, cs_admin_scope=cs_admin_scope, entitlements=entitlements,
        )
        refresh, _jti = mint_refresh_token(self.settings, user_id=str(user.id))
        await self.store.store_refresh_token(conn, RefreshToken(
            user_id=user.id, tenant_key=user.tenant_key, token_hash=hash_refresh_token(refresh),
            expires_at=_now() + timedelta(days=self.settings.refresh_token_ttl_days),
        ))
        if audit_sign_in:
            await self.audit.record(conn, AuditRecord(
                action="sign_in", actor_user_id=user.id, target_user_id=user.id,
                target_tenant_key=user.tenant_key,
            ))
        return SessionPair(
            access_token=access, refresh_token=refresh, user=user, cs_admin_scope=cs_admin_scope,
        )

    async def _verify_external(self, external_token: str) -> VerifiedIdentity:
        try:
            return await self.provider.verify_external_token(external_token)
        except Exception as exc:  # provider-agnostic → 401
            raise AuthenticationError("external token invalid or expired") from exc

    # ── broker flow #1: IdP exchange ─────────────────────────────────────────

    async def exchange_external_token(
        self, external_token: str, *, invitation_id: Optional[str] = None,
    ) -> SessionPair:
        """Verify an external credential and return an internal session (FR-001).

        Handles seed-superuser bootstrap, invitation acceptance, domain-allowlist
        auto-provision, first-user→account_owner, suspended→403, and IdP-identity
        collision→409, mirroring the FA2 exchange semantics.
        """
        identity = await self._verify_external(external_token)
        async with self.store.acquire() as conn:
            async with self._broker_ctx(conn):
                return await self._do_exchange(conn, identity, invitation_id)

    async def _do_exchange(
        self, conn, identity: VerifiedIdentity, invitation_id: Optional[str],
    ) -> SessionPair:
        existing = await self.store.get_user_by_provider_uid(conn, identity.provider_uid)
        if existing is None:
            by_email = await self.store.get_user_by_email(conn, identity.email)
            if by_email is not None:
                if by_email.provider_uid and by_email.provider_uid != identity.provider_uid:
                    raise ConflictError("identity unavailable")
                existing = by_email

        if existing and existing.status == "suspended":
            raise ForbiddenError("Account suspended")

        if existing is None:
            # (a) seed-superuser bootstrap
            seed = (self.settings.seed_superuser_email or "").lower()
            if seed and identity.email.lower() == seed and await self.store.count_superusers(conn) == 0:
                user = await self._provision_user(
                    conn, identity, role=roles_mod.SUPERUSER, tenant_key=None,
                    customer_role=roles_mod.MEMBER,
                )
                return await self._build_session(conn, user, None, [])
            # (b) explicit invitation
            if invitation_id:
                return await self._accept_within(conn, identity, uuid.UUID(str(invitation_id)))
            # (c) pending invitation matched by email
            pending = await self.store.get_pending_invitation_by_email(conn, identity.email)
            if pending is not None:
                return await self._accept_within(conn, identity, pending.id)
            # (d) domain-allowlist auto-provision at the default role
            domain = identity.email.split("@", 1)[1].lower() if "@" in identity.email else ""
            tenant = await self.store.get_tenant_by_domain(conn, domain) if domain else None
            if tenant is None:
                raise ForbiddenError("Email domain not authorized for this application")
            count = await self.store.count_users_in_tenant(conn, tenant.key)
            customer_role = roles_mod.ACCOUNT_OWNER if count == 0 else roles_mod.MEMBER
            user = await self._provision_user(
                conn, identity, role=roles_mod.VIEWER, tenant_key=tenant.key,
                customer_role=customer_role,
            )
            return await self._build_session(conn, user, tenant, [])

        # existing user
        if existing.status == "invited":
            existing = await self.store.update_user(
                conn, existing.id, status="active", provider_uid=identity.provider_uid,
                display_name=identity.display_name or existing.display_name,
                provider=identity.provider, last_sign_in_at=_now(),
            )
            pending = await self.store.get_pending_invitation_by_email(conn, identity.email)
            if pending is not None:
                await self.store.update_invitation(
                    conn, pending.id, status="accepted", accepted_at=_now(),
                )
        else:
            updates: Dict[str, Any] = {"last_sign_in_at": _now()}
            if not existing.provider_uid:
                updates["provider_uid"] = identity.provider_uid
                updates["provider"] = identity.provider
            existing = await self.store.update_user(conn, existing.id, **updates)

        tenant = await self.store.get_tenant(conn, existing.tenant_key) if existing.tenant_key else None
        scope = await self._scope_for(conn, existing)
        return await self._build_session(conn, existing, tenant, scope)

    async def _provision_user(
        self, conn, identity: VerifiedIdentity, *, role: str, tenant_key: Optional[str],
        customer_role: str, status: str = "active",
    ) -> User:
        user = await self.store.create_user(conn, User(
            provider_uid=identity.provider_uid, email=identity.email.lower(),
            display_name=identity.display_name, role=role, customer_role=customer_role,
            status=status, provider=identity.provider, tenant_key=tenant_key,
            last_sign_in_at=_now(),
        ))
        if self.product_hooks is not None:
            await self.product_hooks.on_user_provisioned(user)
        return user

    # ── broker flow #2: invitation acceptance ───────────────────────────────

    async def accept_invitation(self, external_token: str, invitation_id: str) -> SessionPair:
        """Accept an invitation: bind the IdP identity and activate the account."""
        identity = await self._verify_external(external_token)
        async with self.store.acquire() as conn:
            async with self._broker_ctx(conn):
                return await self._accept_within(conn, identity, uuid.UUID(str(invitation_id)))

    async def _accept_within(
        self, conn, identity: VerifiedIdentity, invitation_id: uuid.UUID,
    ) -> SessionPair:
        inv = await self.store.get_invitation(conn, invitation_id)
        if inv is None or inv.status != "pending":
            raise NotFoundError("Invitation not found or already used")
        if inv.expires_at is not None and inv.expires_at < _now():
            await self.store.update_invitation(conn, inv.id, status="expired")
            raise NotFoundError("Invitation has expired")
        if inv.email.lower() != identity.email.lower():
            raise ForbiddenError("Invitation email does not match authenticated email")

        user = await self.store.get_user_by_email(conn, identity.email)
        if user is not None:
            if user.provider_uid and user.provider_uid != identity.provider_uid:
                raise ConflictError("identity unavailable")
            user = await self.store.update_user(
                conn, user.id, status="active", provider_uid=identity.provider_uid,
                display_name=identity.display_name or user.display_name,
                provider=identity.provider, role=inv.role, tenant_key=inv.tenant_key,
                last_sign_in_at=_now(),
            )
        else:
            count = (
                await self.store.count_users_in_tenant(conn, inv.tenant_key)
                if inv.tenant_key else 1
            )
            customer_role = roles_mod.ACCOUNT_OWNER if count == 0 else roles_mod.MEMBER
            user = await self._provision_user(
                conn, identity, role=inv.role, tenant_key=inv.tenant_key,
                customer_role=customer_role,
            )

        await self.store.update_invitation(conn, inv.id, status="accepted", accepted_at=_now())
        await self.audit.record(conn, AuditRecord(
            action="accept", actor_user_id=user.id, target_user_id=user.id,
            target_tenant_key=inv.tenant_key,
        ))
        tenant = await self.store.get_tenant(conn, user.tenant_key) if user.tenant_key else None
        scope = await self._scope_for(conn, user)
        return await self._build_session(conn, user, tenant, scope)

    # ── broker flow #3: refresh (rotating) ───────────────────────────────────

    async def refresh(self, refresh_token: str) -> SessionPair:
        """Rotate a refresh token into a new session pair (FR-012).

        Rotation is atomic: the presented token is revoked under a live-only
        predicate, so N concurrent refreshes yield exactly one new session — the
        losers are rejected, never duplicated.
        """
        try:
            payload = verify_token(self.settings, refresh_token, expected_type=REFRESH)
        except TokenError as exc:
            raise AuthenticationError("invalid or expired refresh token") from exc

        token_hash = hash_refresh_token(refresh_token)
        async with self.store.acquire() as conn:
            async with self._broker_ctx(conn):
                stored = await self.store.get_refresh_token_by_hash(conn, token_hash)
                if stored is None or stored.revoked_at is not None or stored.expires_at < _now():
                    raise AuthenticationError("refresh token has been revoked")
                user = await self.store.get_user_by_id(conn, uuid.UUID(str(payload["sub"])))
                if user is None:
                    raise AuthenticationError("user not found")
                if user.status == "suspended":
                    raise ForbiddenError("Account suspended")
                won = await self.store.revoke_refresh_token_by_hash(conn, token_hash)
                if not won:
                    raise AuthenticationError("refresh token has been revoked")
                tenant = await self.store.get_tenant(conn, user.tenant_key) if user.tenant_key else None
                scope = await self._scope_for(conn, user)
                return await self._build_session(conn, user, tenant, scope, audit_sign_in=False)

    # ── session teardown ─────────────────────────────────────────────────────

    async def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token server-side; idempotent (FR-012)."""
        try:
            payload = verify_token(self.settings, refresh_token, expected_type=REFRESH)
        except TokenError:
            return  # unknown/invalid token — logout is idempotent
        user_id = str(payload["sub"])
        token_hash = hash_refresh_token(refresh_token)
        async with self.store.acquire() as conn:
            async with self._tenant_ctx(conn, user_role="", tenant_key=None, user_id=user_id):
                revoked = await self.store.revoke_refresh_token_by_hash(conn, token_hash)
                if revoked:
                    await self.audit.record(conn, AuditRecord(
                        action="sign_out", actor_user_id=uuid.UUID(user_id),
                        target_user_id=uuid.UUID(user_id),
                    ))

    # ── admin: invitations ───────────────────────────────────────────────────

    async def invite(
        self, actor: Mapping[str, Any], *, email: str, role: str, tenant_key: str,
    ) -> Invitation:
        """Create and deliver an invitation (FR-006); enforces the rank ceiling."""
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        if not roles_mod.can_grant_role(actor.get("role", ""), role):
            raise ForbiddenError("cannot invite at or above your own rank")
        self._require_tenant_in_scope(actor, tenant_key)
        email = email.lower()

        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                existing = await self.store.get_user_by_email(conn, email)
                if existing is not None and existing.status == "active":
                    raise ConflictError("a user with this email already exists")
                inv = await self.store.create_invitation(conn, Invitation(
                    email=email, role=role, tenant_key=tenant_key,
                    invited_by=self._actor_id(actor),
                    expires_at=_now() + timedelta(days=self.settings.invite_expiry_days),
                ))
                if existing is None:
                    await self.store.create_user(conn, User(
                        email=email, role=role, customer_role=roles_mod.MEMBER,
                        status="invited", tenant_key=tenant_key, provider="google",
                    ))
                await self.audit.record(conn, AuditRecord(
                    action="invite", actor_user_id=self._actor_id(actor),
                    target_tenant_key=tenant_key, after_state={"email": email, "role": role},
                ))
        await self._deliver_invite(inv)
        return inv

    async def resend_invitation(self, actor: Mapping[str, Any], invitation_id: str) -> Invitation:
        """Extend an invitation's expiry and re-deliver it (FR-006)."""
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                inv = await self.store.get_invitation(conn, uuid.UUID(str(invitation_id)))
                if inv is None or inv.status != "pending":
                    raise NotFoundError("no pending invitation")
                self._require_tenant_in_scope(actor, inv.tenant_key)
                inv = await self.store.update_invitation(
                    conn, inv.id,
                    expires_at=_now() + timedelta(days=self.settings.invite_expiry_days),
                )
        await self._deliver_invite(inv)
        return inv

    async def _deliver_invite(self, inv: Invitation) -> None:
        if self.invite_delivery is not None:
            await self.invite_delivery.send(
                inv.email, self.settings.accept_invite_url(str(inv.id)), inv,
            )

    async def list_invitations(
        self, actor: Mapping[str, Any], *, tenant_key: Optional[str] = None,
    ) -> List[Invitation]:
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                return await self.store.list_invitations(conn, tenant_key=tenant_key)

    # ── admin: users ─────────────────────────────────────────────────────────

    async def list_users(
        self, actor: Mapping[str, Any], *, tenant_key: Optional[str] = None,
    ) -> List[User]:
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                return await self.store.list_users(conn, tenant_key=tenant_key)

    async def patch_user(
        self, actor: Mapping[str, Any], target_user_id: str, *,
        role: Optional[str] = None, customer_role: Optional[str] = None,
    ) -> User:
        """Change a user's role/customer_role under the rank ceiling (FR-006)."""
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                target = await self.store.get_user_by_id(conn, uuid.UUID(str(target_user_id)))
                if target is None:
                    raise NotFoundError("user not found")
                self._require_outranks(actor, target.role)
                fields: Dict[str, Any] = {}
                if role is not None:
                    if not roles_mod.can_grant_role(actor.get("role", ""), role):
                        raise ForbiddenError("cannot assign at or above your own rank")
                    fields["role"] = role
                if customer_role is not None:
                    fields["customer_role"] = customer_role
                if not fields:
                    return target
                before = {"role": target.role, "customer_role": target.customer_role}
                updated = await self.store.update_user(conn, target.id, **fields)
                await self.audit.record(conn, AuditRecord(
                    action="role_change", actor_user_id=self._actor_id(actor),
                    target_user_id=target.id, target_tenant_key=target.tenant_key,
                    before_state=before, after_state=fields,
                ))
                return updated

    async def suspend(self, actor: Mapping[str, Any], target_user_id: str) -> User:
        """Suspend a user: block new sessions + revoke internal & provider sessions."""
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                target = await self.store.get_user_by_id(conn, uuid.UUID(str(target_user_id)))
                if target is None:
                    raise NotFoundError("user not found")
                self._require_outranks(actor, target.role)
                updated = await self.store.update_user(conn, target.id, status="suspended")
                await self.store.revoke_all_user_refresh_tokens(conn, target.id)
                await self.audit.record(conn, AuditRecord(
                    action="suspend", actor_user_id=self._actor_id(actor),
                    target_user_id=target.id, target_tenant_key=target.tenant_key,
                    before_state={"status": target.status}, after_state={"status": "suspended"},
                ))
        if target.provider_uid:
            await self.provider.revoke_sessions(target.provider_uid)
        return updated

    async def reactivate(self, actor: Mapping[str, Any], target_user_id: str) -> User:
        """Restore a suspended user's access (FR-007)."""
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                target = await self.store.get_user_by_id(conn, uuid.UUID(str(target_user_id)))
                if target is None:
                    raise NotFoundError("user not found")
                self._require_outranks(actor, target.role)
                updated = await self.store.update_user(conn, target.id, status="active")
                await self.audit.record(conn, AuditRecord(
                    action="reactivate", actor_user_id=self._actor_id(actor),
                    target_user_id=target.id, target_tenant_key=target.tenant_key,
                    before_state={"status": target.status}, after_state={"status": "active"},
                ))
                return updated

    async def read_audit(
        self, actor: Mapping[str, Any], *, target_user_id: Optional[str] = None,
        tenant_key: Optional[str] = None, limit: int = 100,
    ) -> List[AuditRecord]:
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                return await self.audit.read(
                    conn,
                    target_user_id=uuid.UUID(str(target_user_id)) if target_user_id else None,
                    target_tenant_key=tenant_key, limit=limit,
                )

    # ── admin: tenants ───────────────────────────────────────────────────────

    async def create_tenant(self, actor: Mapping[str, Any], tenant: Tenant) -> Tenant:
        """Create a tenant (superuser only)."""
        self._require_min_role(actor, roles_mod.SUPERUSER)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                created = await self.store.create_tenant(conn, tenant)
                await self.audit.record(conn, AuditRecord(
                    action="tenant_assign", actor_user_id=self._actor_id(actor),
                    target_tenant_key=created.key, after_state={"display_name": created.display_name},
                ))
                return created

    async def list_tenants(self, actor: Mapping[str, Any]) -> List[Tenant]:
        self._require_min_role(actor, roles_mod.CS_ADMIN)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                return await self.store.list_tenants(conn)

    async def assign_support(
        self, actor: Mapping[str, Any], *, user_id: str, tenant_key: str,
    ) -> None:
        """Grant a cs_admin a support assignment to a tenant (superuser only)."""
        self._require_min_role(actor, roles_mod.SUPERUSER)
        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                await self.store.add_support_assignment(conn, SupportAssignment(
                    user_id=uuid.UUID(str(user_id)), tenant_key=tenant_key,
                    assigned_by=self._actor_id(actor),
                ))
                await self.audit.record(conn, AuditRecord(
                    action="tenant_assign", actor_user_id=self._actor_id(actor),
                    target_user_id=uuid.UUID(str(user_id)), target_tenant_key=tenant_key,
                ))

    # ── support scoping & break-glass ────────────────────────────────────────

    async def switch_tenant(self, actor: Mapping[str, Any], target_tenant_key: str) -> str:
        """Re-mint an ACCESS token scoped to another tenant (FR-011).

        Enforces cs_admin scope (superuser: any); mints access only, so the
        refresh grant and its session are unchanged and a stale token keeps its
        old scope (the session-scope-binding rule).
        """
        role = actor.get("role", "")
        if not roles_mod.has_rank(role, roles_mod.CS_ADMIN):
            raise ForbiddenError("only support staff may switch tenant")
        scope = [str(c) for c in actor.get("cs_admin_scope", [])]
        if role != roles_mod.SUPERUSER and target_tenant_key not in scope:
            raise ForbiddenError("target tenant not in your support scope")

        async with self.store.acquire() as conn:
            async with self._actor_ctx(conn, actor):
                tenant = await self.store.get_tenant(conn, target_tenant_key)
                if tenant is None:
                    raise NotFoundError("tenant not found")
        return mint_access_token(
            self.settings, user_id=str(actor.get("sub")), email=actor.get("email", ""),
            role=role, customer_id=target_tenant_key, customer_name=tenant.display_name,
            customer_role=actor.get("customer_role", roles_mod.MEMBER), cs_admin_scope=scope,
            entitlements=actor.get("entitlements", {}),
        )

    async def escape_hatch_login(
        self, *, email: str, password: str, secret: str, client_ip: str = "unknown",
    ) -> SessionPair:
        """Secret-gated, rate-limited, audited superuser password path (FR-015)."""
        if not self.settings.escape_hatch_secret or secret != self.settings.escape_hatch_secret:
            raise ForbiddenError("missing or incorrect escape secret")
        self._check_escape_rate_limit(client_ip)

        from .passwords import verify_password  # local: passwords used only here
        async with self.store.acquire() as conn:
            # Superuser RLS context: the break-glass account has no tenant.
            async with self._tenant_ctx(conn, user_role=roles_mod.SUPERUSER, tenant_key=None):
                user = await self.store.get_user_by_email(conn, email.lower())
                if user is None or user.role != roles_mod.SUPERUSER or not user.password_hash:
                    raise ForbiddenError("not a superuser with password auth enabled")
                if user.status == "suspended":
                    raise ForbiddenError("Account suspended")
                if not verify_password(password, user.password_hash):
                    raise AuthenticationError("invalid credentials")
                user = await self.store.update_user(conn, user.id, last_sign_in_at=_now())
                await self.audit.record(conn, AuditRecord(
                    action="escape_hatch", actor_user_id=user.id, target_user_id=user.id,
                ))
                return await self._build_session(conn, user, None, [], audit_sign_in=False)

    def _check_escape_rate_limit(self, ip: str) -> None:
        now = time.monotonic()
        cutoff = now - self.settings.escape_hatch_window_seconds
        attempts = [t for t in self._escape_attempts[ip] if t > cutoff]
        if len(attempts) >= self.settings.escape_hatch_max_attempts:
            self._escape_attempts[ip] = attempts
            raise RateLimitError("too many escape-hatch attempts")
        attempts.append(now)
        self._escape_attempts[ip] = attempts

    # ── actor helpers ────────────────────────────────────────────────────────

    def _actor_ctx(self, conn, actor: Mapping[str, Any]):
        return self._tenant_ctx(
            conn, user_role=actor.get("role", ""), tenant_key=actor.get("customer_id"),
            user_id=(str(actor.get("sub")) if actor.get("sub") else None),
            cs_admin_scope=[str(c) for c in actor.get("cs_admin_scope", [])],
        )

    @staticmethod
    def _actor_id(actor: Mapping[str, Any]) -> Optional[uuid.UUID]:
        sub = actor.get("sub")
        return uuid.UUID(str(sub)) if sub else None

    @staticmethod
    def _require_min_role(actor: Mapping[str, Any], min_role: str) -> None:
        if not roles_mod.has_rank(actor.get("role", ""), min_role):
            raise ForbiddenError(f"requires {min_role} or higher")

    def _require_tenant_in_scope(self, actor: Mapping[str, Any], tenant_key: Optional[str]) -> None:
        if not tenant_key:
            raise ValidationError("tenant_key is required")
        role = actor.get("role", "")
        if role == roles_mod.SUPERUSER:
            return
        scope = {str(c) for c in actor.get("cs_admin_scope", [])}
        if tenant_key not in scope:
            raise ForbiddenError("tenant not in your support scope")

    @staticmethod
    def _require_outranks(actor: Mapping[str, Any], target_role: str) -> None:
        if roles_mod.rank(actor.get("role", "")) <= roles_mod.rank(target_role):
            raise ForbiddenError("cannot act on a user at or above your own rank")
