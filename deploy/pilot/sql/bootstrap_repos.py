"""VetAgent pilot — repository schema bootstrap (idempotent).

Provisions the Feature-011 relationship tables (incl. the append-only
``reveal_decision_log`` reveal audit) and the Feature-009 envelope tables by
REUSING each repository's own sentinel-guarded ``init_db()`` — no DDL is
duplicated here. Both ``init_db()`` calls are safe to re-run: table creation is
``CREATE TABLE IF NOT EXISTS`` via SQLAlchemy, and the FORCE-RLS / append-only
trigger installs are guarded by a ``pg_proc`` sentinel so a second run is a
no-op.

The C7 identity schema (001_identity_schema.sql) is applied SEPARATELY by
bootstrap.sh via psql, because its role-creation (\\gexec) and ALTER … OWNER
require a superuser psql session — see vendoring.md §2.

Target DB: the SQLAlchemy DSN in ``VOICE_DATABASE_URL``
(e.g. postgresql+psycopg2://user:pass@host:5432/db). Falls back to the shared
local dev DSN when unset.

Usage:  VOICE_DATABASE_URL=... python -m deploy.pilot.sql.bootstrap_repos
        (or run from repo root: python deploy/pilot/sql/bootstrap_repos.py)
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    # Ensure the repo root is importable when run as a bare script.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from backend.envelope.onboarding_repository import OnboardingRepository, default_db_url
    from backend.relationship.household_repository import HouseholdRepository

    dsn = os.environ.get("VOICE_DATABASE_URL", "").strip() or default_db_url()
    # Redact credentials in the log line.
    safe = dsn
    if "@" in safe:
        safe = safe.split("@", 1)[0].rsplit(":", 1)[0] + ":***@" + safe.split("@", 1)[1]
    print(f"[bootstrap] target DSN: {safe}")

    print("[bootstrap] 011 relationship tables + reveal_decision_log audit ...")
    HouseholdRepository(dsn).init_db()          # sentinel-guarded; idempotent
    print("[bootstrap]   ok")

    print("[bootstrap] 009 envelope tables + FORCE-RLS + append-only triggers ...")
    OnboardingRepository(dsn).init_db()         # sentinel-guarded; idempotent
    print("[bootstrap]   ok")

    print("[bootstrap] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
