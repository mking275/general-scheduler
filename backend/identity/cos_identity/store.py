"""Persistence: ``PgStore`` (asyncpg) and ``InMemoryStore`` on one ``Store``
protocol (D7).

Every method takes an opaque ``conn`` obtained from ``store.acquire()``; for
``PgStore`` the caller must have entered a tenant/broker context on that conn
(no query runs without RLS scoping). ``InMemoryStore`` ignores ``conn`` and is
the fast unit tier — RLS is proven only against real Postgres.
"""
from __future__ import annotations

import copy
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from .models import (
    AuditRecord,
    Invitation,
    RefreshToken,
    SupportAssignment,
    Tenant,
    User,
)
from .settings import IdentitySettings

_USER_UPDATABLE = {
    "provider_uid", "email", "display_name", "role", "customer_role",
    "status", "provider", "password_hash", "tenant_key", "last_sign_in_at",
}
_INVITE_UPDATABLE = {"status", "expires_at", "accepted_at", "role"}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class Store(Protocol):
    """The persistence contract shared by the Postgres and in-memory stores."""

    def acquire(self): ...

    # tenants
    async def create_tenant(self, conn, tenant: Tenant) -> Tenant: ...
    async def get_tenant(self, conn, key: str) -> Optional[Tenant]: ...
    async def get_tenant_by_domain(self, conn, domain: str) -> Optional[Tenant]: ...
    async def list_tenants(self, conn) -> List[Tenant]: ...
    async def set_tenant_status(self, conn, key: str, status: str) -> Optional[Tenant]: ...

    # users
    async def create_user(self, conn, user: User) -> User: ...
    async def get_user_by_id(self, conn, user_id: uuid.UUID) -> Optional[User]: ...
    async def get_user_by_email(self, conn, email: str) -> Optional[User]: ...
    async def get_user_by_provider_uid(self, conn, uid: str) -> Optional[User]: ...
    async def update_user(self, conn, user_id: uuid.UUID, **fields) -> Optional[User]: ...
    async def list_users(self, conn, tenant_key: Optional[str] = None) -> List[User]: ...
    async def count_users_in_tenant(self, conn, tenant_key: str) -> int: ...
    async def count_superusers(self, conn) -> int: ...

    # invitations
    async def create_invitation(self, conn, inv: Invitation) -> Invitation: ...
    async def get_invitation(self, conn, inv_id: uuid.UUID) -> Optional[Invitation]: ...
    async def get_pending_invitation_by_email(self, conn, email: str) -> Optional[Invitation]: ...
    async def list_invitations(self, conn, tenant_key: Optional[str] = None) -> List[Invitation]: ...
    async def update_invitation(self, conn, inv_id: uuid.UUID, **fields) -> Optional[Invitation]: ...

    # refresh tokens
    async def store_refresh_token(self, conn, rt: RefreshToken) -> RefreshToken: ...
    async def get_refresh_token_by_hash(self, conn, token_hash: str) -> Optional[RefreshToken]: ...
    async def revoke_refresh_token_by_hash(self, conn, token_hash: str) -> bool: ...
    async def revoke_all_user_refresh_tokens(self, conn, user_id: uuid.UUID) -> int: ...

    # support assignments
    async def add_support_assignment(self, conn, sa: SupportAssignment) -> SupportAssignment: ...
    async def get_support_scope(self, conn, user_id: uuid.UUID) -> List[str]: ...

    # audit
    async def insert_audit(self, conn, rec: AuditRecord) -> AuditRecord: ...
    async def read_audit(
        self, conn, *, target_user_id: Optional[uuid.UUID] = None,
        target_tenant_key: Optional[str] = None, limit: int = 100,
    ) -> List[AuditRecord]: ...


# ── In-memory store (unit tier) ─────────────────────────────────────────────

