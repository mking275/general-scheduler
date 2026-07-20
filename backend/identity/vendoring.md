# Vendoring guide — cos_identity (C7)

How a product adopts the identity component: configuration, DDL, the two-role
security posture, the extension hooks, the API/client contract, and the
FarmAgent2 cutover notes. The component ships **source only**; you vendor the
`cos_identity/` directory and deploy it as part of your service.

## 1. Configuration — the one surface

Everything organizational is `IdentitySettings` (env prefix `COS_IDENTITY_`);
the source carries **no consumer identifier** and neutral `en-US`/`UTC` defaults.

| Field | Env | Notes |
|---|---|---|
| `jwt_secret` | `COS_IDENTITY_JWT_SECRET` | required; HS256 signing key |
| `access_token_ttl_minutes` / `refresh_token_ttl_days` | `…_ACCESS_TOKEN_TTL_MINUTES` / `…_REFRESH_TOKEN_TTL_DAYS` | 1440 / 7 |
| `schema_name`, `app_role`, `auth_role`, `owner_role` | `…_SCHEMA_NAME`, `…_APP_ROLE`, `…_AUTH_ROLE`, `…_OWNER_ROLE` | **must** match the DDL apply values |
| `seed_superuser_email` | `…_SEED_SUPERUSER_EMAIL` | bootstrap superuser (first sign-in) |
| `app_base_url`, `accept_invite_path` | `…_APP_BASE_URL`, `…_ACCEPT_INVITE_PATH` | build the accept-invite URL |
| `default_locale`, `default_timezone` | `…_DEFAULT_LOCALE`, `…_DEFAULT_TIMEZONE` | neutral defaults; a consumer overrides |
| `provider` | `…_PROVIDER` | `fake` or `firebase` |
| `firebase_project_id`, `firebase_web_api_key_secret` | `…_FIREBASE_PROJECT_ID`, `…_FIREBASE_WEB_API_KEY_SECRET` | Secret-Manager **location**, not the key |
| `escape_hatch_secret`, `…_max_attempts`, `…_window_seconds` | `…_ESCAPE_HATCH_SECRET`, … | break-glass gate + limiter |

## 2. Applying the schema

The DDL is psql `\set`-parameterized. Apply once, as a superuser (or a role that
may create roles and `ALTER … OWNER`):

```bash
psql -v ON_ERROR_STOP=1 \
     -v schema=cos_identity \
     -v owner_role=cos_identity_owner \
     -v app_role=cos_identity_app \
     -v auth_role=cos_identity_auth \
     -f cos_identity/sql/001_identity_schema.sql
```

The `\gexec` block creates the three roles if absent (NOLOGIN, non-owner). Grant
them to your service's **login** role so it can `SET LOCAL ROLE` at runtime:

```sql
GRANT cos_identity_app, cos_identity_auth TO your_service_login_role;
```

A non-psql applier (e.g. a migration runner without `\gexec`) must create the
three roles first, then apply the file with simple `:var` string substitution —
see `tests/integration/conftest.py` for a reference harness.

The `audit_log` table may be month-partitioned by the consumer if desired; the
component neither requires nor precludes it (reads are always
`ORDER BY created_at, id`).

## 3. The two-role posture (D1) — why a broker role exists

Tenant isolation is enforced by `FORCE ROW LEVEL SECURITY` under **non-owner**
roles, so cross-tenant reads are impossible from the API tier even with every
Python check removed (SC-003). Two roles:

- **`:app_role`** — every product/admin query. Strictly tenant-scoped policies
  keyed on `app.customer_id` / `app.user_role` / `app.cs_admin_scope`. No broker
  path on any table.
- **`:auth_role`** — the authn broker. Login inherently needs cross-tenant
  lookups by unique key (email, provider UID, refresh-token hash) that cannot be
  a tenant predicate. Those run under `:auth_role` with `app.identity_broker='on'`,
  entered by **exactly three** service methods — `exchange_external_token`,
  `refresh`, `accept_invitation` — and asserted by a test
  (`tests/test_broker_discipline.py`). This is the honest resolution of the FA2
  gap (login-by-unique-key) — a narrow, named, auditable role instead of a silent
  owner-role bypass.

Session vars (transaction-scoped `SET LOCAL` + `set_config(..., true)`):
`app.customer_id`, `app.user_role`, `app.user_id`, `app.cs_admin_scope` (csv),
`app.identity_broker`.

## 4. Extension hooks (what you supply)

- **`IdentityProviderPort`** — the IdP. Use the shipped `FakeIdentityProvider`
  (sim) or `providers.firebase.FirebaseIdentityProvider` (soft-imports
  `firebase_admin`; verification only, revocation at the DB layer).
- **`InviteDeliveryPort`** — invite transport. `CollectingInviteDelivery` (tests)
  or `FirebaseInviteDelivery` (Identity-Toolkit `sendOobCode`, web API key from
  the configured secret location). When the delivery component (extraction #4)
  lands, this becomes an adapter there.
- **`EntitlementsHook`** — resolves the opaque `entitlements` map carried in the
  access token. The component never interprets it (billing/entitlement is
  extraction #2).
- **`ProductHooks`** — `on_user_provisioned` (e.g. product-side worker setup) and
  the `deferred_registration` seam for guest flows. None of that logic lives in
  core.

## 5. Client contract (frontend seam)

- Store the access + refresh tokens; attach the access token as `Authorization: Bearer`.
- **Dedup refresh**: share a single in-flight refresh promise; refresh **rotates**
  the token (a new refresh is returned, the old one is revoked) — concurrent
  refreshes of one token yield exactly one new session, the rest 401.
- **401 interceptor**: on 401, attempt one refresh then retry; on repeated 401,
  clear tokens and route to sign-in (do not intercept the refresh call itself).
- `switch_tenant` re-mints the **access** token only; the refresh grant and its
  scope are unchanged, so a stale token keeps its old tenant (session-scope
  binding).

## 6. FarmAgent2 cutover notes (consumer #2, on its own clock — SC-006)

- **Tenant keys**: FA2's text farm-name keys work unchanged — the key is opaque
  and rendered nowhere; `display_name` is separate (FR-010).
- **Token continuity (D4)**: claims are a superset-compatible evolution of FA2's.
  Map FA2's `labor_tier` **into** `entitlements` at the adapter. Run a
  dual-validation window: accept both the legacy and the component-stamped
  issuer during rollover, then drop legacy once outstanding tokens expire (≤ the
  refresh TTL).
- **RLS posture flip**: FA2's admin queries currently rely on the owner-role
  bypass; adoption means routing them through `:app_role` with `app.*` set. The
  policy *shape* matches FA2's declared 018 policies, so this is a posture flip,
  not a policy redesign. Rehearse against a snapshot before cutover.
- **Pruned at extraction** (do not port): API-key middleware, `/api/internal/users`,
  legacy `/login` + `farmagent2.users`, `upgrade-labor-tier`, guest-start /
  claim-account / pre-claim-provision (these become `ProductHooks`), `connect-tickets`.

## 7. Known limitations

- **Escape-hatch rate limiter is per-process, in-memory** (D8) — "good enough v1";
  a distributed limiter is a later concern. Documented, not fixed this cycle.
- **Firebase live paths are untestable in-env** until a Firebase project + web API
  key exist; the fake provider is a first-class substitute until then.
