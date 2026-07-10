"""Shared fixtures for the voice test suite.

The 8 voice tables run on the local docker-compose PostgreSQL (port 5433 by
default; override with VOICE_DATABASE_URL). Per the plan's VP-1-slip
degradation, scoping is app-level clinic_id/party_id.
"""
import os

import pytest

# Repo-root paths for the config fixtures.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_VOICE = os.path.join(_REPO_ROOT, "config", "voice")


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
    """A fresh VoiceRepository with the 8 tables created (idempotent)."""
    from backend.voice.voice_repository import VoiceRepository

    r = VoiceRepository(db_url)
    try:
        r.init_db()
    except Exception as exc:  # pragma: no cover - surfaced loudly, never silent
        pytest.skip(f"voice Postgres unavailable at {db_url}: {exc}")
    return r
