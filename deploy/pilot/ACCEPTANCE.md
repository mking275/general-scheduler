# Pilot Infrastructure — Acceptance Evidence

**Project** `vetagent-503823` · **Region** us-central1 · **Captured** 2026-07-29
**Serving commit** `a7de8da` (verified against image tags, not asserted)

Evidence for the five acceptance items in Steward's W7 provisioning brief. Every
result below is real output from the live project — no simulated or expected values.

---

## A1 · Deploy provenance ✅

Both services expose the build SHA and it **matches the deployed image tag**:

```
vetagent-api           {"status":"ok","service":"vetagent-api","git_sha":"a7de8da",…}
vetagent-voice-bridge  {"status":"ok","service":"vetagent-voice-bridge","git_sha":"a7de8da",…}
```

Two defects were found and fixed getting here, both recorded in `README.md`:
1. **Cloud Run reserves `/healthz`** — intercepted at the edge, never forwarded. Probe `/api/healthz`.
2. **A runtime `GIT_SHA` env var silently overrode the baked value**, so the service
   reported an *older* commit than it was running. Build provenance must not be
   overridable by runtime config; verification is a **comparison**, never a single read.

## A2 · Database bootstrap is idempotent ✅

Re-ran the full four-layer bootstrap against live Cloud SQL — clean no-op, stable at
40 tables across `public` + `cos_identity`. Layers: C7 identity (6 tables), 011
relationship, 009 envelope, `reveal_decision_log` audit spine. 27 tables under
FORCE row-level security; both append-only trigger functions installed.

## A3 · RLS wall — SC-003 posture ✅

Not a bare zero. Three-part proof, per the fleet's 2026-07-28 vacuous-zero hazard:

```
STEP 1 · keys verified exact (copied, never retyped):   tenant-A, tenant-B
STEP 2 · positive control — tenant-B rows EXIST:        1
STEP 3 · isolation, session scoped to tenant-A:
           should_be_zero (tenant-B rows visible):      0
           should_be_positive (tenant-A rows visible):  1
           unfiltered SELECT … GROUP BY tenant_key:     tenant-A only
```

The unfiltered select is the clincher: with **no WHERE clause**, only tenant-A returns —
so the wall is the database, not application filtering. Corroborating evidence: the
policy also blocked the *seeding* attempt until the documented admin path was used.

## A4 · Forced websocket drop ✅

Against the live voice bridge, not a simulation:

```
1. connected; Twilio start + media frames sent
2. TCP ABORTED mid-stream — no close handshake (the real Twilio failure mode)
3. RECONNECTED after the abort — service survived, session state intact
   post-abort health: {"status":"ok",…,"git_sha":"a7de8da"}
```

## A5 · Secrets from Secret Manager — ⚠ PARTIAL

**Passing:** every credential resolves via `secretKeyRef` — 4 on the API, 5 on the
voice bridge, **zero literal values** in either service config.

**Outstanding:** both services currently run as `vetagent-agent-ops`, which is the
**deployer** identity (holds `run.admin`, `artifactregistry.admin`). A compromised
container would inherit deploy rights. **Deployer identity must not be runtime
identity.** Fix pending: dedicated `vetagent-api-sa` / `vetagent-voice-sa` holding only
`cloudsql.client` plus per-secret accessor, then redeploy onto them. Held open
deliberately rather than reported green.

---

## Notes for the board

- Cost lever unchanged: Cloud SQL is **non-HA (zonal)** for shadow week; HA enable is a
  deliberate decision at the pilot-activation gate, not a default.
- The ops account cannot read Cloud Logging, so the first failed revision was diagnosed
  by reproducing locally. `roles/logging.viewer` is worth adding before pilot week, when
  a failure may only reproduce in the cloud.
