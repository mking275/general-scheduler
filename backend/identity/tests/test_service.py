"""Service flow matrix on InMemoryStore (fast tier) — US-1..US-4 + edge cases.

Fixture rule (FR-010): every test tenant uses key != display_name so any
key/name conflation fails loudly. Plus the concurrent-refresh race (FR-012).
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from cos_identity import (
    CollectingInviteDelivery,
    FakeIdentityProvider,
    IdentitySettings,
    IdentityService,
    InMemoryStore,
    make_fake_token,
)
from cos_identity.errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
)
from cos_identity.models import Invitation, Tenant, User
from cos_identity.passwords import hash_password

SEED_EMAIL = "root@corp.example"


def _now():
    return datetime.now(tz=timezone.utc)


def _settings(**over):
    base = dict(
        jwt_secret="service-test-secret-0000000000",
        seed_superuser_email=SEED_EMAIL,
        escape_hatch_secret="sekret",
        escape_hatch_max_attempts=3,
    )
    base.update(over)
    return IdentitySettings(**base)


class _EntHook:
    async def resolve(self, user, tenant):
        return {"plan": "pro", "tenant": tenant.key if tenant else None}


async def _build(**settings_over):
    store = InMemoryStore()
    provider = FakeIdentityProvider()
    delivery = CollectingInviteDelivery()
    settings = _settings(**settings_over)
    svc = IdentityService(
        store, provider, settings, invite_delivery=delivery, entitlements_hook=_EntHook(),
    )
    async with store.acquire() as conn:
        # key != display_name — the FR-010 fixture rule.
        await store.create_tenant(conn, Tenant(
            key="tnt_alpha", display_name="Alpha Clinic Group",
            allowed_domains=["alpha.example"],
        ))
        await store.create_tenant(conn, Tenant(
            key="tnt_beta", display_name="Beta Veterinary",
            allowed_domains=["beta.example"],
        ))
    return svc, store, provider, delivery, settings


def _superuser_actor():
    return {"sub": str(uuid.uuid4()), "role": "superuser", "customer_id": None,
            "cs_admin_scope": [], "email": "admin@corp.example", "entitlements": {}}


# ── fixture-rule guard ──────────────────────────────────────────────────────

async def test_every_test_tenant_key_differs_from_display_name():
    _svc, store, *_ = await _build()
    async with store.acquire() as conn:
        for t in await store.list_tenants(conn):
            assert t.key != t.display_name


# ── US-1: exchange / auto-provision ─────────────────────────────────────────

async def test_domain_allowlist_first_user_is_account_owner():
    svc, *_ = await _build()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    assert pair.user.role == "viewer"
    assert pair.user.customer_role == "account_owner"
    assert pair.user.tenant_key == "tnt_alpha"
    # Token carries the display name distinct from the key, and entitlements.
    from cos_identity import verify_token
    claims = verify_token(svc.settings, pair.access_token, expected_type="access")
    assert claims["customer_id"] == "tnt_alpha"
    assert claims["customer_name"] == "Alpha Clinic Group"
    assert claims["entitlements"] == {"plan": "pro", "tenant": "tnt_alpha"}


async def test_second_user_in_tenant_is_member():
    svc, *_ = await _build()
    await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    pair2 = await svc.exchange_external_token(make_fake_token("u2", "vet@alpha.example"))
    assert pair2.user.customer_role == "member"


async def test_unknown_domain_refused():
    svc, *_ = await _build()
    with pytest.raises(ForbiddenError):
        await svc.exchange_external_token(make_fake_token("u1", "nobody@unknown.example"))


async def test_seed_superuser_bootstrap():
    svc, *_ = await _build()
    pair = await svc.exchange_external_token(make_fake_token("root", SEED_EMAIL))
    assert pair.user.role == "superuser"
    assert pair.user.tenant_key is None
    # Bootstraps once: a DIFFERENT IdP identity claiming the seed email collides
    # with the existing superuser account (no info leak, no second superuser).
    with pytest.raises(ConflictError):
        await svc.exchange_external_token(make_fake_token("root2", SEED_EMAIL))


async def test_returning_user_reuses_account():
    svc, store, *_ = await _build()
    p1 = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    p2 = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    assert p1.user.id == p2.user.id


async def test_idp_identity_collision_refused():
    svc, *_ = await _build()
    await svc.exchange_external_token(make_fake_token("uidA", "shared@alpha.example"))
    with pytest.raises(ConflictError):
        await svc.exchange_external_token(make_fake_token("uidB", "shared@alpha.example"))


# ── US-2: invitations + suspension + audit ──────────────────────────────────

async def test_invite_accept_via_invitation_id():
    svc, store, provider, delivery, _ = await _build()
    admin = _superuser_actor()
    inv = await svc.invite(admin, email="newbie@alpha.example", role="agent", tenant_key="tnt_alpha")
    assert len(delivery.sent) == 1
    pair = await svc.accept_invitation(
        make_fake_token("newbie-uid", "newbie@alpha.example"), str(inv.id),
    )
    assert pair.user.status == "active"
    assert pair.user.role == "agent"
    assert pair.user.tenant_key == "tnt_alpha"
    async with store.acquire() as conn:
        got = await store.get_invitation(conn, inv.id)
        assert got.status == "accepted"


async def test_pending_invitation_accepted_on_plain_exchange():
    svc, store, *_ = await _build()
    admin = _superuser_actor()
    inv = await svc.invite(admin, email="staff@beta.example", role="viewer", tenant_key="tnt_beta")
    # No invitation_id supplied — the invited user row is activated on first sign-in.
    pair = await svc.exchange_external_token(make_fake_token("staff-uid", "staff@beta.example"))
    assert pair.user.status == "active"
    assert pair.user.tenant_key == "tnt_beta"
    async with store.acquire() as conn:
        assert (await store.get_invitation(conn, inv.id)).status == "accepted"


async def test_expired_invitation_refused_no_side_effects():
    svc, store, *_ = await _build()
    async with store.acquire() as conn:
        inv = await store.create_invitation(conn, Invitation(
            email="late@alpha.example", role="agent", tenant_key="tnt_alpha",
            expires_at=_now() - timedelta(days=1),
        ))
    with pytest.raises(NotFoundError):
        await svc.accept_invitation(make_fake_token("late-uid", "late@alpha.example"), str(inv.id))
    async with store.acquire() as conn:
        assert await store.get_user_by_email(conn, "late@alpha.example") is None


async def test_invite_email_mismatch_refused():
    svc, *_ = await _build()
    admin = _superuser_actor()
    inv = await svc.invite(admin, email="a@alpha.example", role="agent", tenant_key="tnt_alpha")
    with pytest.raises(ForbiddenError):
        await svc.accept_invitation(make_fake_token("x", "different@alpha.example"), str(inv.id))


async def test_resend_extends_expiry():
    svc, store, provider, delivery, _ = await _build()
    admin = _superuser_actor()
    inv = await svc.invite(admin, email="r@alpha.example", role="agent", tenant_key="tnt_alpha")
    resent = await svc.resend_invitation(admin, str(inv.id))
    assert resent.expires_at >= inv.expires_at
    assert len(delivery.sent) == 2


async def test_suspend_blocks_and_revokes():
    svc, store, provider, *_ = await _build()
    admin = _superuser_actor()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    await svc.suspend(admin, str(pair.user.id))
    # provider-side revocation happened
    assert "u1" in provider.revoked
    # new sign-in blocked
    with pytest.raises(ForbiddenError):
        await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    # refresh dies — suspension revoked the stored refresh, so it is rejected
    # (revoked check fires before the suspended-status check; both block).
    with pytest.raises((AuthenticationError, ForbiddenError)):
        await svc.refresh(pair.refresh_token)


async def test_reactivate_restores_access():
    svc, *_ = await _build()
    admin = _superuser_actor()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    await svc.suspend(admin, str(pair.user.id))
    await svc.reactivate(admin, str(pair.user.id))
    again = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    assert again.user.status == "active"


async def test_audit_records_and_deterministic_read():
    svc, *_ = await _build()
    admin = _superuser_actor()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    await svc.suspend(admin, str(pair.user.id))
    await svc.reactivate(admin, str(pair.user.id))
    r1 = await svc.read_audit(admin)
    r2 = await svc.read_audit(admin)
    actions = [r.action for r in r1]
    assert "sign_in" in actions and "suspend" in actions and "reactivate" in actions
    assert [r.id for r in r1] == [r.id for r in r2]


# ── rank ceiling (US-3) ─────────────────────────────────────────────────────

async def test_cs_admin_cannot_invite_peer_rank():
    svc, *_ = await _build()
    cs_admin = {"sub": str(uuid.uuid4()), "role": "cs_admin", "customer_id": "tnt_alpha",
                "cs_admin_scope": ["tnt_alpha"], "email": "cs@corp.example", "entitlements": {}}
    with pytest.raises(ForbiddenError):
        await svc.invite(cs_admin, email="peer@alpha.example", role="cs_admin", tenant_key="tnt_alpha")


async def test_cs_admin_cannot_elevate_to_superuser():
    svc, *_ = await _build()
    admin = _superuser_actor()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    cs_admin = {"sub": str(uuid.uuid4()), "role": "cs_admin", "customer_id": "tnt_alpha",
                "cs_admin_scope": ["tnt_alpha"], "email": "cs@corp.example", "entitlements": {}}
    with pytest.raises(ForbiddenError):
        await svc.patch_user(cs_admin, str(pair.user.id), role="superuser")


async def test_invite_outside_scope_refused():
    svc, *_ = await _build()
    cs_admin = {"sub": str(uuid.uuid4()), "role": "cs_admin", "customer_id": "tnt_alpha",
                "cs_admin_scope": ["tnt_alpha"], "email": "cs@corp.example", "entitlements": {}}
    with pytest.raises(ForbiddenError):
        await svc.invite(cs_admin, email="x@beta.example", role="agent", tenant_key="tnt_beta")


# ── US-3: switch tenant scoping ──────────────────────────────────────────────

async def test_switch_tenant_scope_enforced():
    svc, *_ = await _build()
    cs_admin = {"sub": str(uuid.uuid4()), "role": "cs_admin", "customer_id": "tnt_alpha",
                "cs_admin_scope": ["tnt_alpha"], "email": "cs@corp.example", "entitlements": {"plan": "x"}}
    token = await svc.switch_tenant(cs_admin, "tnt_alpha")
    from cos_identity import verify_token
    claims = verify_token(svc.settings, token, expected_type="access")
    assert claims["customer_id"] == "tnt_alpha"
    assert claims["customer_name"] == "Alpha Clinic Group"
    with pytest.raises(ForbiddenError):
        await svc.switch_tenant(cs_admin, "tnt_beta")


async def test_switch_tenant_superuser_any():
    svc, *_ = await _build()
    su = _superuser_actor()
    token = await svc.switch_tenant(su, "tnt_beta")
    from cos_identity import verify_token
    assert verify_token(svc.settings, token, expected_type="access")["customer_id"] == "tnt_beta"


async def test_agent_cannot_switch_tenant():
    svc, *_ = await _build()
    agent = {"sub": str(uuid.uuid4()), "role": "agent", "customer_id": "tnt_alpha",
             "cs_admin_scope": [], "email": "a@alpha.example", "entitlements": {}}
    with pytest.raises(ForbiddenError):
        await svc.switch_tenant(agent, "tnt_beta")


# ── US-2/FR-012: refresh, logout, rotation, race ────────────────────────────

async def test_refresh_rotates_and_old_token_dies():
    svc, *_ = await _build()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    rotated = await svc.refresh(pair.refresh_token)
    assert rotated.refresh_token != pair.refresh_token
    with pytest.raises(AuthenticationError):
        await svc.refresh(pair.refresh_token)  # replayed original


async def test_logout_idempotent_and_kills_refresh():
    svc, *_ = await _build()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    await svc.logout(pair.refresh_token)
    await svc.logout(pair.refresh_token)  # idempotent — no error
    with pytest.raises(AuthenticationError):
        await svc.refresh(pair.refresh_token)


async def test_concurrent_refresh_yields_exactly_one_session():
    svc, *_ = await _build()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    results = await asyncio.gather(
        *[svc.refresh(pair.refresh_token) for _ in range(12)],
        return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(successes) == 1, f"expected 1 winner, got {len(successes)}"
    assert all(isinstance(r, AuthenticationError) for r in failures)


# ── FR-015: escape hatch ────────────────────────────────────────────────────

async def _seed_superuser_with_password(store, email, password):
    async with store.acquire() as conn:
        await store.create_user(conn, User(
            email=email, role="superuser", status="active", provider="password",
            password_hash=hash_password(password),
        ))


async def test_escape_hatch_happy_and_wrong_secret():
    svc, store, *_ = await _build()
    await _seed_superuser_with_password(store, "break@corp.example", "glass")
    pair = await svc.escape_hatch_login(
        email="break@corp.example", password="glass", secret="sekret",
    )
    assert pair.user.role == "superuser"
    with pytest.raises(ForbiddenError):
        await svc.escape_hatch_login(email="break@corp.example", password="glass", secret="wrong")


async def test_escape_hatch_rate_limited():
    svc, store, *_ = await _build()
    await _seed_superuser_with_password(store, "break@corp.example", "glass")
    for _ in range(3):
        await svc.escape_hatch_login(email="break@corp.example", password="glass", secret="sekret", client_ip="1.2.3.4")
    with pytest.raises(RateLimitError):
        await svc.escape_hatch_login(email="break@corp.example", password="glass", secret="sekret", client_ip="1.2.3.4")


async def test_escape_hatch_non_superuser_refused():
    svc, store, *_ = await _build()
    async with store.acquire() as conn:
        await store.create_user(conn, User(
            email="agent@alpha.example", role="agent", status="active", provider="password",
            password_hash=hash_password("glass"), tenant_key="tnt_alpha",
        ))
    with pytest.raises(ForbiddenError):
        await svc.escape_hatch_login(email="agent@alpha.example", password="glass", secret="sekret")
