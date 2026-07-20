"""T018 — service flows against real Postgres (PgStore), incl. the refresh race.

Running the same service code over PgStore catches any protocol drift from the
in-memory tier (D7) and proves the RLS wiring and atomic rotation end-to-end.
"""
import asyncio
import uuid

import pytest

pytestmark = pytest.mark.integration


async def _seed_tenant(db, key, name, domains):
    await db.admin.execute(
        f"INSERT INTO {db.schema}.tenant (key, display_name, allowed_domains) VALUES ($1,$2,$3)",
        key, name, domains,
    )


def _service(db):
    from cos_identity import (
        CollectingInviteDelivery,
        FakeIdentityProvider,
        IdentityService,
        PgStore,
    )

    return IdentityService(
        PgStore(db.pool, db.settings), FakeIdentityProvider(), db.settings,
        invite_delivery=CollectingInviteDelivery(),
    )


def _superuser_actor():
    return {"sub": str(uuid.uuid4()), "role": "superuser", "customer_id": None,
            "cs_admin_scope": [], "email": "admin@corp.example", "entitlements": {}}


async def test_exchange_auto_provisions_account_owner(db):
    from cos_identity import make_fake_token, verify_token

    await _seed_tenant(db, "tnt_alpha", "Alpha Clinic Group", ["alpha.example"])
    svc = _service(db)
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    assert pair.user.customer_role == "account_owner"
    assert pair.user.tenant_key == "tnt_alpha"
    claims = verify_token(db.settings, pair.access_token, expected_type="access")
    assert claims["customer_name"] == "Alpha Clinic Group"


async def test_invite_accept_and_audit_against_db(db):
    from cos_identity import make_fake_token

    await _seed_tenant(db, "tnt_alpha", "Alpha Clinic Group", ["alpha.example"])
    svc = _service(db)
    admin = _superuser_actor()
    inv = await svc.invite(admin, email="new@alpha.example", role="agent", tenant_key="tnt_alpha")
    pair = await svc.accept_invitation(make_fake_token("new-uid", "new@alpha.example"), str(inv.id))
    assert pair.user.status == "active" and pair.user.role == "agent"
    audit = await svc.read_audit(admin, tenant_key="tnt_alpha")
    actions = {r.action for r in audit}
    assert {"invite", "accept", "sign_in"} <= actions


async def test_suspend_revokes_refresh_in_db(db):
    from cos_identity import make_fake_token
    from cos_identity.errors import AuthenticationError, ForbiddenError

    await _seed_tenant(db, "tnt_alpha", "Alpha Clinic Group", ["alpha.example"])
    svc = _service(db)
    admin = _superuser_actor()
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    await svc.suspend(admin, str(pair.user.id))
    with pytest.raises((AuthenticationError, ForbiddenError)):
        await svc.refresh(pair.refresh_token)


async def test_refresh_rotation_and_replay_in_db(db):
    from cos_identity import make_fake_token
    from cos_identity.errors import AuthenticationError

    await _seed_tenant(db, "tnt_alpha", "Alpha Clinic Group", ["alpha.example"])
    svc = _service(db)
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    rotated = await svc.refresh(pair.refresh_token)
    assert rotated.refresh_token != pair.refresh_token
    with pytest.raises(AuthenticationError):
        await svc.refresh(pair.refresh_token)


async def test_concurrent_refresh_exactly_one_winner_in_db(db):
    from cos_identity import make_fake_token
    from cos_identity.errors import AuthenticationError

    await _seed_tenant(db, "tnt_alpha", "Alpha Clinic Group", ["alpha.example"])
    svc = _service(db)
    pair = await svc.exchange_external_token(make_fake_token("u1", "boss@alpha.example"))
    results = await asyncio.gather(
        *[svc.refresh(pair.refresh_token) for _ in range(8)], return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(successes) == 1, f"expected exactly one winner, got {len(successes)}"
    assert all(isinstance(r, AuthenticationError) for r in failures)


async def test_domain_refused_and_unknown_tenant(db):
    from cos_identity import make_fake_token
    from cos_identity.errors import ForbiddenError

    await _seed_tenant(db, "tnt_alpha", "Alpha Clinic Group", ["alpha.example"])
    svc = _service(db)
    with pytest.raises(ForbiddenError):
        await svc.exchange_external_token(make_fake_token("u9", "ghost@nowhere.example"))
