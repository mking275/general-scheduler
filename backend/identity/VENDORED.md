# Vendored: cos_identity (C7) — Identity & RBAC Core

This directory is a **source-only vendor** of the COS-platform identity component
(spec 008, contract C7). It is a verbatim copy of `components/identity/` from the
COS-platform repository — do **not** hand-edit the component source here; re-vendor
from upstream instead. VetAgent-side glue lives in `backend/identity_auth.py`.

## Source provenance

| | |
|---|---|
| Upstream repo | `COS-platform` |
| Component path | `components/identity/` |
| Source commit (last touching `cos_identity/`) | `82d826d0bc8167645fecba9901a910a41707572f` — *feat(008): cos_identity — Identity & RBAC Core (C7), 89 tests green* |
| Merge commit | `9f366b60f8798552b46dfa444af6454ef7a52e6a` (PR #3, `feat/008-identity-rbac`) |
| `origin/main` HEAD at vendor time | `aa482035b0c64c8037d71dc6cd9dfb740cf20c2f` |
| Component subtree hash (`origin/main:components/identity`) | `40a60ff232297ef4a049ffbea2a3a0523a611832` |
| Vendored on | 2026-07-19 |

`__pycache__/` and `*.pyc` were stripped on copy; nothing else was modified.

## What was vendored

- `cos_identity/` — the package (settings/roles/tokens/passwords/models/ports/
  service/store/tenancy/audit + `fastapi_ext/` router factories + `providers/`
  fake & firebase + `sql/001_identity_schema.sql`).
- `tests/` — the component's own unit + integration test tiers (run verbatim).
- `conftest.py`, `pytest.ini` — the component's test harness (put this dir on
  `sys.path` so `import cos_identity` resolves; register the `integration` marker).
- `README.md`, `vendoring.md` — upstream docs, kept for provenance.

## How VetAgent consumes it

- Import path: the package is top-level `cos_identity`; `backend/identity_auth.py`
  prepends `backend/identity/` to `sys.path` so the app and its tests both import
  it under the one name.
- Provider: **`fake`** (Firebase project deferred by Matt). The fake provider is a
  first-class sim substitute per the component's own posture.
- Database: the shared dev Postgres (`vetagent-voice-pg`, host port **5433**, db
  `voice`), schema **`cos_identity`**, non-owner roles
  `cos_identity_owner` / `cos_identity_app` / `cos_identity_auth`.
- Config: all `COS_IDENTITY_*` env (see `backend/.env.example`).

## Two-role posture (do not defeat)

Tenant isolation is `ENABLE + FORCE ROW LEVEL SECURITY` under the two **non-owner**
roles. Every query runs under `:app_role`; the auth broker `:auth_role`
(`app.identity_broker='on'`) is entered by exactly three service methods
(`exchange_external_token`, `refresh`, `accept_invitation`). C7 roles
(`superuser > cs_admin > agent > viewer`) are the **staff-side** vocabulary —
client / pet-owner identity stays on the 011 verification ladder and is
intentionally **not** wired to C7.

## Re-applying the schema

```bash
PGPASSWORD=voice psql -h localhost -p 5433 -U voice -d voice \
  -v ON_ERROR_STOP=1 \
  -v schema=cos_identity -v owner_role=cos_identity_owner \
  -v app_role=cos_identity_app -v auth_role=cos_identity_auth \
  -f backend/identity/cos_identity/sql/001_identity_schema.sql
# then grant the two app roles to the service login role:
PGPASSWORD=voice psql -h localhost -p 5433 -U voice -d voice \
  -c "GRANT cos_identity_app, cos_identity_auth TO voice;"
```

## Running the component's own tests

```bash
# unit tier (no infra)
cd backend/identity && python -m pytest tests -m "not integration"
# integration tier (needs the dev Postgres on 5433)
cd backend/identity && TEST_DATABASE_URL=postgresql://voice:voice@localhost:5433/voice \
  python -m pytest tests -m integration
```
