"""cos_identity — Identity & RBAC Core (C7).

Source-only, vendored by products. The core (settings/roles/tokens/passwords/
models/ports/service/store/tenancy/audit) imports without FastAPI or
firebase_admin on the path; the FastAPI router factories live in
``cos_identity.fastapi_ext`` and the Firebase adapter soft-imports its SDK.
"""
from __future__ import annotations

from . import roles
from .audit import AuditLog
from .errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    IdentityError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from .models import (
    AuditRecord,
    Invitation,
    RefreshToken,
    SessionPair,
    SupportAssignment,
    Tenant,
    User,
    VerifiedIdentity,
)
from .ports import (
    EntitlementsHook,
    IdentityProviderPort,
    InviteDeliveryPort,
    ProductHooks,
)
from .providers.fake import CollectingInviteDelivery, FakeIdentityProvider, make_fake_token
from .roles import (
    ACCOUNT_OWNER,
    AGENT,
    CS_ADMIN,
    MEMBER,
    ROLE_RANK,
    SUPERUSER,
    VIEWER,
    can_grant_role,
    has_rank,
    invitable_roles,
)
from .service import IdentityService
from .settings import IdentitySettings
from .store import InMemoryStore, PgStore, Store
from .tenancy import tenant_context
from .tokens import (
    ACCESS,
    REFRESH,
    TokenError,
    hash_refresh_token,
    mint_access_token,
    mint_refresh_token,
    verify_token,
)

__all__ = [
    "roles",
    "IdentitySettings",
    "IdentityService",
    "Store",
    "InMemoryStore",
    "PgStore",
    "AuditLog",
    "tenant_context",
    # roles vocabulary
    "ROLE_RANK", "SUPERUSER", "CS_ADMIN", "AGENT", "VIEWER",
    "ACCOUNT_OWNER", "MEMBER", "has_rank", "invitable_roles", "can_grant_role",
    # tokens
    "ACCESS", "REFRESH", "TokenError", "mint_access_token", "mint_refresh_token",
    "verify_token", "hash_refresh_token",
    # models
    "Tenant", "User", "Invitation", "RefreshToken", "SupportAssignment",
    "AuditRecord", "SessionPair", "VerifiedIdentity",
    # ports & providers
    "IdentityProviderPort", "InviteDeliveryPort", "EntitlementsHook", "ProductHooks",
    "FakeIdentityProvider", "CollectingInviteDelivery", "make_fake_token",
    # errors
    "IdentityError", "AuthenticationError", "ForbiddenError", "NotFoundError",
    "ConflictError", "ValidationError", "RateLimitError",
]
