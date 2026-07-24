"""VetAgent-side wiring for the vendored cos_identity (C7) component.

The component ships source-only under ``backend/identity/cos_identity`` (see
``backend/identity/VENDORED.md`` for the source commit). This is the ONLY glue
VetAgent adds on top of it:

* put the vendored top-level ``cos_identity`` package on ``sys.path``;
* build :class:`IdentitySettings` from ``COS_IDENTITY_*`` env with dev/sim
  defaults (provider ``fake`` — Firebase deferred by Matt — and the shared dev
  Postgres on host port 5433, schema ``cos_identity``);
* construct an :class:`IdentityService` over a :class:`PgStore` whose asyncpg
  pool is opened lazily at app startup (so the routers can be mounted at import
  time and the DB connection deferred).

Two-role posture (D1) is the component's; nothing here defeats it. C7 roles
(``superuser > cs_admin > agent > viewer``) are the STAFF-side vocabulary —
client / pet-owner identity stays on the 011 verification ladder and is
deliberately NOT wired to C7 here.
"""
from __future__ import annotations

import os
import sys

_IDENTITY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "identity")
if _IDENTITY_DIR not in sys.path:
    sys.path.insert(0, _IDENTITY_DIR)

from cos_identity import (  # noqa: E402  (import after sys.path tweak)
    FakeIdentityProvider,
    IdentityService,
    IdentitySettings,
    PgStore,
)
from cos_identity.fastapi_ext import (  # noqa: E402
    build_admin_router,
    build_auth_router,
)

__all__ = [
    "build_settings",
    "build_identity",
    "build_auth_router",
    "build_admin_router",
]


def _default_db_url() -> str:
    """asyncpg DSN for the shared dev Postgres (host port 5433, db ``voice``).

    Reuses the 010/011 dev container; override with ``COS_IDENTITY_DATABASE_URL``
    (or ``VOICE_DATABASE_URL``). No secrets are committed — this is a dev default.
    """
    return (
        os.environ.get("COS_IDENTITY_DATABASE_URL")
        or os.environ.get("VOICE_DATABASE_URL")
        or "postgresql://voice:voice@localhost:5433/voice"
    )


def _to_asyncpg_dsn(url: str) -> str:
    """Tolerate a SQLAlchemy-style URL if that is what the env carries."""
    return (
        url.replace("postgresql+psycopg2://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )


def build_settings(env: dict | None = None) -> IdentitySettings:
    """Build :class:`IdentitySettings` with VetAgent dev/sim defaults.

    Every default is overridable via the corresponding ``COS_IDENTITY_*`` var;
    the JWT secret has a dev-only fallback so the fake-provider flow works out of
    the box without committing a secret. Set a real secret via env in any shared
    environment.
    """
    e = dict(os.environ if env is None else env)
    e.setdefault("COS_IDENTITY_JWT_SECRET", "dev-only-vetagent-identity-secret-change-me")
    e.setdefault("COS_IDENTITY_PROVIDER", "fake")
    e.setdefault("COS_IDENTITY_SEED_SUPERUSER_EMAIL", "demo@clinic.com")
    e.setdefault("COS_IDENTITY_TOKEN_ISSUER", "vetagent-identity")
    e.setdefault("COS_IDENTITY_APP_BASE_URL", "http://localhost:3000")
    e.setdefault("COS_IDENTITY_DEFAULT_TIMEZONE", "America/Los_Angeles")
    # schema / role names default to the neutral cos_identity* namespace, which is
    # exactly what the DDL was applied with — keep them in lockstep.
    e.setdefault("COS_IDENTITY_SCHEMA_NAME", "cos_identity")
    e.setdefault("COS_IDENTITY_APP_ROLE", "cos_identity_app")
    e.setdefault("COS_IDENTITY_AUTH_ROLE", "cos_identity_auth")
    e.setdefault("COS_IDENTITY_OWNER_ROLE", "cos_identity_owner")
    return IdentitySettings.from_env(e)


def _build_provider(settings: IdentitySettings):
    """Select the IdP adapter. Only ``fake`` is wired — Firebase is deferred."""
    if settings.provider == "fake":
        return FakeIdentityProvider()
    raise NotImplementedError(
        f"COS_IDENTITY_PROVIDER={settings.provider!r} is not wired in VetAgent; "
        "Firebase is deferred by Matt. Set COS_IDENTITY_PROVIDER=fake for dev/sim."
    )


def build_identity(settings: IdentitySettings | None = None):
    """Construct the service and lazy pool lifecycle handles.

    Returns ``(service, open_pool, close_pool)``. ``service`` can be handed to the
    router factories immediately (mount at import time); ``open_pool`` /
    ``close_pool`` are awaited from FastAPI startup / shutdown so the DB
    connection is deferred until the app actually runs.
    """
    settings = settings or build_settings()
    provider = _build_provider(settings)
    store = PgStore(None, settings)  # pool attached lazily by open_pool()
    service = IdentityService(store, provider, settings)

    async def open_pool():
        import asyncpg

        if store._pool is None:
            dsn = _to_asyncpg_dsn(_default_db_url())
            store._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return store._pool

    async def close_pool():
        if store._pool is not None:
            await store._pool.close()
            store._pool = None

    return service, open_pool, close_pool
