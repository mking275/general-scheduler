"""httpx ASGI tests over the router factories — happy paths + 401/403 matrix."""
import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cos_identity import (
    CollectingInviteDelivery,
    FakeIdentityProvider,
    IdentitySettings,
    IdentityService,
    InMemoryStore,
    make_fake_token,
)
from cos_identity.fastapi_ext import build_admin_router, build_auth_router
from cos_identity.models import Tenant

SEED_EMAIL = "root@corp.example"


@pytest_asyncio.fixture
async def client():
    store = InMemoryStore()
    settings = IdentitySettings(
        jwt_secret="fastapi-test-secret-000000000000", seed_superuser_email=SEED_EMAIL,
        escape_hatch_secret="sekret",
    )
    svc = IdentityService(store, FakeIdentityProvider(), settings,
                          invite_delivery=CollectingInviteDelivery())
    async with store.acquire() as conn:
        await store.create_tenant(conn, Tenant(
            key="tnt_alpha", display_name="Alpha Clinic Group", allowed_domains=["alpha.example"]))
        await store.create_tenant(conn, Tenant(
            key="tnt_beta", display_name="Beta Veterinary", allowed_domains=["beta.example"]))
    app = FastAPI()
    app.state.identity_settings = settings
    app.include_router(build_auth_router(svc), prefix="/api/auth")
    app.include_router(build_admin_router(svc), prefix="/api/admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c._svc = svc  # stash for tests that need direct service access
        yield c


async def _exchange(client, uid, email, invitation_id=None):
    r = await client.post("/api/auth/exchange",
                          json={"external_token": make_fake_token(uid, email),
                                "invitation_id": invitation_id})
    return r


async def test_exchange_happy_path(client):
    r = await _exchange(client, "root", SEED_EMAIL)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["role"] == "superuser"


async def test_admin_requires_auth(client):
    r = await client.get("/api/admin/users")
    assert r.status_code == 401


async def test_admin_forbidden_for_viewer(client):
    viewer = (await _exchange(client, "u1", "boss@alpha.example")).json()
    r = await client.get("/api/admin/users",
                         headers={"Authorization": f"Bearer {viewer['access_token']}"})
    assert r.status_code == 403


async def test_superuser_can_list_and_invite(client):
    su = (await _exchange(client, "root", SEED_EMAIL)).json()
    h = {"Authorization": f"Bearer {su['access_token']}"}
    r = await client.post("/api/admin/invitations",
                          json={"email": "new@alpha.example", "role": "agent", "tenant_key": "tnt_alpha"},
                          headers=h)
    assert r.status_code == 200, r.text
    r2 = await client.get("/api/admin/invitations", headers=h)
    assert r2.status_code == 200
    assert any(i["email"] == "new@alpha.example" for i in r2.json())


async def test_switch_tenant_requires_cs_admin(client):
    viewer = (await _exchange(client, "u1", "boss@alpha.example")).json()
    r = await client.post("/api/auth/switch-tenant", json={"tenant_key": "tnt_beta"},
                          headers={"Authorization": f"Bearer {viewer['access_token']}"})
    assert r.status_code == 403


async def test_switch_tenant_superuser_ok(client):
    su = (await _exchange(client, "root", SEED_EMAIL)).json()
    r = await client.post("/api/auth/switch-tenant", json={"tenant_key": "tnt_beta"},
                          headers={"Authorization": f"Bearer {su['access_token']}"})
    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_refresh_and_logout(client):
    boss = (await _exchange(client, "u1", "boss@alpha.example")).json()
    r = await client.post("/api/auth/refresh", json={"refresh_token": boss["refresh_token"]})
    assert r.status_code == 200
    new_refresh = r.json()["refresh_token"]
    lo = await client.post("/api/auth/logout", json={"refresh_token": new_refresh})
    assert lo.status_code == 200
    r2 = await client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert r2.status_code == 401


async def test_suspended_user_refresh_rejected(client):
    su = (await _exchange(client, "root", SEED_EMAIL)).json()
    boss = (await _exchange(client, "u1", "boss@alpha.example")).json()
    h = {"Authorization": f"Bearer {su['access_token']}"}
    await client.post(f"/api/admin/users/{boss['user']['id']}/suspend", headers=h)
    r = await client.post("/api/auth/refresh", json={"refresh_token": boss["refresh_token"]})
    # Suspension revokes the refresh grant, so refresh is rejected (401 revoked
    # or 403 suspended — both deny).
    assert r.status_code in (401, 403)


async def test_bad_token_is_401(client):
    r = await client.get("/api/admin/users", headers={"Authorization": "Bearer garbage.token.here"})
    assert r.status_code == 401
