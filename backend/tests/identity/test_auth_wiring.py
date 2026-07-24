"""VetAgent C7 wiring — fake-provider login, rotating refresh, rejection, RLS.

Exercises the vendored ``cos_identity`` service exactly as VetAgent configures it
(fake provider, dev Postgres 5433, schema ``cos_identity``, seed superuser
``demo@clinic.com``). Requires the dev Postgres; skips cleanly otherwise (see
conftest).
"""
from __future__ import annotations

import asyncpg
import httpx
import pytest
from fastapi import FastAPI

from cos_identity import make_fake_token
from cos_identity.errors import AuthenticationError

from backend.identity_auth import build_auth_router, build_admin_router

SEED_EMAIL = "demo@clinic.com"


# ── fake-provider login ──────────────────────────────────────────────────────

async def test_login_fake_provider_bootstraps_superuser(service):
    """First sign-in as the seed email mints a real internal session pair."""
    token = make_fake_token("demo-uid-1", SEED_EMAIL, display_name="Demo Staff")
    pair = await service.exchange_external_token(token)

    assert pair.access_token and pair.refresh_token
    assert pair.access_token != pair.refresh_token
    assert pair.user.email == SEED_EMAIL
    # seed-superuser bootstrap (first user, empty schema) => superuser
    assert pair.user.role == "superuser"


async def test_login_unknown_domain_is_forbidden(service):
    """A non-seed identity with no invite / allowed domain cannot self-provision."""
    from cos_identity.errors import ForbiddenError

    token = make_fake_token("stranger-uid", "nobody@unknown.example")
    with pytest.raises(ForbiddenError):
        await service.exchange_external_token(token)


# ── rotating refresh (client must store the returned pair every time) ─────────

async def test_refresh_rotates_and_revokes_old(service):
    """refresh() returns a NEW pair; the presented refresh token is revoked."""
    pair = await service.exchange_external_token(
        make_fake_token("demo-uid-1", SEED_EMAIL)
    )

    rotated = await service.refresh(pair.refresh_token)
    # new refresh token issued (rotation), old one no longer usable
    assert rotated.refresh_token != pair.refresh_token
    assert rotated.access_token  # fresh access token minted too

    # the ORIGINAL refresh token is now revoked -> reuse rejected
    with pytest.raises(AuthenticationError):
        await service.refresh(pair.refresh_token)

    # the NEW refresh token rotates again cleanly
    rotated2 = await service.refresh(rotated.refresh_token)
    assert rotated2.refresh_token not in (pair.refresh_token, rotated.refresh_token)


# ── invalid token rejected ───────────────────────────────────────────────────

async def test_invalid_external_token_rejected(service):
    token = "not-a-fake-token"
    with pytest.raises(AuthenticationError):
        await service.exchange_external_token(token)


async def test_invalid_refresh_token_rejected(service):
    with pytest.raises(AuthenticationError):
        await service.refresh("garbage.not.a.jwt")


# ── HTTP surface: mounted routers honour the contract ────────────────────────

async def test_http_exchange_refresh_and_auth_guard(service):
    """The mounted auth router returns the pair and rotates; admin routes guard."""
    app = FastAPI()
    app.state.identity_settings = service.settings
    app.include_router(build_auth_router(service), prefix="/api/auth")
    app.include_router(build_admin_router(service), prefix="/api/admin")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        token = make_fake_token("demo-uid-1", SEED_EMAIL)
        r = await ac.post("/api/auth/exchange", json={"external_token": token})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["access_token"] and body["refresh_token"]

        # refresh rotates: a different refresh token comes back
        r2 = await ac.post("/api/auth/refresh", json={"refresh_token": body["refresh_token"]})
        assert r2.status_code == 200, r2.text
        assert r2.json()["refresh_token"] != body["refresh_token"]

        # admin route without a bearer -> 401
        r3 = await ac.get("/api/admin/users")
        assert r3.status_code == 401

        # admin route with a garbage bearer -> 401
        r4 = await ac.get("/api/admin/users", headers={"Authorization": "Bearer nope"})
        assert r4.status_code == 401

        # superuser access token unlocks the admin route
        r5 = await ac.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert r5.status_code == 200, r5.text


# ── RLS posture actually applies under the non-owner app role ────────────────

async def test_rls_wall_fail_closed_and_tenant_scoped(fresh_schema):
    """FORCE RLS under :app_role: fail-closed with no vars, scoped by customer_id."""
    conn = await asyncpg.connect(fresh_schema)
    try:
        # Seed as the login superuser (RLS is bypassed for superusers not SET ROLE'd).
        await conn.execute(
            "INSERT INTO cos_identity.tenant(key, display_name) VALUES('t1','T1'),('t2','T2')"
        )
        await conn.execute(
            "INSERT INTO cos_identity.app_user(email, tenant_key) "
            "VALUES('a@t1.example','t1'),('b@t2.example','t2')"
        )

        # Under :app_role with NO app.* vars set -> fail-closed, zero rows.
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE cos_identity_app")
            n = await conn.fetchval("SELECT count(*) FROM cos_identity.app_user")
            assert n == 0

        # Under :app_role scoped to t1 -> sees only the t1 user (cross-tenant hidden).
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE cos_identity_app")
            await conn.execute("SELECT set_config('app.customer_id','t1',true)")
            rows = await conn.fetch("SELECT email FROM cos_identity.app_user")
            emails = {r["email"] for r in rows}
            assert emails == {"a@t1.example"}
    finally:
        await conn.close()
