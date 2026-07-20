"""Transaction-scoped RLS context (FR-009, R1).

Every store query runs inside one of these contexts, which switch to a non-owner
DB role and set the ``app.*`` session vars that the RLS policies key on. Both are
transaction-scoped (``SET LOCAL`` / ``set_config(..., true)``) so state clears at
transaction end — safe under asyncpg pooling.

``_broker_context`` is underscore-named on purpose: only service internals may
enter the broker posture (D1), and only for the three cross-tenant lookups that
login inherently requires.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List, Optional


def _quote_ident(name: str) -> str:
    """Double-quote a role identifier for ``SET LOCAL ROLE`` (config-controlled)."""
    return '"' + name.replace('"', '""') + '"'


@asynccontextmanager
async def tenant_context(
    conn,
    *,
    role: str,
    tenant_key: Optional[str],
    user_role: str,
    user_id: Optional[str] = None,
    cs_admin_scope: Optional[List[str]] = None,
):
    """Enter tenant-scoped RLS as ``role`` with the caller's identity vars.

    Opens a transaction, switches to the (non-owner) ``role``, and sets
    ``app.customer_id / app.user_role / app.user_id / app.cs_admin_scope``.
    A ``None`` connection is a no-op (the in-memory unit tier, D7).
    """
    if conn is None:
        yield None
        return
    scope_csv = ",".join(cs_admin_scope or [])
    async with conn.transaction():
        await conn.execute(f"SET LOCAL ROLE {_quote_ident(role)}")
        await conn.execute("SELECT set_config('app.customer_id', $1, true)", tenant_key or "")
        await conn.execute("SELECT set_config('app.user_role', $1, true)", user_role or "")
        await conn.execute("SELECT set_config('app.user_id', $1, true)", user_id or "")
        await conn.execute("SELECT set_config('app.cs_admin_scope', $1, true)", scope_csv)
        yield conn


@asynccontextmanager
async def _broker_context(conn, *, role: str):
    """Enter the authn broker posture (``app.identity_broker='on'``) as ``role``.

    RESTRICTED: only exchange_external_token, refresh, and accept_invitation may
    use this (D1). ``role`` must be the auth broker role, the only role granted a
    broker RLS policy. A ``None`` connection is a no-op (in-memory unit tier).
    """
    if conn is None:
        yield None
        return
    async with conn.transaction():
        await conn.execute(f"SET LOCAL ROLE {_quote_ident(role)}")
        await conn.execute("SELECT set_config('app.identity_broker', 'on', true)")
        yield conn
