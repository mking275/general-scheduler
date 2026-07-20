"""Domain models (pydantic v2) — the data shapes the store and service exchange.

The tenant key is opaque text kept distinct from ``display_name`` (FR-010); no
model conflates the two. No product-domain tier field exists (FR-005).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

Role = str  # one of roles.ALL_ROLES
Provider = str  # google | microsoft | password
UserStatus = str  # invited | active | suspended
TenantStatus = str  # active | inactive
CustomerRole = str  # account_owner | member
InviteStatus = str  # pending | accepted | expired


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VerifiedIdentity(_Model):
    """The outcome of an external-IdP token verification (provider-agnostic)."""

    provider_uid: str
    email: str
    provider: Provider
    display_name: Optional[str] = None


class Tenant(_Model):
    """A customer tenant. ``key`` is opaque; ``parent_key`` is the v1.1 seam (FR-016)."""

    key: str
    display_name: str
    parent_key: Optional[str] = None
    auth_provider: Provider = "google"
    allowed_domains: List[str] = Field(default_factory=list)
    status: TenantStatus = "active"
    default_locale: str = "en-US"
    timezone: str = "UTC"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class User(_Model):
    """A platform user. ``provider_uid`` is null until the IdP identity is claimed."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    provider_uid: Optional[str] = None
    email: str
    display_name: Optional[str] = None
    role: Role = "viewer"
    customer_role: CustomerRole = "member"
    status: UserStatus = "active"
    provider: Provider = "google"
    password_hash: Optional[str] = None
    tenant_key: Optional[str] = None
    last_sign_in_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Invitation(_Model):
    """An invite; the record id IS the token (FR-006)."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: str
    role: Role
    tenant_key: Optional[str] = None
    invited_by: Optional[uuid.UUID] = None
    status: InviteStatus = "pending"
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class RefreshToken(_Model):
    """A server-side refresh grant; only ``token_hash`` (SHA-256) is stored."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    tenant_key: Optional[str] = None
    token_hash: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SupportAssignment(_Model):
    """A cs_admin ↔ tenant grant powering support scope (FR-011)."""

    user_id: uuid.UUID
    tenant_key: str
    assigned_by: Optional[uuid.UUID] = None
    assigned_at: Optional[datetime] = None


class AuditRecord(_Model):
    """An immutable identity-mutation record (FR-008)."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    action: str
    actor_user_id: Optional[uuid.UUID] = None
    target_user_id: Optional[uuid.UUID] = None
    target_tenant_key: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class SessionPair(_Model):
    """The internal session issued after an IdP exchange (FR-001)."""

    access_token: str
    refresh_token: str
    user: User
    cs_admin_scope: List[str] = Field(default_factory=list)
