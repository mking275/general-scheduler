# VPMA Platform — Account & Subscription Management
## Spec: 007-platform-accounts

**Version**: 1.0  
**Status**: Specified  
**Date**: 2026-06-19  
**Constitution**: `.specify/memory/constitution.md`

---

## Problem Statement

VPMA is a SaaS product but currently has no concept of "customer." Every vet practice using VPMA is an undifferentiated tenant — there's no account, no subscription, no module gating, and no way for a practice owner to manage what they've purchased. 

This feature adds the foundational commercial layer: the `Account` entity (the paying vet practice group), subscription tiers, per-account module licensing, invoice generation, and a self-service Account Portal UI.

---

## User Stories

### US1 — Practice Owner Can View Their Account and Plan
**As a** practice owner (account admin),  
**I want to** see my current VPMA plan, subscription status, and trial countdown,  
**So that** I know what I'm paying for and when my trial ends.

**Acceptance Criteria:**
- Account portal accessible via "Account Admin" role in RoleSelector
- Displays account name, contact details, plan tier badge
- Shows trial countdown banner if status = 'trial'
- Shows warning banner if status = 'past_due'
- Plan tier: Starter / Professional / Enterprise with feature list

**Priority**: P1 — MVP

---

### US2 — Practice Owner Can Manage Module Licenses
**As a** practice owner,  
**I want to** see all available VPMA add-on modules with their prices, and enable or disable them,  
**So that** I can control which features my practice has access to.

**Acceptance Criteria:**
- Module marketplace shows all 9 MODs as cards
- Each card shows: name, description, price/month, current status (Active / Not Licensed)
- "Add" button → confirms purchase → module becomes active immediately
- "Remove" button → confirm dialog → module deactivated
- Module cards are greyed/locked when plan tier doesn't allow them (e.g. Starter can't add any modules)
- Frontend mirrors access: locked module features show "Upgrade" prompt, not a broken UI

**Priority**: P1 — MVP

---

### US3 — Practice Owner Can View Invoices
**As a** practice owner,  
**I want to** see a history of my VPMA invoices with line items and payment status,  
**So that** I can reconcile my accounting and confirm payments.

**Acceptance Criteria:**
- Invoice list shows: invoice number, period, total, status (Paid / Pending / Failed)
- Expandable row shows line items (base plan + each active module)
- Invoices generated monthly from seed data (2 seeded: one paid, one pending)
- Mock payment method displayed ("Visa •••• 4242")

**Priority**: P1 — MVP

---

### US4 — Practice Owner Can Manage Clinics and Users
**As a** practice owner,  
**I want to** see all clinics under my account and manage account users,  
**So that** I can onboard new locations and control who has admin access.

**Acceptance Criteria:**
- Clinic roster: name, color, address, status — each links to that clinic's schedule
- "+ Add Clinic" button visible (active on Professional+; locked with tooltip on Starter)
- Account users list: name, email, role (Admin / Member)
- Seeded with Dr. Sarah Mitchell (admin) + one member user

**Priority**: P2

---

### US5 — Module Access is Enforced at the API Level
**As a** VPMA platform,  
**I want to** reject requests to module-specific routes if the account doesn't have that module licensed,  
**So that** unlicensed features can't be accessed even by direct API calls.

**Acceptance Criteria:**
- FastAPI `require_module(module_id)` dependency defined in main.py
- Returns HTTP 403 with clear message if module not licensed
- In demo/trial mode (status = 'trial'), all modules are allowed
- Applied to placeholder stub routes for each MOD (forward-plumbing for future MOD builds)
- Verbose Log emits: `ACCOUNT AGENT: MOD-FIN access denied — not licensed`

**Priority**: P2

---

### US6 — Plan Upgrade Flow
**As a** practice owner,  
**I want to** upgrade my plan tier,  
**So that** I can unlock more clinics or module tiers.

**Acceptance Criteria:**
- Plan panel shows current tier and the next tier up with price delta
- "Upgrade to Professional" / "Upgrade to Enterprise" CTA buttons
- Clicking upgrade: updates account.plan_tier, generates a pro-rated invoice line item
- Verbose Log emits: `ACCOUNT AGENT: Plan upgraded Starter → Professional`

**Priority**: P3

---

## Functional Requirements

### FR-ACC-001 — Account Entity
- One account per vet practice group (the paying legal entity)
- Account owns N clinics (1:many — existing clinics get account_id FK)
- Account has: name, contact info, plan tier, status, Stripe IDs (mocked), trial dates

### FR-ACC-002 — Account Status Lifecycle
```
trial → active → past_due → suspended → cancelled
```
- `trial`: all features unlocked for N days; banner shown
- `active`: subscription current; licensed modules unlocked
- `past_due`: payment failed; 7-day grace; warning banner
- `suspended`: grace expired; read-only access (not enforced in demo)
- `cancelled`: churned; data retained

### FR-ACC-003 — Module License Gating
- `module_licenses` table: one row per (account, module) pair
- `account_has_module(account_id, module_id)` → bool
- FastAPI dependency `require_module(module_id)` enforces on protected routes
- Frontend reads `/api/account/modules` to render enabled/disabled states

### FR-ACC-004 — Invoice Generation
- Invoices generated from plan tier + active module licenses
- Line items: base plan ($99/$249/$599) + each active module ($N/mo each)
- Status: pending → paid (mocked in demo — no real payment processing)
- Two seeded invoices: one paid (last month), one pending (current month)

### FR-ACC-005 — Seed Demo Account
- Single demo account seeded on startup if accounts table is empty
- Plan: Professional, Status: trial (14 days remaining)
- All 9 modules licensed (full demo visibility)
- Assign clinic-downtown + clinic-westside to this account

### FR-ACC-006 — Account Portal UI
- Accessible via "Account Admin" role in RoleSelector (5th tab)
- Also accessible via floating ⚙ → "Account & Billing"
- Three sub-tabs: Plan & Modules / Billing / Account & Clinics
- No Tailwind; Vanilla CSS only; dark theme matching existing UI

---

## Out of Scope

- Real Stripe payment processing (Stripe IDs stored but calls are mocked)
- Multi-user auth / login system (single-user demo as before)
- Per-clinic module licensing (always per-account)
- Cancellation flows with data export
- Tax calculation

---

## Demo Flow (60 seconds)

1. Click "Account Admin" tab → AccountPortal loads
2. **Plan & Modules tab**: shows "Professional — Trial (12 days left)" banner; 9 module cards all Active
3. Click "Remove" on MOD-REF → confirm → card flips to "Add ($29/mo)"
4. Navigate to a feature that requires MOD-REF → see "Upgrade" prompt instead of broken UI
5. **Billing tab**: shows 2 invoices — last month Paid ✅, current month Pending ⏳; expand to see line items
6. **Account & Clinics tab**: shows both clinic locations + 2 users

---

## Success Criteria

- All 11 new API routes return correct data (GET) or mutate correctly (POST/DELETE/PUT)
- Module licensing enforced: 403 returned for unlicensed modules
- AccountPortal renders all 3 tabs without errors
- TypeScript compiles clean
- No new npm packages (lucide-react icons already installed)
- Seeded demo account appears correct on fresh DB start
