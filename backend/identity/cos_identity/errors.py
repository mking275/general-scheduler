"""Service-layer error taxonomy (transport-agnostic).

The FastAPI extra maps these to HTTP status codes; non-FastAPI consumers map
them however they wish. Core never imports a web framework.
"""
from __future__ import annotations


class IdentityError(Exception):
    """Base class for all identity service errors."""

    status_code = 400


class AuthenticationError(IdentityError):
    """Credential/token verification failed."""

    status_code = 401


class ForbiddenError(IdentityError):
    """Authenticated but not permitted (rank ceiling, suspension, scope)."""

    status_code = 403


class NotFoundError(IdentityError):
    """A referenced entity does not exist."""

    status_code = 404


class ConflictError(IdentityError):
    """An identity is already bound to another account (no info leak)."""

    status_code = 409


class ValidationError(IdentityError):
    """The request is malformed."""

    status_code = 422


class RateLimitError(IdentityError):
    """Too many attempts (escape hatch)."""

    status_code = 429
