# VPMA Platform — Account & Subscription Management Design

**Feature**: platform-accounts (spec-007)
**Date**: 2026-06-19
**Status**: Approved — proceeding to speckit

---

## What This Is

VPMA is a SaaS product. Vet practices (our customers) need to:
1. Subscribe to VPMA and pay a recurring fee
2. Purchase add-on modules (MOD-FIN, MOD-COM, etc.) on top of their base plan
3. Self-manage their account — update billing, see invoices, add clinics, manage module access

This is a new layer above the existing `clinics` table.
- **Account** = the legal entity / practice group that pays for VPMA (can own many clinics)
- **Clinic** = a physical location (already exists; gains `account_id` FK)

> This is VPMA billing its own customers. Separate from MOD-FIN (vet billing their clients).

---

## Tenant Model

```
Account  ("Paws & Claws Veterinary Group")
  ├── Clinic A  (clinic-downtown)
  └── Clinic B  (clinic-westside)

Account has:
  - Plan tier       (Starter / Professional / Enterprise)
  - Module licenses ([MOD-FIN, MOD-COM] purchased add-ons)
  - Billing         (Stripe customer — mocked in demo)
  - Users           (account admins — practice owner / office manager)
```

---

## Approved Design Decisions

1. **Account is the top-level tenant** — clinics become children via `account_id` FK
2. **Mock billing for demo** — invoice rows generated in SQLite; no real Stripe calls; Stripe IDs stored for future live wiring
3. **Module licenses are per-account** — not per-clinic; unlocks MOD for all clinics under that account
4. **Trial mode** — demo seeds one account in `trial` status with all 9 modules licensed (so the demo is always fully featured)
5. **UI entry point** — new `Account Admin` tab in RoleSelector + "Account & Billing" option in the floating ⚙ menu

---

## Pricing Tiers

| Tier | Price | Clinics | Add-ons |
|---|---|---|---|
| **Starter** | $99/mo | 1 | None (base only) |
| **Professional** | $249/mo | ≤ 5 | P1 modules available |
| **Enterprise** | $599/mo | Unlimited | All modules; MOD-ENT included |

## Add-On Module Pricing

| Module | Price |
|---|---|
| MOD-FIN Financial Operations | $79/mo |
| MOD-COM Client Communications | $49/mo |
| MOD-INV Inventory & Pharmacy | $69/mo |
| MOD-TEL Telemedicine | $89/mo |
| MOD-ANL Analytics & BI | $59/mo |
| MOD-MAR Marketing | $49/mo |
| MOD-STF Staff & HR | $59/mo |
| MOD-REF Referral Network | $29/mo |
| MOD-ENT Enterprise | $149/mo (included in Enterprise tier) |

---

## New Database Tables

### `accounts`
| Field | Type | Notes |
|---|---|---|
| id | TEXT PK | "account-demo" for seed |
| name | TEXT | "Paws & Claws Vet Group" |
| contact_name | TEXT | Practice owner |
| contact_email | TEXT UNIQUE | Billing email |
| contact_phone | TEXT | |
| address | TEXT | |
| plan_tier | TEXT | starter / professional / enterprise |
| status | TEXT | trial / active / past_due / suspended / cancelled |
| trial_ends_at | TEXT | ISO datetime |
| created_at | TEXT | ISO datetime |
| stripe_customer_id | TEXT | Mocked in demo |
| stripe_subscription_id | TEXT | Mocked in demo |

### `module_licenses`
| Field | Type | Notes |
|---|---|---|
| id | TEXT PK | |
| account_id | TEXT | FK → accounts.id |
| module_id | TEXT | MOD-FIN / MOD-COM / etc. |
| status | TEXT | active / suspended / cancelled |
| billing_interval | TEXT | monthly / annual |
| price_cents | INTEGER | e.g. 7900 for $79/mo |
| purchased_at | TEXT | ISO datetime |
| expires_at | TEXT | NULL = auto-renewing |
| stripe_subscription_item_id | TEXT | Mocked |
| UNIQUE | (account_id, module_id) | |

### `account_invoices`
| Field | Type | Notes |
|---|---|---|
| id | TEXT PK | |
| account_id | TEXT | FK → accounts |
| invoice_number | TEXT | e.g. "INV-2026-001" |
| period_start | TEXT | ISO date |
| period_end | TEXT | ISO date |
| line_items | TEXT | JSON [{description, amount_cents}] |
| subtotal_cents | INTEGER | |
| total_cents | INTEGER | |
| status | TEXT | pending / paid / failed / void |
| stripe_invoice_id | TEXT | Mocked |
| paid_at | TEXT | ISO datetime |
| created_at | TEXT | ISO datetime |

### `account_users`
| Field | Type | Notes |
|---|---|---|
| id | TEXT PK | |
| account_id | TEXT | FK → accounts |
| name | TEXT | |
| email | TEXT | |
| role | TEXT | admin / member |
| created_at | TEXT | |
| UNIQUE | (account_id, email) | |

---

## Access Enforcement Pattern

```python
def require_module(module_id: str):
    """FastAPI dependency — raises 403 if account doesn't have module licensed."""
    def _check():
        account = db.get_default_account()
        if not account:
            return  # demo mode: allow all
        if not db.account_has_module(account["id"], module_id):
            raise HTTPException(
                status_code=403,
                detail=f"{module_id} is not enabled. Upgrade at /account/modules."
            )
    return _check
```

---

## New API Routes

| Method | Route | Purpose |
|---|---|---|
| GET | /api/account | Get account + plan + status |
| PUT | /api/account | Update contact info |
| GET | /api/account/modules | All 9 modules with license status + pricing |
| POST | /api/account/modules/{module_id} | Purchase module license |
| DELETE | /api/account/modules/{module_id} | Cancel module license |
| GET | /api/account/invoices | List invoices (newest first) |
| GET | /api/account/invoices/{id} | Single invoice detail |
| GET | /api/account/clinics | All clinics under this account |
| POST | /api/account/clinics | Add new clinic (Professional+ only) |
| GET | /api/account/plan | Current plan details + upgrade options |
| POST | /api/account/plan/upgrade | Change plan tier |

---

## New Frontend Components

| Component | Purpose |
|---|---|
| `AccountPortal.tsx` | Full-screen 3-tab panel: Plan & Modules / Billing / Account & Clinics |
| `ModuleMarketplace.tsx` | 9 module cards with license status, price, Add/Remove |
| `BillingPanel.tsx` | Invoice list + payment method display |
| `AccountClinicsPanel.tsx` | Clinic roster management |

Dashboard changes:
- `account_admin` added to Role type
- Floating ⚙ menu gains "Account & Billing" option
- `RoleSelector.tsx` gets 5th "Account Admin" tab
- Trial countdown banner when `status === 'trial'`

---

## Seed Data

```python
demo_account = {
    "id": "account-demo",
    "name": "Paws & Claws Veterinary Group",
    "contact_name": "Dr. Sarah Mitchell",
    "contact_email": "admin@pawsandclaws.demo",
    "plan_tier": "professional",
    "status": "trial",
    "trial_ends_at": NOW + 14 days,
}
# All 9 modules licensed in trial — full demo
# clinic-downtown + clinic-westside assigned to account-demo
# 2 seeded invoices (one paid, one pending)
# 2 seeded account users (admin + member)
```
