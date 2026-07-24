"""SC-004 — audit reads are deterministic under insert churn with equal timestamps."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.integration


async def test_deterministic_order_under_identical_timestamps(db):
    from cos_identity import PgStore
    from cos_identity.models import AuditRecord
    from cos_identity.tenancy import tenant_context

    store = PgStore(db.pool, db.settings)
    t0 = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
    earlier = t0 - timedelta(minutes=5)

    async with store.acquire() as conn:
        async with tenant_context(conn, role=db.app_role, tenant_key="tnt_a", user_role="superuser"):
            # 40 rows share t0; 5 rows (inserted LAST) carry an earlier timestamp.
            for _ in range(40):
                await store.insert_audit(conn, AuditRecord(
                    id=uuid.uuid4(), action="sign_in", target_tenant_key="tnt_a", created_at=t0))
            for _ in range(5):
                await store.insert_audit(conn, AuditRecord(
                    id=uuid.uuid4(), action="sign_in", target_tenant_key="tnt_a", created_at=earlier))
            r1 = await store.read_audit(conn, limit=100)
            r2 = await store.read_audit(conn, limit=100)

    # Determinism: repeated reads are identical.
    assert [r.id for r in r1] == [r.id for r in r2]
    # Primary sort is created_at: the 5 earlier rows come first.
    assert all(r.created_at == earlier for r in r1[:5])
    assert all(r.created_at == t0 for r in r1[5:])
    # Tie-break is id: within equal timestamps, ascending uuid order.
    tie_ids = [r.id for r in r1[5:]]
    assert tie_ids == sorted(tie_ids), "equal-timestamp rows not ordered by id tie-break"
