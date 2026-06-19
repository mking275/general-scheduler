# Technical Plan — 007-platform-accounts

**Status**: Planned  
**Date**: 2026-06-19

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│                  accounts                   │  ← NEW root entity
│   id / name / plan_tier / status / ...     │
└──────────────────┬──────────────────────────┘
                   │ 1:N
┌──────────────────▼──────────────────────────┐
│                  clinics                    │  ← EXISTING; gains account_id FK
│   id / name / color_hex / account_id / ... │
└─────────────────────────────────────────────┘
                   │ 1:N (via account_id join)
┌──────────────────▼──────────────────────────┐
│             module_licenses                 │  ← NEW; per account per MOD
│   account_id / module_id / status / ...    │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│             account_invoices                │  ← NEW; mocked billing history
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│              account_users                  │  ← NEW; admin user roster
└─────────────────────────────────────────────┘
```

---

## Technical Decisions

### TD-001: Single-Account Demo Pattern
The current demo is single-tenant. Rather than adding session/auth complexity, we continue the existing pattern: `db.get_default_account()` returns the first account row (account-demo). All `/api/account/*` routes operate on this account. Future multi-tenant support would add auth middleware here.

### TD-002: Mock Billing — No Real Stripe Calls
All `stripe_*` fields are stored as TEXT but never sent to Stripe. Invoice generation is pure SQLite. The mock payment method "Visa •••• 4242" is hardcoded in the seed. Stripe can be wired in later by replacing `seed_demo_account()` with a real Stripe customer creation.

### TD-003: Module Tier Rules Stored as Code, Not DB
The mapping of `{module_id → min_plan_tier}` lives in `backend/agents/account_agent.py` as a Python dict — not a DB table. This avoids over-engineering for a fixed set of 9 modules. If modules become dynamic, move to DB.

```python
MODULE_TIER_REQUIREMENTS = {
    "MOD-FIN": "professional", "MOD-COM": "professional",
    "MOD-INV": "professional", "MOD-TEL": "professional",
    "MOD-ANL": "professional", "MOD-MAR": "professional",
    "MOD-STF": "professional", "MOD-REF": "professional",
    "MOD-ENT": "enterprise",
}
MODULE_PRICING = {
    "MOD-FIN": 7900, "MOD-COM": 4900, "MOD-INV": 6900,
    "MOD-TEL": 8900, "MOD-ANL": 5900, "MOD-MAR": 4900,
    "MOD-STF": 5900, "MOD-REF": 2900, "MOD-ENT": 14900,
}
MODULE_DESCRIPTIONS = {
    "MOD-FIN": ("Financial Operations", "Invoice drafting, payment terminal, collections"),
    "MOD-COM": ("Client Communications", "Real SMS/email delivery via Twilio/SendGrid"),
    "MOD-INV": ("Inventory & Pharmacy", "Drug stock tracking, DEA logs, smart reorder"),
    "MOD-TEL": ("Telemedicine", "Video consultations, async triage, remote Rx"),
    "MOD-ANL": ("Analytics & BI", "Practice health score, retention cohorts, revenue mix"),
    "MOD-MAR": ("Marketing", "Review automation, social content, campaigns"),
    "MOD-STF": ("Staff & HR", "Scheduling, CE tracking, license expiry alerts"),
    "MOD-REF": ("Referral Network", "Specialist directory, referral letter generator"),
    "MOD-ENT": ("Enterprise", "Multi-location ownership, benchmarking, SSO"),
}
PLAN_PRICES = {"starter": 9900, "professional": 24900, "enterprise": 59900}
```

### TD-004: `require_module` as FastAPI Dependency
The enforcement dependency is defined once in `main.py` and used on placeholder stub routes for each MOD. When a future MOD spec is implemented, its routes already have the dependency in place.

```python
def require_module(module_id: str):
    def _check():
        account = db.get_default_account()
        if not account or account.get("status") == "trial":
            return  # demo/trial: allow all
        if not db.account_has_module(account["id"], module_id):
            _log1(f"ACCOUNT AGENT: {module_id} access denied — not licensed")
            raise HTTPException(403, f"{module_id} not licensed for this account")
    return _check
```

### TD-005: `clinics` Migration — `account_id` Column
Add via `ALTER TABLE clinics ADD COLUMN account_id TEXT` in `_init_db()`, wrapped in try/except (existing pattern). Then `seed_demo_account()` UPDATEs existing clinics to point to account-demo.

### TD-006: Invoice Number Generation
```python
def _next_invoice_number(account_id: str, year: int) -> str:
    with _get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM account_invoices WHERE account_id=? AND invoice_number LIKE ?",
            (account_id, f"INV-{year}-%")
        ).fetchone()[0]
    return f"INV-{year}-{str(count + 1).zfill(3)}"
```

### TD-007: Frontend Module State
`AccountPortal.tsx` fetches `/api/account/modules` on mount and stores the result in `useState`. Module cards render from this array — no per-component fetches needed. When a module is added/removed, the full list is re-fetched (simple, not optimistic).

### TD-008: Verbose Log Integration
All account agent actions log via `_log1()`:
- `ACCOUNT AGENT: Plan upgraded Starter → Professional`
- `ACCOUNT AGENT: MOD-FIN license added · $79/mo`
- `ACCOUNT AGENT: MOD-REF license cancelled`
- `ACCOUNT AGENT: Invoice INV-2026-003 generated · $328/mo`
- `ACCOUNT AGENT: MOD-TEL access denied — not licensed on Starter plan`

### TD-009: AccountPortal Route Design
AccountPortal is NOT a Next.js page route. It renders in the existing single-page dashboard via the `account_admin` role (same pattern as `regional_manager`). This avoids adding Next.js routing complexity.

---

## File Change Summary

### New Files
| File | Purpose |
|---|---|
| `backend/agents/account_agent.py` | AccountAgent: seed, invoice gen, module check, plan upgrade |
| `frontend/src/components/AccountPortal.tsx` | 3-tab account portal shell |
| `frontend/src/components/ModuleMarketplace.tsx` | 9 module cards with add/remove |
| `frontend/src/components/BillingPanel.tsx` | Invoice list + payment method |
| `frontend/src/components/AccountClinicsPanel.tsx` | Clinic roster + user list + add clinic form |

### Modified Files
| File | Change |
|---|---|
| `backend/repository.py` | 4 new tables in `_init_db()` + `account_id` migration on `clinics` + ~10 new methods |
| `backend/models.py` | `Account`, `ModuleLicense`, `AccountInvoice`, `AccountUser` Pydantic models |
| `backend/main.py` | 11 new routes + `require_module` dependency + startup seed call |
| `frontend/src/components/Dashboard.tsx` | `account_admin` role + AccountPortal rendering + status banner |
| `frontend/src/components/RoleSelector.tsx` | 5th "⚙ Account" tab |

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `ALTER TABLE clinics ADD COLUMN account_id` fails on existing DB | Wrapped in try/except (existing pattern) |
| `seed_demo_account()` called on every restart and duplicates data | Guard: `if count > 0: return` before any inserts |
| AccountPortal crashes if `/api/account` returns 404 | Guard on frontend: show "Setting up account..." skeleton if response is null |
| `require_module` blocks existing routes on re-order | Only applied to NEW stub routes for future MODs — not on any existing routes |
| Dashboard `role === 'account_admin'` breaks TypeScript | Extend the `Role` type union to include `'account_admin'` |
