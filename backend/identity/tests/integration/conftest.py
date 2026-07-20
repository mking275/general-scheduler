"""Integration harness — TEST_DATABASE_URL-gated (skips cleanly when unset).

Applies the shipped ``001_identity_schema.sql`` via asyncpg by doing the psql
``\\set`` substitution as simple string replacement (permitted for the harness;
the file itself stays psql-compatible). Roles are created in Python first, then
the DDL is applied against a freshly dropped schema so every test starts clean.
"""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

asyncpg = pytest.importorskip("asyncpg")

SQL_PATH = Path(__file__).resolve().parents[2] / "cos_identity" / "sql" / "001_identity_schema.sql"

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

SCHEMA = "cos_identity"
OWNER_ROLE = "cos_identity_owner"
APP_ROLE = "cos_identity_app"
AUTH_ROLE = "cos_identity_auth"


def _settings():
    from cos_identity import IdentitySettings

    return IdentitySettings(
        jwt_secret="integration-secret-000000000000",
        seed_superuser_email="root@corp.example",
        escape_hatch_secret="sekret",
        schema_name=SCHEMA, owner_role=OWNER_ROLE, app_role=APP_ROLE, auth_role=AUTH_ROLE,
    )


async def _ensure_roles(conn):
    for role in (OWNER_ROLE, APP_ROLE, AUTH_ROLE):
        exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname=$1", role)
        if not exists:
            await conn.execute(f'CREATE ROLE "{role}" NOLOGIN')


async def _apply_schema(conn):
    sql = SQL_PATH.read_text(encoding="utf-8")
    # psql :'var' quoted-literal forms first, then bare identifier forms.
    sql = (sql.replace(":'owner_role'", f"'{OWNER_ROLE}'")
              .replace(":'app_role'", f"'{APP_ROLE}'")
              .replace(":'auth_role'", f"'{AUTH_ROLE}'"))
    sql = (sql.replace(":schema", SCHEMA)
              .replace(":owner_role", OWNER_ROLE)
              .replace(":app_role", APP_ROLE)
              .replace(":auth_role", AUTH_ROLE))
    # \gexec is psql-only; as a non-psql applier we created the roles above, so
    # turn it into a statement terminator (the preceding SELECT is then a no-op).
    sql = sql.replace("\\gexec", ";")
    await conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    await conn.execute(sql)


@pytest_asyncio.fixture
async def db():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — integration tier skipped")
    admin = await asyncpg.connect(TEST_DATABASE_URL)
    await _ensure_roles(admin)
    await _apply_schema(admin)
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=1, max_size=10)
    try:
        yield SimpleNamespace(pool=pool, admin=admin, settings=_settings(),
                              schema=SCHEMA, app_role=APP_ROLE, auth_role=AUTH_ROLE)
    finally:
        await pool.close()
        await admin.close()
