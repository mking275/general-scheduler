"""SC-003 — the database wall holds ALONE, under the non-owner :app_role.

With every application filter removed (raw ``SELECT *``), a tenant-A context sees
only tenant-A rows; unset vars see zero rows; :app_role has no broker path; and
audit UPDATE/DELETE is refused.
"""
import uuid

import pytest

pytestmark = pytest.mark.integration

TENANT_SCOPED = ["tenant", "app_user", "invitation", "refresh_token", "support_assignment", "audit_log"]


async def _seed(db):
    """Insert mirrored rows for tenant A and tenant B as a superuser (bypasses RLS)."""
    a_uid, b_uid = uuid.uuid4(), uuid.uuid4()
    s = db.schema
    conn = db.admin
    for key, name in [("tnt_a", "Alpha Group"), ("tnt_b", "Beta Group")]:
        await conn.execute(
            f"INSERT INTO {s}.tenant (key, display_name) VALUES ($1,$2)", key, name)
    await conn.execute(
        f"""INSERT INTO {s}.app_user (id,email,role,status,provider,tenant_key)
            VALUES ($1,'a@alpha.example','agent','active','google','tnt_a')""", a_uid)
    await conn.execute(
        f"""INSERT INTO {s}.app_user (id,email,role,status,provider,tenant_key)
            VALUES ($1,'b@beta.example','agent','active','google','tnt_b')""", b_uid)
    await conn.execute(
        f"""INSERT INTO {s}.invitation (email,role,tenant_key) VALUES
            ('x@alpha.example','agent','tnt_a'),('y@beta.example','agent','tnt_b')""")
    await conn.execute(
        f"""INSERT INTO {s}.refresh_token (user_id,tenant_key,token_hash,expires_at) VALUES
            ($1,'tnt_a','ha',now()+interval '1 day'),
            ($2,'tnt_b','hb',now()+interval '1 day')""", a_uid, b_uid)
    await conn.execute(
        f"""INSERT INTO {s}.support_assignment (user_id,tenant_key) VALUES
            ($1,'tnt_a'),($2,'tnt_b')""", a_uid, b_uid)
    await conn.execute(
        f"""INSERT INTO {s}.audit_log (action,target_tenant_key) VALUES
            ('sign_in','tnt_a'),('sign_in','tnt_b')""")
    return a_uid, b_uid


async def _counts(db, *, role, set_vars):
    """Row counts per tenant-scoped table under SET LOCAL ROLE + optional app.* vars."""
    out = {}
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f'SET LOCAL ROLE "{role}"')
            for name, val in set_vars.items():
                await conn.execute("SELECT set_config($1,$2,true)", name, val)
            for t in TENANT_SCOPED:
                out[t] = await conn.fetchval(f"SELECT count(*) FROM {db.schema}.{t}")
    return out


async def test_tenant_a_context_sees_only_a(db):
    await _seed(db)
    counts = await _counts(db, role=db.app_role, set_vars={
        "app.customer_id": "tnt_a", "app.user_role": "agent",
        "app.cs_admin_scope": "", "app.user_id": "",
    })
    for t in TENANT_SCOPED:
        assert counts[t] == 1, f"{t}: expected only tenant-A row, got {counts[t]}"


async def test_switching_to_b_sees_only_b(db):
    await _seed(db)
    counts = await _counts(db, role=db.app_role, set_vars={
        "app.customer_id": "tnt_b", "app.user_role": "agent",
    })
    for t in TENANT_SCOPED:
        assert counts[t] == 1


async def test_unset_vars_see_zero_rows(db):
    await _seed(db)
    counts = await _counts(db, role=db.app_role, set_vars={})
    for t in TENANT_SCOPED:
        assert counts[t] == 0, f"{t}: fail-closed violated, saw {counts[t]}"


async def test_app_role_has_no_broker_path(db):
    await _seed(db)
    # Even asserting the broker flag, :app_role gets no broker policy → zero rows.
    counts = await _counts(db, role=db.app_role, set_vars={"app.identity_broker": "on"})
    for t in TENANT_SCOPED:
        assert counts[t] == 0, f"{t}: :app_role must have NO broker path, saw {counts[t]}"


async def test_auth_role_broker_sees_all(db):
    await _seed(db)
    # The broker role, in broker posture, performs the cross-tenant lookups login needs.
    counts = await _counts(db, role=db.auth_role, set_vars={"app.identity_broker": "on"})
    for t in ["tenant", "app_user", "invitation", "refresh_token", "support_assignment"]:
        assert counts[t] == 2, f"{t}: broker should see both tenants, saw {counts[t]}"


async def test_superuser_sees_all(db):
    await _seed(db)
    counts = await _counts(db, role=db.app_role, set_vars={"app.user_role": "superuser"})
    for t in ["tenant", "app_user", "invitation"]:
        assert counts[t] == 2


async def test_cs_admin_scope_limits_to_assigned(db):
    await _seed(db)
    counts = await _counts(db, role=db.app_role, set_vars={
        "app.user_role": "cs_admin", "app.cs_admin_scope": "tnt_b",
    })
    # Only tenant B is in scope.
    assert counts["tenant"] == 1
    assert counts["app_user"] == 1


async def test_audit_update_and_delete_refused_for_app_role(db):
    await _seed(db)
    import asyncpg

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f'SET LOCAL ROLE "{db.app_role}"')
            await conn.execute("SELECT set_config('app.user_role','superuser',true)")
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute(f"UPDATE {db.schema}.audit_log SET action='suspend'")
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f'SET LOCAL ROLE "{db.app_role}"')
            await conn.execute("SELECT set_config('app.user_role','superuser',true)")
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute(f"DELETE FROM {db.schema}.audit_log")


async def test_app_role_cannot_write_cross_tenant(db):
    await _seed(db)
    import asyncpg

    # In tenant-A context, inserting a tenant-B user must fail the WITH CHECK.
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f'SET LOCAL ROLE "{db.app_role}"')
            await conn.execute("SELECT set_config('app.customer_id','tnt_a',true)")
            await conn.execute("SELECT set_config('app.user_role','agent',true)")
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute(
                    f"""INSERT INTO {db.schema}.app_user (email,role,status,provider,tenant_key)
                        VALUES ('evil@beta.example','agent','active','google','tnt_b')""")