class InMemoryStore:
    """Dict-backed store implementing the same protocol for fast logic tests.

    Does not enforce RLS (that is the integration tier's job); it does enforce
    the same uniqueness and atomicity semantics the service relies on.
    """

    def __init__(self) -> None:
        self.tenants: Dict[str, Tenant] = {}
        self.users: Dict[uuid.UUID, User] = {}
        self.invitations: Dict[uuid.UUID, Invitation] = {}
        self.refresh_tokens: Dict[str, RefreshToken] = {}
        self.support: List[SupportAssignment] = []
        self.audit: List[AuditRecord] = []

    @asynccontextmanager
    async def acquire(self):
        yield None

    # tenants
    async def create_tenant(self, conn, tenant: Tenant) -> Tenant:
        if tenant.key in self.tenants:
            raise ValueError("duplicate tenant key")
        t = tenant.model_copy(update={"created_at": _now(), "updated_at": _now()})
        self.tenants[t.key] = t
        return t.model_copy(deep=True)

    async def get_tenant(self, conn, key: str) -> Optional[Tenant]:
        t = self.tenants.get(key)
        return t.model_copy(deep=True) if t else None

    async def get_tenant_by_domain(self, conn, domain: str) -> Optional[Tenant]:
        domain = domain.lower()
        for t in self.tenants.values():
            if domain in [d.lower() for d in t.allowed_domains]:
                return t.model_copy(deep=True)
        return None

    async def list_tenants(self, conn) -> List[Tenant]:
        return [t.model_copy(deep=True) for t in self.tenants.values()]

    async def set_tenant_status(self, conn, key: str, status: str) -> Optional[Tenant]:
        t = self.tenants.get(key)
        if not t:
            return None
        t = t.model_copy(update={"status": status, "updated_at": _now()})
        self.tenants[key] = t
        return t.model_copy(deep=True)

    # users
    async def create_user(self, conn, user: User) -> User:
        for u in self.users.values():
            if u.email.lower() == user.email.lower():
                raise ValueError("duplicate email")
            if user.provider_uid and u.provider_uid == user.provider_uid:
                raise ValueError("duplicate provider_uid")
        u = user.model_copy(update={"created_at": _now(), "updated_at": _now()})
        self.users[u.id] = u
        return u.model_copy(deep=True)

    async def get_user_by_id(self, conn, user_id: uuid.UUID) -> Optional[User]:
        u = self.users.get(user_id)
        return u.model_copy(deep=True) if u else None

    async def get_user_by_email(self, conn, email: str) -> Optional[User]:
        email = email.lower()
        for u in self.users.values():
            if u.email.lower() == email:
                return u.model_copy(deep=True)
        return None

    async def get_user_by_provider_uid(self, conn, uid: str) -> Optional[User]:
        for u in self.users.values():
            if u.provider_uid == uid:
                return u.model_copy(deep=True)
        return None

    async def update_user(self, conn, user_id: uuid.UUID, **fields) -> Optional[User]:
        u = self.users.get(user_id)
        if not u:
            return None
        bad = set(fields) - _USER_UPDATABLE
        if bad:
            raise ValueError(f"non-updatable user fields: {sorted(bad)}")
        if "email" in fields:
            for other in self.users.values():
                if other.id != user_id and other.email.lower() == fields["email"].lower():
                    raise ValueError("duplicate email")
        if fields.get("provider_uid"):
            for other in self.users.values():
                if other.id != user_id and other.provider_uid == fields["provider_uid"]:
                    raise ValueError("duplicate provider_uid")
        u = u.model_copy(update={**fields, "updated_at": _now()})
        self.users[user_id] = u
        return u.model_copy(deep=True)

    async def list_users(self, conn, tenant_key: Optional[str] = None) -> List[User]:
        vals = self.users.values()
        if tenant_key is not None:
            vals = [u for u in vals if u.tenant_key == tenant_key]
        return [u.model_copy(deep=True) for u in vals]

    async def count_users_in_tenant(self, conn, tenant_key: str) -> int:
        return sum(1 for u in self.users.values() if u.tenant_key == tenant_key)

    async def count_superusers(self, conn) -> int:
        return sum(1 for u in self.users.values() if u.role == "superuser")

    # invitations
    async def create_invitation(self, conn, inv: Invitation) -> Invitation:
        i = inv.model_copy(update={"created_at": _now()})
        self.invitations[i.id] = i
        return i.model_copy(deep=True)

    async def get_invitation(self, conn, inv_id: uuid.UUID) -> Optional[Invitation]:
        i = self.invitations.get(inv_id)
        return i.model_copy(deep=True) if i else None

    async def get_pending_invitation_by_email(self, conn, email: str) -> Optional[Invitation]:
        email = email.lower()
        cands = [
            i for i in self.invitations.values()
            if i.email.lower() == email and i.status == "pending"
        ]
        cands.sort(key=lambda i: i.created_at or _now(), reverse=True)
        return cands[0].model_copy(deep=True) if cands else None

    async def list_invitations(self, conn, tenant_key: Optional[str] = None) -> List[Invitation]:
        vals = self.invitations.values()
        if tenant_key is not None:
            vals = [i for i in vals if i.tenant_key == tenant_key]
        return [i.model_copy(deep=True) for i in vals]

    async def update_invitation(self, conn, inv_id: uuid.UUID, **fields) -> Optional[Invitation]:
        i = self.invitations.get(inv_id)
        if not i:
            return None
        bad = set(fields) - _INVITE_UPDATABLE
        if bad:
            raise ValueError(f"non-updatable invitation fields: {sorted(bad)}")
        i = i.model_copy(update=fields)
        self.invitations[inv_id] = i
        return i.model_copy(deep=True)

    # refresh tokens
    async def store_refresh_token(self, conn, rt: RefreshToken) -> RefreshToken:
        if rt.token_hash in self.refresh_tokens:
            raise ValueError("duplicate token hash")
        r = rt.model_copy(update={"created_at": _now()})
        self.refresh_tokens[r.token_hash] = r
        return r.model_copy(deep=True)

    async def get_refresh_token_by_hash(self, conn, token_hash: str) -> Optional[RefreshToken]:
        r = self.refresh_tokens.get(token_hash)
        return r.model_copy(deep=True) if r else None

    async def revoke_refresh_token_by_hash(self, conn, token_hash: str) -> bool:
        # Atomic under asyncio: no await between the liveness check and the flip.
        r = self.refresh_tokens.get(token_hash)
        if r is None or r.revoked_at is not None:
            return False
        self.refresh_tokens[token_hash] = r.model_copy(update={"revoked_at": _now()})
        return True

    async def revoke_all_user_refresh_tokens(self, conn, user_id: uuid.UUID) -> int:
        n = 0
        for h, r in list(self.refresh_tokens.items()):
            if r.user_id == user_id and r.revoked_at is None:
                self.refresh_tokens[h] = r.model_copy(update={"revoked_at": _now()})
                n += 1
        return n

    # support assignments
    async def add_support_assignment(self, conn, sa: SupportAssignment) -> SupportAssignment:
        for existing in self.support:
            if existing.user_id == sa.user_id and existing.tenant_key == sa.tenant_key:
                return existing.model_copy(deep=True)
        s = sa.model_copy(update={"assigned_at": _now()})
        self.support.append(s)
        return s.model_copy(deep=True)

    async def get_support_scope(self, conn, user_id: uuid.UUID) -> List[str]:
        return [s.tenant_key for s in self.support if s.user_id == user_id]

    # audit
    async def insert_audit(self, conn, rec: AuditRecord) -> AuditRecord:
        r = rec.model_copy(update={"created_at": rec.created_at or _now()})
        self.audit.append(r)
        return r.model_copy(deep=True)

    async def read_audit(
        self, conn, *, target_user_id: Optional[uuid.UUID] = None,
        target_tenant_key: Optional[str] = None, limit: int = 100,
    ) -> List[AuditRecord]:
        rows = self.audit
        if target_user_id is not None:
            rows = [r for r in rows if r.target_user_id == target_user_id]
        if target_tenant_key is not None:
            rows = [r for r in rows if r.target_tenant_key == target_tenant_key]
        # Deterministic order: (created_at, id) — matches the SQL ordering (SC-004).
        rows = sorted(rows, key=lambda r: (r.created_at or _now(), str(r.id)))
        return [r.model_copy(deep=True) for r in rows[:limit]]


