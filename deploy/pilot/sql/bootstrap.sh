#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# VetAgent pilot — database bootstrap (idempotent). Applies, IN ORDER:
#   1. C7 identity schema (001_identity_schema.sql) via psql \set recipe
#      (vendoring.md §2) — needs a SUPERUSER psql session (role creation +
#      ALTER … OWNER).
#   2. 011 relationship tables + reveal_decision_log audit  (repo init_db)
#   3. 009 envelope tables + FORCE-RLS + append-only triggers (repo init_db)
# Steps 2–3 reuse each repository's sentinel-guarded init_db() — no duplicate DDL.
#
# Env:
#   IDENTITY_ADMIN_DSN   superuser psql DSN for the identity DDL, e.g.
#                        postgresql://admin:pw@127.0.0.1:5432/vetagent
#   VOICE_DATABASE_URL   SQLAlchemy DSN for the repos, e.g.
#                        postgresql+psycopg2://app:pw@127.0.0.1:5432/vetagent
#   IDENTITY_SCHEMA / _OWNER_ROLE / _APP_ROLE / _AUTH_ROLE  (optional overrides;
#                        MUST match the app's COS_IDENTITY_* env — vendoring.md §1)
#
# Idempotent: safe to re-run. Everything is IF-NOT-EXISTS / sentinel-guarded.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
IDENTITY_SQL="${REPO_ROOT}/backend/identity/cos_identity/sql/001_identity_schema.sql"

SCHEMA="${IDENTITY_SCHEMA:-cos_identity}"
OWNER_ROLE="${IDENTITY_OWNER_ROLE:-cos_identity_owner}"
APP_ROLE="${IDENTITY_APP_ROLE:-cos_identity_app}"
AUTH_ROLE="${IDENTITY_AUTH_ROLE:-cos_identity_auth}"

# ── Step 1: identity DDL (psql, superuser) ─────────────────────────────────
if [[ -z "${IDENTITY_ADMIN_DSN:-}" ]]; then
  echo "ERROR: IDENTITY_ADMIN_DSN unset — required for the C7 identity schema (superuser psql)." >&2
  exit 1
fi
echo "[bootstrap] step 1/3: applying C7 identity schema (schema=${SCHEMA}) ..."
psql "${IDENTITY_ADMIN_DSN}" \
     -v ON_ERROR_STOP=1 \
     -v schema="${SCHEMA}" \
     -v owner_role="${OWNER_ROLE}" \
     -v app_role="${APP_ROLE}" \
     -v auth_role="${AUTH_ROLE}" \
     -f "${IDENTITY_SQL}"
echo "[bootstrap] step 1/3: ok"

# ── Steps 2–3: relationship + envelope repos (SQLAlchemy init_db) ───────────
echo "[bootstrap] steps 2-3/3: relationship (011) + envelope (009) repos ..."
PYTHON_BIN="${PYTHON_BIN:-python3}"
( cd "${REPO_ROOT}" && "${PYTHON_BIN}" deploy/pilot/sql/bootstrap_repos.py )

echo "[bootstrap] all steps complete."
echo "[bootstrap] NOTE: grant the app login role its identity roles (vendoring.md §2):"
echo "           GRANT ${APP_ROLE}, ${AUTH_ROLE} TO <your_service_login_role>;"
