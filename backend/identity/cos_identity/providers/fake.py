"""Deterministic fake IdP + collecting invite delivery (plan R4).

A first-class deliverable, not a stub: it is the provider sim path a consumer
uses until its Firebase project exists, and the substrate for every unit/service
test. Tokens
encode the identity inline so verification is pure and reproducible.
"""
from __future__ import annotations

from typing import List, Tuple

from ..models import Invitation, VerifiedIdentity

_TOKEN_PREFIX = "fake:"


def make_fake_token(
    provider_uid: str,
    email: str,
    *,
    provider: str = "google",
    display_name: str = "",
) -> str:
    """Build a fake external token encoding an identity (test/sim helper)."""
    return f"{_TOKEN_PREFIX}{provider_uid}|{email}|{provider}|{display_name}"


class FakeIdentityProvider:
    """Verifies ``fake:uid|email|provider|display_name`` tokens deterministically."""

    def __init__(self) -> None:
        self.revoked: List[str] = []

    async def verify_external_token(self, external_token: str) -> VerifiedIdentity:
        """Parse a fake token into a :class:`VerifiedIdentity`.

        Raises ``ValueError`` for a malformed token (the 401 path in tests).
        """
        if not external_token.startswith(_TOKEN_PREFIX):
            raise ValueError("invalid fake token")
        body = external_token[len(_TOKEN_PREFIX):]
        parts = body.split("|")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError("malformed fake token")
        provider_uid, email = parts[0], parts[1].lower()
        provider = parts[2] if len(parts) > 2 and parts[2] else "google"
        display_name = parts[3] if len(parts) > 3 and parts[3] else None
        return VerifiedIdentity(
            provider_uid=provider_uid,
            email=email,
            provider=provider,
            display_name=display_name,
        )

    async def revoke_sessions(self, provider_uid: str) -> None:
        """Record a provider-side revocation (observable in tests)."""
        self.revoked.append(provider_uid)


class CollectingInviteDelivery:
    """Invite delivery that collects sends in memory instead of emailing."""

    def __init__(self) -> None:
        self.sent: List[Tuple[str, str, Invitation]] = []

    async def send(self, email: str, accept_url: str, invitation: Invitation) -> None:
        """Record the ``(email, accept_url, invitation)`` that would be delivered."""
        self.sent.append((email, accept_url, invitation))
