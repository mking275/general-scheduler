# Database bootstrap notes — VetAgent pilot

## What gets provisioned, in order

| # | Owner | What | Applied by | Idempotency |
|---|-------|------|-----------|-------------|
| 1 | C7 identity | `cos_identity` schema, 3 non-owner roles, 6 tables, FORCE-RLS + broker policy | `psql` (`bootstrap.sh` step 1) | `\gexec` role guard + `CREATE … IF NOT EXISTS`; re-runnable |
| 2 | 011 relationship | 13 tables incl. append-only `reveal_decision_log`, `consent_event`, `inbound_message` | `HouseholdRepository.init_db()` (`bootstrap_repos.py`) | `create_all` + `pg_proc` sentinel (`relationship_reject_mutation`) |
| 3 | 009 envelope | onboarding-control + canonical tables, FORCE-RLS, append-only triggers | `OnboardingRepository.init_db()` (`bootstrap_repos.py`) | `create_all` + `pg_proc` sentinel (`envelope_reject_mutation`) |

No DDL is duplicated in this directory: steps 2–3 call the repositories' own
`init_db()`. The reveal-decision audit log is table #2's `reveal_decision_log`
(011), so it is provisioned by step 2 — there is no separate "reveal log" DDL.

## Two DSNs (two roles, two drivers)

- **`IDENTITY_ADMIN_DSN`** — a *superuser* psql DSN. Step 1 creates roles and
  runs `ALTER … OWNER`, which a plain login role cannot do. Format:
  `postgresql://admin:pw@host:5432/db`.
- **`VOICE_DATABASE_URL`** — the SQLAlchemy DSN used by both repos and by the
  running app. Format: `postgresql+psycopg2://app:pw@host:5432/db`. The login
  role here needs `CREATE` on the target schema and (for the FORCE-RLS installs)
  ownership of the 009/011 tables it creates — which it gets by creating them.

## Post-bootstrap grant (required once)

The identity DDL creates `cos_identity_app` / `cos_identity_auth` as **NOLOGIN**
roles. The service's login role must be granted them so it can `SET LOCAL ROLE`
at runtime (vendoring.md §2):

```sql
GRANT cos_identity_app, cos_identity_auth TO <your_service_login_role>;
```

## RLS spot-check (SC-003 posture)

After bootstrap, confirm the wall is the DB, not Python. Under the **app role**
with no tenant set, a cross-tenant read must return zero rows (see the README
acceptance section for the exact `SET ROLE` + `set_config` recipe). The identity
integration test `backend/identity/tests/integration/test_rls_wall.py` is the
canonical reference harness.

## Local dry-run

Against the repo's dev Postgres (docker-compose.voice.yml, host port 5433) you
can exercise steps 2–3 without a superuser:

```bash
VOICE_DATABASE_URL=postgresql+psycopg2://voice:voice@localhost:5433/voice \
  python3 deploy/pilot/sql/bootstrap_repos.py
```

Step 1 (identity) needs a role that may create roles; the shared dev `voice`
superuser works locally.
