"""Shared fixtures for the 011 relationship test suite.

The 13 relationship tables run on the SAME local docker-compose PostgreSQL the
010 voice stack uses (container ``vetagent-voice-pg``, host port 5433; override
with ``VOICE_DATABASE_URL``). Per the plan's VP-1-slip degradation, scoping is
app-level ``clinic_id`` / ``party_id`` (R8: never touch other ports/containers).
"""
import os

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_REL = os.path.join(_REPO_ROOT, "config", "relationship")


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
    """A fresh HouseholdRepository with the 13 tables created (idempotent)."""
    from backend.relationship.household_repository import HouseholdRepository

    r = HouseholdRepository(db_url)
    try:
        r.init_db()
    except Exception as exc:  # pragma: no cover - surfaced loudly, never silent
        pytest.skip(f"relationship Postgres unavailable at {db_url}: {exc}")
    return r
