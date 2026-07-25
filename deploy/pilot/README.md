# VetAgent pilot — same-day deploy runbook (Synergy Vet)

Everything here is buildable and reviewable **before** the GCP project exists.
When the project is created (human-gated — see `iam.md` §1), this runbook takes
you from "project id in hand" to "two services live + acceptance evidence
captured" in one sitting.

**Scope:** api (`backend.main:app`) + voice-bridge (`backend.voice_bridge_main:app`).
The Next.js frontend deploys separately on Vercel (`vercel.json`) — not covered here.

---

## Prereqs (before the project exists — do these now)

- [x] Images build locally (`deploy/pilot/build.sh --allow-dirty`).
- [x] DB bootstrap dry-runs against local Postgres (`sql/notes.md` §"Local dry-run").
- [x] Websocket-drop harness green (`pytest backend/tests/infra/`).
- [ ] Paid-tier model keys + Twilio creds gathered (values, not committed).

## Human-gated inputs (from `iam.md` §1 — Matt only)

1. `PROJECT_ID` — the created GCP project (Gate 1).
2. Billing budget set on that project (Gate 2).

Set once, reused below:

```bash
export PROJECT_ID=...            # from Gate 1
export REGION=us-central1
export REPO=vetagent             # Artifact Registry repo
```

---

## Order of operations (once PROJECT_ID exists)

### 1. Enable APIs + Artifact Registry

```bash
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
    secretmanager.googleapis.com artifactregistry.googleapis.com \
    aiplatform.googleapis.com
gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION"
```

### 2. Service accounts + least-privilege roles (`iam.md` §2)

```bash
gcloud iam service-accounts create vetagent-api-sa
gcloud iam service-accounts create vetagent-voice-sa
# grant per-service roles + per-secret secretAccessor (see iam.md §2/§3) ...
```

### 3. Secrets (Secret Manager — never env-baked, `iam.md` §3)

Create each entry from `iam.md` §3 and grant the consuming SA `secretAccessor`
on that specific secret:

```bash
printf '%s' "$JWT" | gcloud secrets create vetagent-identity-jwt-secret --data-file=-
# ... repeat for db urls, twilio, gemini, openai ...
```

### 4. Cloud SQL + schema bootstrap

Provision Cloud SQL (Postgres 16), then apply the schema (idempotent):

```bash
IDENTITY_ADMIN_DSN='postgresql://admin:...@HOST:5432/vetagent' \
VOICE_DATABASE_URL='postgresql+psycopg2://app:...@HOST:5432/vetagent' \
  deploy/pilot/sql/bootstrap.sh
# then the one-time grant it prints:
#   GRANT cos_identity_app, cos_identity_auth TO <app_login_role>;
```

### 5. Build + push provenance images (`build.sh`)

From a clean, `origin/main`-synced tree (the guard enforces it):

```bash
REGISTRY="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO" deploy/pilot/build.sh
docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/vetagent-api:<sha>"
docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/vetagent-voice-bridge:<sha>"
```

### 6. Deploy both services

Substitute `PROJECT_ID` / `REGION` / `IMAGE_SHA` in the manifests, then apply:

```bash
gcloud run services replace deploy/pilot/cloudrun/api.service.yaml --region="$REGION"
gcloud run services replace deploy/pilot/cloudrun/voice-bridge.service.yaml --region="$REGION"
```

### 7. Point Twilio at the voice-bridge

Set the number's Media Streams URL to
`wss://<voice-bridge-url>/twilio/media-stream`.

---

## Acceptance evidence to capture (5 items)

> Reconstructed from the provisioning intent; two are named explicitly in the
> brief (RLS spot-check, forced websocket-drop). Confirm against the W7 brief's
> exact list before sign-off.

### A1 — Deploy provenance on both services (`/healthz` carries the SHA)

```bash
curl -fsS https://<api-url>/healthz          # -> {"service":"vetagent-api","git_sha":"<sha>",...}
curl -fsS https://<voice-url>/healthz        # -> {"service":"vetagent-voice-bridge","git_sha":"<sha>","live":true}
```
Both `git_sha` values must equal the deployed commit (`build.sh` output), and
match `origin/main`.

### A2 — DB bootstrap is idempotent

Re-run `sql/bootstrap.sh`; it must exit 0 with no errors and no schema churn
(sentinels short-circuit the RLS/trigger installs). Confirm the tables exist:

```bash
psql "$VOICE_DATABASE_URL_PSQL" -c "\dt" | grep -E 'reveal_decision_log|onboarding'
```

### A3 — RLS wall spot-check (SC-003 posture)

Under the **non-owner app role** with no tenant set, a cross-tenant read returns
**zero rows** — the wall is the DB, not Python. Reference harness:
`backend/identity/tests/integration/test_rls_wall.py`. Manual spot-check:

```bash
psql "$IDENTITY_ADMIN_DSN" <<'SQL'
SET ROLE cos_identity_app;
SELECT set_config('app.customer_id', 'tenant-A', true);
-- attempt to read tenant-B rows: must be 0
SELECT count(*) FROM cos_identity.users WHERE customer_id = 'tenant-B';
SQL
```
Expected: `count = 0` (RLS filters it even though the SQL asks for tenant-B).

### A4 — Forced websocket-drop (voice-bridge survives, session intact)

The server must survive an abrupt call drop (socket close, no Twilio `stop`)
without crashing or corrupting session state. Local proof:

```bash
python3 -m pytest backend/tests/infra/test_ws_reconnect_harness.py -v
```
Live proof: place a test call, hang up mid-utterance, confirm the voice-bridge
instance stays healthy (`/healthz` still 200, no crash in logs) and re-dial
connects (Twilio-side reconnect; resume does not re-disclose).

### A5 — Secrets resolve from Secret Manager; no env-baked secrets

`gcloud run services describe` shows every credential as a `secretKeyRef`, none
as a literal env value. Both services reach `Ready` and pass their startup probe.

---

## Rollback

`gcloud run services update-traffic <svc> --to-revisions=<prev>=100`. Images are
immutable + SHA-tagged, so rollback is a traffic flip to the prior revision.