# ── Postgres store (integration tier) ───────────────────────────────────────

def _tenant_from_row(row) -> Tenant:
    return Tenant(
        key=row["key"], display_name=row["display_name"], parent_key=row["parent_key"],
        auth_provider=row["auth_provider"], allowed_domains=list(row["allowed_domains"]),
        status=row["status"], default_locale=row["default_locale"], timezone=row["timezone"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _user_from_row(row) -> User:
    return User(
        id=row["id"], provider_uid=row["provider_uid"], email=row["email"],
        display_name=row["display_name"], role=row["role"], customer_role=row["customer_role"],
        status=row["status"], provider=row["provider"], password_hash=row["password_hash"],
        tenant_key=row["tenant_key"], last_sign_in_at=row["last_sign_in_at"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _invite_from_row(row) -> Invitation:
    return Invitation(
        id=row["id"], email=row["email"], role=row["role"], tenant_key=row["tenant_key"],
        invited_by=row["invited_by"], status=row["status"], expires_at=row["expires_at"],
        accepted_at=row["accepted_at"], created_at=row["created_at"],
    )


def _refresh_from_row(row) -> RefreshToken:
    return RefreshToken(
        id=row["id"], user_id=row["user_id"], tenant_key=row["tenant_key"],
        token_hash=row["token_hash"], expires_at=row["expires_at"],
        revoked_at=row["revoked_at"], created_at=row["created_at"],
    )


def _audit_from_row(row) -> AuditRecord:
    return AuditRecord(
        id=row["id"], action=row["action"], actor_user_id=row["actor_user_id"],
        target_user_id=row["target_user_id"], target_tenant_key=row["target_tenant_key"],
        before_state=row["before_state"], after_state=row["after_state"],
        created_at=row["created_at"],
    )


class PgStore:
    """asyncpg-backed store. ``schema`` names the DDL schema; all SQL is qualified."""

    def __init__(self, pool, settings: IdentitySettings) -> None:
        self._pool = pool
        self._settings = settings
        self.s = settings.schema_name

    @asynccontextmanager
    async def acquire(self):
        """Acquire a pooled connection with a jsonb codec registered."""
        async with self._pool.acquire() as conn:
            await conn.set_type_codec(
                "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog",
            )
            yield conn

    # tenants
    async def create_tenant(self, conn, tenant: Tenant) -> Tenant:
        row = await conn.fetchrow(
            f"""INSERT INTO {self.s}.tenant
                (key, display_name, parent_key, auth_provider, allowed_domains,
                 status, default_locale, timezone)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING *""",
            tenant.key, tenant.display_name, tenant.parent_key, tenant.auth_provider,
            tenant.allowed_domains, tenant.status, tenant.default_locale, tenant.timezone,
        )
        return _tenant_from_row(row)

    async def get_tenant(self, conn, key: str) -> Optional[Tenant]:
        row = await conn.fetchrow(f"SELECT * FROM {self.s}.tenant WHERE key=$1", key)
        return _tenant_from_row(row) if row else None

    async def get_tenant_by_domain(self, conn, domain: str) -> Optional[Tenant]:
        row = await conn.fetchrow(
            f"SELECT * FROM {self.s}.tenant WHERE lower($1) = ANY(allowed_domains) LIMIT 1",
            domain.lower(),
        )
        return _tenant_from_row(row) if row else None

    async def list_tenants(self, conn) -> List[Tenant]:
        rows = await conn.fetch(f"SELECT * FROM {self.s}.tenant ORDER BY created_at, key")
        return [_tenant_from_row(r) for r in rows]

    async def set_tenant_status(self, conn, key: str, status: str) -> Optional[Tenant]:
        row = await conn.fetchrow(
            f"UPDATE {self.s}.tenant SET status=$2, updated_at=now() WHERE key=$1 RETURNING *",
            key, status,
        )
        return _tenant_from_row(row) if row else None

    # users
    async def create_user(self, conn, user: User) -> User:
        row = await conn.fetchrow(
            f"""INSERT INTO {self.s}.app_user
                (id, provider_uid, email, display_name, role, customer_role, status,
                 provider, password_hash, tenant_key, last_sign_in_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING *""",
            user.id, user.provider_uid, user.email, user.display_name, user.role,
            user.customer_role, user.status, user.provider, user.password_hash,
            user.tenant_key, user.last_sign_in_at,
        )
        return _user_from_row(row)

    async def get_user_by_id(self, conn, user_id: uuid.UUID) -> Optional[User]:
        row = await conn.fetchrow(f"SELECT * FROM {self.s}.app_user WHERE id=$1", user_id)
        return _user_from_row(row) if row else None

    async def get_user_by_email(self, conn, email: str) -> Optional[User]:
        row = await conn.fetchrow(
            f"SELECT * FROM {self.s}.app_user WHERE lower(email)=lower($1)", email,
        )
        return _user_from_row(row) if row else None

    async def get_user_by_provider_uid(self, conn, uid: str) -> Optional[User]:
        row = await conn.fetchrow(
            f"SELECT * FROM {self.s}.app_user WHERE provider_uid=$1", uid,
        )
        return _user_from_row(row) if row else None

    async def update_user(self, conn, user_id: uuid.UUID, **fields) -> Optional[User]:
        bad = set(fields) - _USER_UPDATABLE
        if bad:
            raise ValueError(f"non-updatable user fields: {sorted(bad)}")
        if not fields:
            return await self.get_user_by_id(conn, user_id)
        cols = list(fields)
        assigns = ", ".join(f"{c}=${i+2}" for i, c in enumerate(cols))
        row = await conn.fetchrow(
            f"UPDATE {self.s}.app_user SET {assigns}, updated_at=now() WHERE id=$1 RETURNING *",
            user_id, *[fields[c] for c in cols],
        )
        return _user_from_row(row) if row else None

    async def list_users(self, conn, tenant_key: Optional[str] = None) -> List[User]:
        if tenant_key is None:
            rows = await conn.fetch(f"SELECT * FROM {self.s}.app_user ORDER BY created_at, id")
        else:
            rows = await conn.fetch(
                f"SELECT * FROM {self.s}.app_user WHERE tenant_key=$1 ORDER BY created_at, id",
                tenant_key,
            )
        return [_user_from_row(r) for r in rows]

    async def count_users_in_tenant(self, conn, tenant_key: str) -> int:
        return await conn.fetchval(
            f"SELECT count(*) FROM {self.s}.app_user WHERE tenant_key=$1", tenant_key,
        )

    async def count_superusers(self, conn) -> int:
        return await conn.fetchval(
            f"SELECT count(*) FROM {self.s}.app_user WHERE role='superuser'",
        )

    # invitations
    async def create_invitation(self, conn, inv: Invitation) -> Invitation:
        row = await conn.fetchrow(
            f"""INSERT INTO {self.s}.invitation
                (id, email, role, tenant_key, invited_by, status, expires_at)
                VALUES ($1,$2,$3,$4,$5,$6, COALESCE($7, now() + interval '{self._settings.invite_expiry_days} days'))
                RETURNING *""",
            inv.id, inv.email, inv.role, inv.tenant_key, inv.invited_by,
            inv.status, inv.expires_at,
        )
        return _invite_from_row(row)

    async def get_invitation(self, conn, inv_id: uuid.UUID) -> Optional[Invitation]:
        row = await conn.fetchrow(f"SELECT * FROM {self.s}.invitation WHERE id=$1", inv_id)
        return _invite_from_row(row) if row else None

    async def get_pending_invitation_by_email(self, conn, email: str) -> Optional[Invitation]:
        row = await conn.fetchrow(
            f"""SELECT * FROM {self.s}.invitation
                WHERE lower(email)=lower($1) AND status='pending'
                ORDER BY created_at DESC LIMIT 1""",
            email,
        )
        return _invite_from_row(row) if row else None

    async def list_invitations(self, conn, tenant_key: Optional[str] = None) -> List[Invitation]:
        if tenant_key is None:
            rows = await conn.fetch(f"SELECT * FROM {self.s}.invitation ORDER BY created_at, id")
        else:
            rows = await conn.fetch(
                f"SELECT * FROM {self.s}.invitation WHERE tenant_key=$1 ORDER BY created_at, id",
                tenant_key,
            )
        return [_invite_from_row(r) for r in rows]

    async def update_invitation(self, conn, inv_id: uuid.UUID, **fields) -> Optional[Invitation]:
        bad = set(fields) - _INVITE_UPDATABLE
        if bad:
            raise ValueError(f"non-updatable invitation fields: {sorted(bad)}")
        if not fields:
            return await self.get_invitation(conn, inv_id)
        cols = list(fields)
        assigns = ", ".join(f"{c}=${i+2}" for i, c in enumerate(cols))
        row = await conn.fetchrow(
            f"UPDATE {self.s}.invitation SET {assigns} WHERE id=$1 RETURNING *",
            inv_id, *[fields[c] for c in cols],
        )
        return _invite_from_row(row) if row else None

    # refresh tokens
    async def store_refresh_token(self, conn, rt: RefreshToken) -> RefreshToken:
        row = await conn.fetchrow(
            f"""INSERT INTO {self.s}.refresh_token
                (id, user_id, tenant_key, token_hash, expires_at, revoked_at)
                VALUES ($1,$2,$3,$4,$5,$6) RETURNING *""",
            rt.id, rt.user_id, rt.tenant_key, rt.token_hash, rt.expires_at, rt.revoked_at,
        )
        return _refresh_from_row(row)

    async def get_refresh_token_by_hash(self, conn, token_hash: str) -> Optional[RefreshToken]:
        row = await conn.fetchrow(
            f"SELECT * FROM {self.s}.refresh_token WHERE token_hash=$1", token_hash,
        )
        return _refresh_from_row(row) if row else None

    async def revoke_refresh_token_by_hash(self, conn, token_hash: str) -> bool:
        # Atomic: only the transaction that flips revoked_at from NULL gets the row.
        row = await conn.fetchrow(
            f"""UPDATE {self.s}.refresh_token SET revoked_at=now()
                WHERE token_hash=$1 AND revoked_at IS NULL RETURNING id""",
            token_hash,
        )
        return row is not None

    async def revoke_all_user_refresh_tokens(self, conn, user_id: uuid.UUID) -> int:
        rows = await conn.fetch(
            f"""UPDATE {self.s}.refresh_token SET revoked_at=now()
                WHERE user_id=$1 AND revoked_at IS NULL RETURNING id""",
            user_id,
        )
        return len(rows)

    # support assignments
    async def add_support_assignment(self, conn, sa: SupportAssignment) -> SupportAssignment:
        row = await conn.fetchrow(
            f"""INSERT INTO {self.s}.support_assignment (user_id, tenant_key, assigned_by)
                VALUES ($1,$2,$3)
                ON CONFLICT (user_id, tenant_key) DO UPDATE SET tenant_key=EXCLUDED.tenant_key
                RETURNING *""",
            sa.user_id, sa.tenant_key, sa.assigned_by,
        )
        return SupportAssignment(
            user_id=row["user_id"], tenant_key=row["tenant_key"],
            assigned_by=row["assigned_by"], assigned_at=row["assigned_at"],
        )

    async def get_support_scope(self, conn, user_id: uuid.UUID) -> List[str]:
        rows = await conn.fetch(
            f"SELECT tenant_key FROM {self.s}.support_assignment WHERE user_id=$1", user_id,
        )
        return [r["tenant_key"] for r in rows]

    # audit
    async def insert_audit(self, conn, rec: AuditRecord) -> AuditRecord:
        # No RETURNING: audit is append-only and written under contexts that
        # deliberately lack audit SELECT visibility (broker, logout). RETURNING
        # would require read visibility and fail RLS — so the timestamp is
        # stamped here and the record returned as-inserted.
        created = rec.created_at or _now()
        await conn.execute(
            f"""INSERT INTO {self.s}.audit_log
                (id, action, actor_user_id, target_user_id, target_tenant_key,
                 before_state, after_state, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
            rec.id, rec.action, rec.actor_user_id, rec.target_user_id, rec.target_tenant_key,
            rec.before_state, rec.after_state, created,
        )
        return rec.model_copy(update={"created_at": created})

    async def read_audit(
        self, conn, *, target_user_id: Optional[uuid.UUID] = None,
        target_tenant_key: Optional[str] = None, limit: int = 100,
    ) -> List[AuditRecord]:
        clauses, args = [], []
        if target_user_id is not None:
            args.append(target_user_id)
            clauses.append(f"target_user_id=${len(args)}")
        if target_tenant_key is not None:
            args.append(target_tenant_key)
            clauses.append(f"target_tenant_key=${len(args)}")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        args.append(limit)
        rows = await conn.fetch(
            # SC-004: always ORDER BY created_at, id — deterministic, never heap order.
            f"SELECT * FROM {self.s}.audit_log {where} ORDER BY created_at, id LIMIT ${len(args)}",
            *args,
        )
        return [_audit_from_row(r) for r in rows]
