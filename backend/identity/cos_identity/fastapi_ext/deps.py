"""FastAPI auth dependencies (FR-003).

``get_current_user`` is the SOLE JWT entry point: it decodes the bearer token and
asserts ``token_type == 'access'``. ``require_role(min)`` is a factory; the
``require_superuser``/``require_cs_admin`` dependencies are the factory's RESULT,
not the factory itself — mounting ``Depends(require_role)`` uncalled would enforce
nothing (the FA2 bug this deliberately avoids).

The active :class:`IdentitySettings` is read from ``request.app.state.identity_settings``
(the consumer sets it when building the app).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..roles import ROLE_RANK
from ..settings import IdentitySettings
from ..tokens import ACCESS, TokenError, verify_token

bearer_scheme = HTTPBearer(auto_error=False)


def _settings(request: Request) -> IdentitySettings:
    settings = getattr(request.app.state, "identity_settings", None)
    if settings is None:
        raise HTTPException(status_code=500, detail="identity_settings not configured on app.state")
    return settings


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Decode the bearer access token; the only place a JWT is trusted."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_token(_settings(request), credentials.credentials, expected_type=ACCESS)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return payload


def build_current_user_dep(settings: IdentitySettings):
    """Return a ``get_current_user`` bound to explicit ``settings`` (no app.state)."""

    async def _dep(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            return verify_token(settings, credentials.credentials, expected_type=ACCESS)
        except TokenError as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    return _dep


def require_role(min_role: str):
    """Factory: a dependency enforcing at least ``min_role`` (call it, don't mount it)."""

    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if ROLE_RANK.get(current_user.get("role", ""), -1) < ROLE_RANK.get(min_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {min_role} role or higher",
            )
        return current_user

    return _check


# Pre-instantiated (the factory RESULT, so Depends enforces — not the factory itself).
require_superuser = require_role("superuser")
require_cs_admin = require_role("cs_admin")
