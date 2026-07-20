"""Internal session tokens — access/refresh mint + verify (FR-001/005/012).

The external IdP session is never trusted after exchange: the component mints its
own HS256 pair. Access-token claims are a superset-compatible evolution of the
FA2 shape (D4), with an opaque ``entitlements`` map replacing product tiers.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Mapping, Optional

import jwt

from .settings import IdentitySettings

ACCESS = "access"
REFRESH = "refresh"


class TokenError(Exception):
    """Raised when a token fails verification (invalid, expired, or wrong type)."""


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def mint_access_token(
    settings: IdentitySettings,
    *,
    user_id: str,
    email: str,
    role: str,
    customer_id: Optional[str],
    customer_name: Optional[str],
    customer_role: str,
    cs_admin_scope: Optional[List[str]] = None,
    entitlements: Optional[Mapping[str, Any]] = None,
) -> str:
    """Mint a short-lived access token with the D4 claim set.

    ``entitlements`` is carried opaquely and never interpreted (FR-005).
    """
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "customer_id": str(customer_id) if customer_id else None,
        "customer_name": customer_name,
        "customer_role": customer_role,
        "cs_admin_scope": list(cs_admin_scope or []),
        "entitlements": dict(entitlements or {}),
        "token_type": ACCESS,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "iss": settings.token_issuer,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def mint_refresh_token(
    settings: IdentitySettings,
    *,
    user_id: str,
    jti: Optional[str] = None,
) -> tuple[str, str]:
    """Mint a refresh token; returns ``(token, jti)``. The DB stores only its hash."""
    jti = jti or str(uuid.uuid4())
    now = _now()
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "token_type": REFRESH,
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_ttl_days),
        "iss": settings.token_issuer,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def verify_token(
    settings: IdentitySettings,
    token: str,
    *,
    expected_type: Optional[str] = None,
) -> dict:
    """Decode and verify a token; assert ``token_type`` when ``expected_type`` given.

    Verification is clock-skew tolerant (``clock_skew_leeway_seconds``) and
    enforces the configured issuer. Raises ``TokenError`` on any failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.token_issuer,
            leeway=settings.clock_skew_leeway_seconds,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:  # invalid signature, expired, bad issuer, etc.
        raise TokenError(str(exc)) from exc

    if expected_type is not None and payload.get("token_type") != expected_type:
        raise TokenError(f"expected {expected_type} token, got {payload.get('token_type')!r}")
    return payload


def hash_refresh_token(raw_token: str) -> str:
    """SHA-256 hex digest of a refresh token — only the hash is ever persisted."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
