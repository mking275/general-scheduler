"""Extension seams products supply (FR-002/005/013).

Every external dependency the identity component has — the IdP, invite delivery,
entitlement resolution, product-side provisioning — sits behind a port so that
adding a provider or a product flow requires no change to session, role, or admin
logic.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable

from .models import Invitation, User, VerifiedIdentity


@runtime_checkable
class IdentityProviderPort(Protocol):
    """An external identity provider (Firebase first; federation later)."""

    async def verify_external_token(self, external_token: str) -> VerifiedIdentity:
        """Verify an external credential and return the identity it asserts.

        Raises on an invalid/expired token; the caller maps that to a 401.
        """
        ...

    async def revoke_sessions(self, provider_uid: str) -> None:
        """Revoke the subject's provider-side sessions (called on suspend)."""
        ...


@runtime_checkable
class InviteDeliveryPort(Protocol):
    """Transport for invitation links (D5; migrates to the delivery component)."""

    async def send(self, email: str, accept_url: str, invitation: Invitation) -> None:
        """Deliver ``accept_url`` to ``email`` for ``invitation``."""
        ...


@runtime_checkable
class EntitlementsHook(Protocol):
    """Product-supplied resolver for the opaque entitlements claim (FR-005).

    The component carries the returned map verbatim into the token and never
    interprets it.
    """

    async def resolve(self, user: User, tenant: Optional[Any]) -> Dict[str, Any]:
        """Return the entitlements map for ``user`` in ``tenant`` (may be empty)."""
        ...


@runtime_checkable
class ProductHooks(Protocol):
    """Product-side provisioning seams (FR-013); none of this logic lives in core."""

    async def on_user_provisioned(self, user: User) -> None:
        """Called after a new user is created (e.g. product-side worker setup)."""
        ...

    async def deferred_registration(self, user: User) -> None:
        """Seam for guest/deferred-registration flows (stays in the product)."""
        ...
