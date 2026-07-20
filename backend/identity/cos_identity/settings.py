"""Identity component configuration — the single env/config contract (FR-014).

All organizational identity is parameterized here; the package source carries no
consumer-specific identifier (D10). Locale/timezone defaults are the neutral
``en-US`` / ``UTC``; a consumer overrides them, never the component.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from typing import Optional


@dataclass(frozen=True)
class IdentitySettings:
    """Immutable configuration surface for the identity component.

    ``jwt_secret`` is the only field with no safe default and must be supplied.
    Role and schema names default to a neutral ``cos_identity`` namespace and
    must match the values the DDL is applied with.
    """

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 1440
    refresh_token_ttl_days: int = 7
    invite_expiry_days: int = 7
    token_issuer: str = "cos-identity"
    clock_skew_leeway_seconds: int = 30

    # Database object names — MUST match the DDL applied with the same values.
    schema_name: str = "cos_identity"
    app_role: str = "cos_identity_app"
    auth_role: str = "cos_identity_auth"
    owner_role: str = "cos_identity_owner"

    # Organizational identity — parameterized, never hardcoded.
    seed_superuser_email: Optional[str] = None
    app_base_url: str = "http://localhost"
    accept_invite_path: str = "/accept-invite"
    default_locale: str = "en-US"
    default_timezone: str = "UTC"

    # Provider selection: "fake" (sim/tests) or "firebase".
    provider: str = "fake"
    firebase_project_id: Optional[str] = None
    firebase_web_api_key_secret: Optional[str] = None

    # Break-glass escape hatch (FR-015, D8 in-memory limiter).
    escape_hatch_secret: Optional[str] = None
    escape_hatch_max_attempts: int = 5
    escape_hatch_window_seconds: int = 15 * 60

    def accept_invite_url(self, invitation_id: str) -> str:
        """Absolute accept-invite URL for ``invitation_id``, from configured base."""
        base = self.app_base_url.rstrip("/")
        path = self.accept_invite_path if self.accept_invite_path.startswith("/") else f"/{self.accept_invite_path}"
        return f"{base}{path}?invitation_id={invitation_id}"

    def with_overrides(self, **changes: object) -> "IdentitySettings":
        """Return a copy with the given fields replaced (tests/multi-tenant apps)."""
        return replace(self, **changes)

    @classmethod
    def from_env(cls, env: Optional[dict] = None) -> "IdentitySettings":
        """Build settings from environment variables (``COS_IDENTITY_*`` prefix).

        Raises ``ValueError`` when the JWT secret is absent — the component never
        invents a signing key.
        """
        e = os.environ if env is None else env

        def get(name: str, default: Optional[str] = None) -> Optional[str]:
            return e.get(f"COS_IDENTITY_{name}", default)

        secret = get("JWT_SECRET")
        if not secret:
            raise ValueError("COS_IDENTITY_JWT_SECRET is required")

        def as_int(name: str, default: int) -> int:
            raw = get(name)
            return int(raw) if raw is not None else default

        return cls(
            jwt_secret=secret,
            jwt_algorithm=get("JWT_ALGORITHM", "HS256"),
            access_token_ttl_minutes=as_int("ACCESS_TOKEN_TTL_MINUTES", 1440),
            refresh_token_ttl_days=as_int("REFRESH_TOKEN_TTL_DAYS", 7),
            invite_expiry_days=as_int("INVITE_EXPIRY_DAYS", 7),
            token_issuer=get("TOKEN_ISSUER", "cos-identity"),
            clock_skew_leeway_seconds=as_int("CLOCK_SKEW_LEEWAY_SECONDS", 30),
            schema_name=get("SCHEMA_NAME", "cos_identity"),
            app_role=get("APP_ROLE", "cos_identity_app"),
            auth_role=get("AUTH_ROLE", "cos_identity_auth"),
            owner_role=get("OWNER_ROLE", "cos_identity_owner"),
            seed_superuser_email=(get("SEED_SUPERUSER_EMAIL") or None),
            app_base_url=get("APP_BASE_URL", "http://localhost"),
            accept_invite_path=get("ACCEPT_INVITE_PATH", "/accept-invite"),
            default_locale=get("DEFAULT_LOCALE", "en-US"),
            default_timezone=get("DEFAULT_TIMEZONE", "UTC"),
            provider=get("PROVIDER", "fake"),
            firebase_project_id=(get("FIREBASE_PROJECT_ID") or None),
            firebase_web_api_key_secret=(get("FIREBASE_WEB_API_KEY_SECRET") or None),
            escape_hatch_secret=(get("ESCAPE_HATCH_SECRET") or None),
            escape_hatch_max_attempts=as_int("ESCAPE_HATCH_MAX_ATTEMPTS", 5),
            escape_hatch_window_seconds=as_int("ESCAPE_HATCH_WINDOW_SECONDS", 15 * 60),
        )
