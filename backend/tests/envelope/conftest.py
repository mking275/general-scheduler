"""Shared fixtures for the 009 envelope-onboarding test suite.

The net-new onboarding-control + canonical financial/inventory tables run on the
SAME local docker-compose PostgreSQL the 010/011 stack uses (container
``vetagent-voice-pg``, host port 5433; override with ``VOICE_DATABASE_URL``).
Per the plan's VP-1-slip degradation, scoping is app-level ``clinic_id`` /
``practice_id`` with FORCE-RLS set as the SEC-20 posture (R8: never another
port/container).
"""
import os

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_ENVELOPE = os.path.join(_REPO_ROOT, "config", "envelope")


def _default_db_url() -> str:
    return os.environ.get(
        "VOICE_DATABASE_URL",
        "postgresql+psycopg2://voice:voice@localhost:5433/voice",
    )


@pytest.fixture(scope="session")
def db_url() -> str:
    return _default_db_url()


@pytest.fixture()
def repo(db_url):
    """A fresh OnboardingRepository with all 009 tables created (idempotent)."""
    from backend.envelope.onboarding_repository import OnboardingRepository

    r = OnboardingRepository(db_url)
    try:
        r.init_db()
    except Exception as exc:  # pragma: no cover - surfaced loudly, never silent
        pytest.skip(f"envelope Postgres unavailable at {db_url}: {exc}")
    return r
