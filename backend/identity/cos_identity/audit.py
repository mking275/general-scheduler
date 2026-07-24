"""Immutable audit trail (FR-008) — the hard-won read-ordering lesson.

Writes are INSERT-only (no grant exists for UPDATE/DELETE on the audit table).
Reads ALWAYS return ``ORDER BY created_at, id`` — an explicit ordering with a
unique tie-break, never physical/heap order — so repeated reads are identical
even under insert churn with equal timestamps (SC-004).
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from .models import AuditRecord

# The canonical, non-negotiable read ordering. Documented here as the contract;
# both stores implement it (SQL ORDER BY / in-memory sort key).
AUDIT_READ_ORDER = ("created_at", "id")


class AuditLog:
    """Append-only audit facade over a store, enforcing deterministic reads."""

    def __init__(self, store) -> None:
        self._store = store

    async def record(self, conn, record: AuditRecord) -> AuditRecord:
        """Append an immutable audit record."""
        return await self._store.insert_audit(conn, record)

    async def read(
        self,
        conn,
        *,
        target_user_id: Optional[uuid.UUID] = None,
        target_tenant_key: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """Read audit records in deterministic ``(created_at, id)`` order."""
        return await self._store.read_audit(
            conn,
            target_user_id=target_user_id,
            target_tenant_key=target_tenant_key,
            limit=limit,
        )
