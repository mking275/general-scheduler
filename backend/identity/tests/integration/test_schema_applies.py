"""T015 — the DDL applies clean and forces RLS on all six tables."""
import pytest

pytestmark = pytest.mark.integration

TABLES = ["tenant", "app_user", "invitation", "refresh_token", "support_assignment", "audit_log"]


async def test_all_tables_exist(db):
    for t in TABLES:
        exists = await db.admin.fetchval(
            "SELECT to_regclass($1)", f"{db.schema}.{t}",
        )
        assert exists is not None, f"missing table {t}"


async def test_rls_enabled_and_forced_everywhere(db):
    for t in TABLES:
        row = await db.admin.fetchrow(
            """SELECT relrowsecurity, relforcerowsecurity
               FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname=$1 AND c.relname=$2""",
            db.schema, t,
        )
        assert row["relrowsecurity"], f"RLS not enabled on {t}"
        assert row["relforcerowsecurity"], f"RLS not FORCED on {t}"


async def test_tables_owned_by_owner_role(db):
    for t in TABLES:
        owner = await db.admin.fetchval(
            """SELECT pg_get_userbyid(c.relowner)
               FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname=$1 AND c.relname=$2""",
            db.schema, t,
        )
        assert owner == db.settings.owner_role


async def test_audit_has_no_update_or_delete_grant_for_app_role(db):
    for priv in ("UPDATE", "DELETE"):
        has = await db.admin.fetchval(
            "SELECT has_table_privilege($1, $2, $3)",
            db.app_role, f"{db.schema}.audit_log", priv,
        )
        assert has is False, f"app role must not have {priv} on audit_log"
    # ...but INSERT and SELECT are granted.
    for priv in ("INSERT", "SELECT"):
        assert await db.admin.fetchval(
            "SELECT has_table_privilege($1, $2, $3)",
            db.app_role, f"{db.schema}.audit_log", priv,
        ) is True
