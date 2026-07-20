"""Password hashing for the break-glass escape hatch ONLY (FR-015).

No normal sign-in path uses passwords; the platform authenticates through the
external IdP. These helpers exist solely for the secret-gated superuser recovery
path when the IdP is unavailable.
"""
from __future__ import annotations

import bcrypt

# bcrypt truncates silently past 72 bytes; guard rather than mis-hash.
_MAX_PASSWORD_BYTES = 72


def hash_password(plain: str) -> str:
    """Return a bcrypt hash (cost 12) of ``plain``; rejects >72-byte inputs."""
    encoded = plain.encode()
    if len(encoded) > _MAX_PASSWORD_BYTES:
        raise ValueError("password exceeds bcrypt's 72-byte limit")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verify ``plain`` against a stored bcrypt ``hashed``."""
    try:
        return bcrypt.checkpw(plain.encode()[:_MAX_PASSWORD_BYTES], hashed.encode())
    except (ValueError, TypeError):
        return False
