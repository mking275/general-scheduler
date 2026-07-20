"""Fixtures for the VetAgent C7 identity wiring tests.

These exercise the vendored ``cos_identity`` component as VetAgent configures it
(fake provider, dev Postgres on host port 5433, schema ``cos_identity``). They
apply a FRESH identity schema per module — dropping and re-applying the vendored
DDL — so bootstrap/rotation/RLS assertions are deterministic. The tier skips
cleanly when the dev Postgres is unavailable (mirrors the 010/011 convention).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Put the vendored top-level ``cos_identity`` package on sys.path (same seam the
# app uses via backend.identity_auth), so ``import cos_identity`` resolves.
_BACKEND = Path(__file__).resolve().parents[2]
_IDENTITY_DIR = _BACKEND / "identity"
if str(_IDENTITY_DIR) not in sys.path:
    sys.path.insert(0, str(_IDENTITY_DIR))

asyncpg = pytest.importorskip("asyncpg")

_SQL_PATH = _IDENTITY_DIR / "cos_identity" / "sql" / "001_identity_schema.sql"

SCHEMA = "cos_identity"
OWNER_ROLE = "cos_identity_owner"
APP_ROLE = "cos_identity_app"
AUTH_ROLE = "cos_identity_auth"


def _dsn() -> str:
    url = (
        os.environ.get("COS_IDENTITY_DATABASE_URL")
        or os.environ.get("VOICE_DATABASE_URL")
        or "postgresql://voice:voice@localhost:5433/voice"
    )
    return (
        url.replace("postgresql+psycopg2://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )


async def _ensure_roles(conn):
    for role in (OWNER_ROLE, APP_ROLE, AUTH_ROLE):
        if not await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname=$1", role):
            await conn.execute(f'CREATE ROLE "{role}" NOLOGIN')


async def _apply_fresh_schema(conn):
    sql = _SQL_PATH.read_text(encoding="utf-8")
    sql = (
        sql.replace(":'owner_role'", f"'{OWNER_ROLE}'")
        .replace(":'app_role'", f"'{APP_ROLE}'")
        .replace(":'auth_role'", f"'{AUTH_ROLE}'")
    )
    sql = (
        sql.replace(":schema", SCHEMA)
        .replace(":owner_role", OWNER_ROLE)
        .replace(":app_role", APP_ROLE)
        .replace(":auth_role", AUTH_ROLE)
    )
    sql = sql.replace("\\gexec", ";")
    await conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    await conn.execute(sql)
    # Let the login role assume the two app roles at runtime (SET LOCAL ROLE).
    login = await conn.fetchval("SELECT current_user")
    await conn.execute(f'GRANT "{APP_ROLE}", "{AUTH_ROLE}" TO "{login}"')


@pytest.fixture()
async def fresh_schema():
    """Drop + re-apply the vendored identity DDL; yield the asyncpg DSN."""
    dsn = _dsn()
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as exc:  # pragma: no cover - surfaced as a skip, never silent
        pytest.skip(f"identity Postgres unavailable at {dsn}: {exc}")
    try:
        await _ensure_roles(conn)
        await _apply_fresh_schema(conn)
    finally:
        await conn.close()
    return dsn


@pytest.fixture()
async def service(fresh_schema):
    """A VetAgent-configured IdentityService bound to a fresh schema."""
    from backend.identity_auth import build_identity

    svc, open_pool, close_pool = build_identity()
    await open_pool()
    try:
        yield svc
    finally:
        await close_pool()
