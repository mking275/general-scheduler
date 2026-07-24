# cos_identity — Identity & RBAC Core (C7)

**Maturity**: beta (spec 008 implemented; vendoring documented) · **Kind**: source-only Python package, vendored by products · **Contract**: C7 (`specs/004-chief-of-staff-pattern-v1/contracts/identity-rbac.md`)

Every COS product needs the same identity layer: external-IdP sign-in exchanged
for an internal session, a ranked platform-role vocabulary, customer-admin
(invites, suspension, audit), support-staff cross-tenant scoping, and tenant
isolation enforced by the database. This component is that layer, extracted from
the proven FarmAgent2 shape, pruned of product coupling, with row-level security
**actually forced** under a non-owner role.

## What it provides

1. **Role vocabulary** (canonical, ranked): `superuser > cs_admin > agent > viewer`,
   plus the orthogonal `customer_role` axis (`account_owner | member`). One rank
   table (`cos_identity.roles`); C6 audiences and C4 policies read it.
2. **Sessions**: IdP sign-in → internal HS256 pair (short-lived access +
   server-side-revocable, rotating refresh). Claims: `sub, email, role,
   customer_id` (opaque tenant key), `customer_name, customer_role,
   cs_admin_scope, entitlements` (opaque product map), `token_type, iat, exp, iss`.
3. **Customer-admin**: invite lifecycle, suspend/reactivate (revokes internal +
   provider sessions), immutable audit with deterministic reads.
4. **Tenant isolation**: `ENABLE + FORCE ROW LEVEL SECURITY` on all six tables
   under two non-owner roles; the wall holds with every app-layer check removed
   (SC-003).

## API surface

- `IdentitySettings` — the one config contract (`from_env()` or explicit).
- `IdentityService(store, provider, settings, *, invite_delivery, entitlements_hook, product_hooks)`
  — `exchange_external_token`, `accept_invitation`, `refresh`, `logout`,
  `invite`/`resend_invitation`, `patch_user`, `suspend`/`reactivate`,
  `switch_tenant`, `escape_hatch_login`, `create_tenant`/`list_tenants`,
  `list_users`/`list_invitations`/`read_audit`, `assign_support`.
- `PgStore` / `InMemoryStore` (one `Store` protocol) · `AuditLog`.
- Ports: `IdentityProviderPort`, `InviteDeliveryPort`, `EntitlementsHook`,
  `ProductHooks`. Shipped adapters: `FakeIdentityProvider` + `CollectingInviteDelivery`
  (sim/tests), `providers.firebase` (soft-imports `firebase_admin`).
- `cos_identity.fastapi_ext`: `build_auth_router(service)`,
  `build_admin_router(service)`, `require_role(min)` / `require_superuser` /
  `require_cs_admin` (import only when FastAPI is installed).
- SQL: `cos_identity/sql/001_identity_schema.sql` (psql `\set`-parameterized).

The core (`settings/roles/tokens/passwords/models/ports/service/store/tenancy/audit`)
imports **without** FastAPI or `firebase_admin` on the path.

## Install (vendor)

Copy `components/identity/cos_identity/` into the consumer repo. Runtime deps:
`PyJWT`, `bcrypt`, `pydantic` v2, `asyncpg` (for `PgStore`); optional `fastapi`
(the extra) and `firebase_admin` (the Firebase adapter).

## Quickstart (fake provider — no Firebase project needed)

```python
from cos_identity import IdentitySettings, IdentityService, InMemoryStore, FakeIdentityProvider, make_fake_token

svc = IdentityService(InMemoryStore(), FakeIdentityProvider(),
                      IdentitySettings(jwt_secret="...", seed_superuser_email="admin@you.example"))
pair = await svc.exchange_external_token(make_fake_token("uid-1", "admin@you.example"))
# pair.access_token / pair.refresh_token / pair.user
```

Mount in FastAPI: set `app.state.identity_settings = settings`, then
`app.include_router(build_auth_router(svc), prefix="/api/auth")` and
`build_admin_router(svc)` under your own prefix.

## Tests

- Unit tier (no infra): `pytest components/identity/tests -m "not integration"`.
- Integration tier (Postgres): set `TEST_DATABASE_URL`, then `pytest components/identity/tests -m integration`.
  Skips cleanly when unset. `test_rls_wall.py` proves SC-003; `test_audit_order.py`
  proves SC-004.

Full vendoring guide, DDL recipe, two-role posture, and FA2 cutover notes:
[`vendoring.md`](./vendoring.md).
