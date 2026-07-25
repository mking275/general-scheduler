# IAM & model-access plan — VetAgent pilot (Synergy Vet)

Least-privilege identity per Cloud Run service, the two human-gated steps, and
the model-access posture. Nothing here is applied automatically — this is the
plan the same-day runbook (README.md) executes once the project exists.

> **Provenance note for the coordinator:** the two human-gated steps below are
> reconstructed from the provisioning intent, not pasted from the W7 brief — the
> literal brief text was not present in this worktree. Replace the quoted blocks
> with the brief's exact wording before this doc is treated as authoritative.

---

## 1. Two human-gated steps (Matt-only — do NOT automate)

These are the only two steps a minion must NOT perform. They create spend
authority and the tenancy boundary; they are the human's to own.

> **Gate 1 — GCP project creation.**
> Matt creates the GCP project (and links it to the billing account). No agent
> runs `gcloud projects create` or `gcloud billing` — the project id is handed
> to the runbook as an input.

> **Gate 2 — Budget / billing budget.**
> Matt sets the billing budget and alert thresholds for the project. No agent
> creates or edits the budget. Infra proceeds only after the budget exists.

Everything downstream of these two (service accounts, roles, secrets, deploys)
is minion-executable once the project id is in hand.

---

## 2. Per-service service accounts (least privilege)

Two dedicated SAs, one per Cloud Run service. Neither is the default compute SA
(which is over-privileged). Each gets ONLY the roles its service needs.

### `vetagent-api-sa` — the API service

| Role | Why |
|------|-----|
| `roles/cloudsql.client` | connect to Cloud SQL (identity + envelope/relationship tables) |
| `roles/secretmanager.secretAccessor` | read its secrets (JWT signing key, DB DSNs, Twilio creds) — **scope the grant to the specific secrets**, not project-wide |
| `roles/logging.logWriter` | structured logs |
| `roles/monitoring.metricWriter` | request metrics |

No Vertex/Gemini access: the api does not call realtime models.

### `vetagent-voice-sa` — the voice-bridge service

| Role | Why |
|------|-----|
| `roles/cloudsql.client` | the 8 voice tables (call sessions, escalation events, reveal audit) |
| `roles/secretmanager.secretAccessor` | Gemini + OpenAI keys, Twilio creds, voice DB DSN — **scoped to those secrets** |
| `roles/logging.logWriter` | structured logs |
| `roles/monitoring.metricWriter` | realtime latency / SLO metrics |
| `roles/aiplatform.user` | **only if** Gemini Live is used via Vertex rather than the paid API key (see §4) |

No blanket `roles/editor` on either SA. Secret access is granted per-secret
(`gcloud secrets add-iam-policy-binding <secret> --member=...`), not at project
scope, so a compromised SA reads only its own slots.

### DB login roles (distinct from GCP SAs)

The DB has its own role model (vendoring.md §2): the app login role is granted
the NOLOGIN `cos_identity_app` / `cos_identity_auth` roles so RLS applies under
`SET LOCAL ROLE`. The api and voice services may share one Cloud SQL login role
for the pilot (single clinic) or use two; either way, product queries run under
`:app_role`, never the owner role.

---

## 3. Secret Manager inventory (never env-baked)

Every secret is a Secret Manager entry referenced by `secretKeyRef` in the
Cloud Run manifests. None is baked into an image or a plaintext env.

| Secret | Consumer(s) |
|--------|-------------|
| `vetagent-identity-jwt-secret` | api (HS256 signing) |
| `vetagent-identity-db-url` | api (asyncpg DSN) |
| `vetagent-voice-db-url` | api + voice (SQLAlchemy DSN) |
| `vetagent-twilio-account-sid`, `vetagent-twilio-auth-token` | api + voice |
| `vetagent-gemini-api-key` | voice (paid tier) |
| `vetagent-openai-api-key` | voice (Realtime fallback) |

---

## 4. Model access

**Paid-tier keys only.** Free-tier / consumer keys are not permitted for the
pilot — they carry data-use terms and rate limits unfit for clinic traffic.
Provision paid-tier keys and store them as the Secret Manager entries above.

### gen-3 Gemini requires `location=global` (coupling warning)

The gen-3 Gemini (Live) primary **requires the client location be `global`**.
This is a hard coupling, not a preference: a regional location (e.g.
`us-central1`) will fail or silently route to an unsupported endpoint for gen-3.
The voice-bridge manifest sets `GEMINI_LOCATION=global` for exactly this reason.
If you ever pin a region for data-residency, you drop off gen-3 and must
re-qualify a different model — treat the region choice and the model generation
as one coupled decision.

### OpenAI Realtime fallback

The voice port is provider-agnostic (`RealtimeModelPort`); OpenAI Realtime is
the drop-in fallback. Provision a paid `vetagent-openai-api-key` slot even if
Gemini is primary, so a failover is a config swap (`VOICE_LIVE` stays on, the
adapter selection flips) with no redeploy of new code.

---

## 5. What stays off

- No public bucket, no `allUsers` grants.
- No `roles/owner` / `roles/editor` on any runtime SA.
- Ingress is `all` only because Twilio + the Vercel frontend are external
  callers; tighten to an internal LB + IAP if/when a private network lands.
