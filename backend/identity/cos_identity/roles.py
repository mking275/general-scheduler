"""Canonical platform-role vocabulary (FR-003) — the C7 vocabulary C6/C4 consume.

One ranked table lives here and nowhere else. The rank ceiling (FR-006) is the
single rule that governs who may invite or elevate whom: never at-or-above one's
own rank.
"""
from __future__ import annotations

from typing import List

# Platform roles, ascending rank. This is the ONLY rank table in the platform.
VIEWER = "viewer"
AGENT = "agent"
CS_ADMIN = "cs_admin"
SUPERUSER = "superuser"

ROLE_RANK: dict[str, int] = {
    VIEWER: 0,
    AGENT: 1,
    CS_ADMIN: 2,
    SUPERUSER: 3,
}

ALL_ROLES: tuple[str, ...] = (VIEWER, AGENT, CS_ADMIN, SUPERUSER)

# Roles that may be granted via invitation (superuser is bootstrap-only, never invited).
INVITABLE_ROLES: tuple[str, ...] = (CS_ADMIN, AGENT, VIEWER)

# Orthogonal customer-role axis (FR-004); semantics owned by billing (extraction #2).
ACCOUNT_OWNER = "account_owner"
MEMBER = "member"
CUSTOMER_ROLES: tuple[str, ...] = (ACCOUNT_OWNER, MEMBER)


def rank(role: str) -> int:
    """Numeric rank of ``role``; unknown roles rank below everything (-1)."""
    return ROLE_RANK.get(role, -1)


def has_rank(role: str, min_role: str) -> bool:
    """True when ``role`` meets or exceeds ``min_role`` in the hierarchy."""
    return rank(role) >= rank(min_role)


def invitable_roles(actor_role: str) -> List[str]:
    """Roles ``actor_role`` may invite/assign: strictly below their own rank.

    Enforces the rank ceiling (FR-006) — an admin may never invite or elevate a
    peer or a superior.
    """
    ceiling = rank(actor_role)
    return [r for r in INVITABLE_ROLES if rank(r) < ceiling]


def can_grant_role(actor_role: str, target_role: str) -> bool:
    """True when ``actor_role`` may invite or set a user to ``target_role``."""
    return target_role in invitable_roles(actor_role)
