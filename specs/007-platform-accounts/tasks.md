# Tasks — 007-platform-accounts

**Total**: 52 tasks across 9 phases  
**Status**: Ready for implementation

---

## Phase 1 — Schema & Models (T001–T008)
*Foundation — must complete before any other phase*

- [ ] T001 In `backend/repository.py` `_init_db()`, add 4 new CREATE TABLE IF NOT EXISTS statements: `accounts`, `module_licenses`, `account_invoices`, `account_users` (see data-model.md for exact SQL)
- [ ] T002 In `backend/repository.py` `_init_db()`, add `ALTER TABLE clinics ADD COLUMN account_id TEXT` wrapped in try/except (existing pattern)
- [ ] T003 In `backend/models.py`, add 7 new Pydantic models: `Account`, `ModuleLicense`, `AccountInvoice`, `AccountUser`, `AccountUpdateRequest`, `ModuleSubscribeRequest`, `PlanUpgradeRequest` (see data-model.md for exact fields). **W-05 fix**: `ModuleSubscribeRequest.billing_interval` must have a default of `"monthly"` so the body is fully optional
- [ ] T004 In `backend/main.py` imports, add the 6 new models to the `from .models import ...` line
- [ ] T005 In `backend/main.py`, add `require_module(module_id: str)` dependency function (see plan.md TD-004 for exact implementation)
- [ ] T006 In `backend/repository.py`, import `Account`, `ModuleLicense`, `AccountInvoice`, `AccountUser` from models
- [ ] T007 Verify backend restarts cleanly after T001–T006 by checking `curl http://127.0.0.1:8080/api/session` returns 200
- [ ] T008 Mark Phase 1 complete with git commit: `feat(accounts): Phase 1 — schema + models`

---

## Phase 2 — Repository Methods (T009–T020)
*All DB access methods for account entities*

- [ ] T009 Add `get_default_account() -> Optional[dict]` — SELECT first row from accounts ORDER BY created_at ASC LIMIT 1
- [ ] T010 Add `get_account(account_id: str) -> Optional[dict]`
- [ ] T011 Add `create_account(account: Account) -> dict` — INSERT OR IGNORE
- [ ] T012 Add `update_account(account_id: str, updates: dict) -> Optional[dict]` — allowed keys: name, contact_name, contact_email, contact_phone, address, plan_tier, status
- [ ] T013 Add `get_module_licenses(account_id: str) -> list` — all rows for account
- [ ] T014 Add `account_has_module(account_id: str, module_id: str) -> bool` — COUNT > 0 WHERE status='active'
- [ ] T015 Add `add_module_license(account_id: str, module_id: str, price_cents: int, interval: str) -> dict` — INSERT OR REPLACE
- [ ] T016 Add `cancel_module_license(account_id: str, module_id: str) -> bool` — UPDATE status='cancelled'
- [ ] T017 Add `get_account_invoices(account_id: str) -> list` — ORDER BY created_at DESC
- [ ] T018 Add `get_account_invoice(invoice_id: str) -> Optional[dict]` — parse line_items JSON on read
- [ ] T019 Add `create_account_invoice(invoice: dict) -> dict` — json.dumps(line_items) on write
- [ ] T020 Add `get_account_users(account_id: str) -> list`
- [ ] T020b Add `get_clinics_for_account(account_id: str) -> list` — SELECT * FROM clinics WHERE account_id=?
- [ ] T009b **B-02 fix** — Add `set_clinic_account(clinic_id: str, account_id: str) -> None` — `UPDATE clinics SET account_id=? WHERE id=?`; used by T037 after create_clinic and by seed_demo_account

---

## Phase 3 — Account Agent & Seed (T021–T028)
*Business logic and demo data*

- [ ] T021 Create `backend/agents/account_agent.py` with constants: `MODULE_TIER_REQUIREMENTS`, `MODULE_PRICING`, `MODULE_DESCRIPTIONS`, `PLAN_PRICES` dicts (see plan.md TD-003 for exact values)
- [ ] T022 In `account_agent.py`, implement `seed_demo_account(db, log_fn)` — **W-02 fix**: split guard:
  - Create account only if not exists: `if not db.get_default_account(): db.create_account(demo_account)`
  - Always run: `UPDATE clinics SET account_id='account-demo' WHERE account_id IS NULL` (catches new clinics added after first seed)
  - Seed all 9 module_licenses as active (INSERT OR IGNORE — idempotent)
  - Seed 2 account_invoices (INSERT OR IGNORE — INV-2026-001 paid June, INV-2026-002 pending July)
  - Seed 2 account_users (INSERT OR IGNORE — Dr. Sarah Mitchell admin, James Kowalski member)
  - log_fn("ACCOUNT AGENT: Demo account seeded — Paws & Claws Veterinary Group")
- [ ] T023 In `account_agent.py`, implement `get_modules_with_status(db, account_id: str) -> list`:
  - For each of 9 modules in MODULE_PRICING.keys():
    - Check if licensed (db.account_has_module)
    - Return dict with: module_id, name, description, price_cents, tier_required, licensed, license_status, purchased_at
- [ ] T024 In `account_agent.py`, implement `compute_trial_days_remaining(trial_ends_at: str) -> int`
- [ ] T025 In `account_agent.py`, implement `validate_module_add(account: dict, module_id: str) -> Optional[str]`:
  - Returns error string if blocked, None if allowed
  - Check trial (always allowed), plan tier vs MODULE_TIER_REQUIREMENTS, already active check
- [ ] T026 In `account_agent.py`, implement `generate_invoice_line_items(account: dict, licenses: list) -> list`:
  - Base plan line item from PLAN_PRICES[account["plan_tier"]]
  - One line item per active module_license
  - Returns [{description, amount_cents}]
- [ ] T027 In `account_agent.py`, implement `next_invoice_number(db, account_id: str) -> str` (see plan.md TD-006)
- [ ] T028 In `backend/main.py` `on_startup`, add call: `from .agents.account_agent import seed_demo_account; seed_demo_account(db, _log1)` — after existing seed calls, wrapped in try/except

---

## Phase 4 — API Routes (T029–T041)
*All 11 + 9 stub routes in main.py*

- [ ] T029 Add `GET /api/account` — call db.get_default_account(), compute trial_days_remaining, attach active_module_count; 404 if no account
- [ ] T030 Add `PUT /api/account` — body: AccountUpdateRequest; call db.update_account(); log_fn
- [ ] T031 Add `GET /api/account/modules` — call account_agent.get_modules_with_status(); return list
- [ ] T032 Add `POST /api/account/modules/{module_id}` — **W-05 fix**: signature `async def _(module_id: str, body: ModuleSubscribeRequest = Body(default=ModuleSubscribeRequest()))` so empty body is accepted; validate_module_add() → 403/409 on error; db.add_module_license(); log_fn("ACCOUNT AGENT: {module_id} license added · ${price/100}/mo")
- [ ] T033 Add `DELETE /api/account/modules/{module_id}` — db.cancel_module_license(); 404 if not found; log_fn("ACCOUNT AGENT: {module_id} license cancelled")
- [ ] T034 Add `GET /api/account/invoices` — db.get_account_invoices(account["id"]); parse line_items JSON
- [ ] T035 Add `GET /api/account/invoices/{invoice_id}` — db.get_account_invoice(invoice_id); 404 if not found
- [ ] T036 Add `GET /api/account/clinics` — db.get_clinics_for_account(account["id"])
- [ ] T037 Add `POST /api/account/clinics` — check plan tier (Professional+, else 403); build Clinic model from request body; call db.create_clinic(clinic); then call **db.set_clinic_account(clinic.id, account["id"])** (B-02 fix); return 201 with clinic dict
- [ ] T038 Add `GET /api/account/plan` — return current tier, price, upgrade/downgrade options
- [ ] T039 Add `POST /api/account/plan/upgrade` — body: PlanUpgradeRequest; validate target tier; db.update_account plan_tier; if upgrading to Enterprise, auto-add MOD-ENT license; log_fn; return summary
- [ ] T040 Add 9 module stub routes `GET /api/mods/{mod_slug}/status` for each MOD: fin, com, inv, tel, anl, mar, stf, ref, ent — each with `Depends(require_module("MOD-XYZ"))` and returns `{"module": "MOD-XYZ", "access": "granted"}`
- [ ] T041 Verify all routes with smoke test curl commands (see quickstart.md section below)

---

## Phase 5 — Frontend: AccountPortal Shell (T042–T045)
*Portal frame, role integration, tab navigation*

- [ ] T042 In `frontend/src/components/RoleSelector.tsx`: **B-01 fix** — update `type Role` union to add `'account_admin'` in all 3 files: `RoleSelector.tsx` (line 3), `Dashboard.tsx` (line 16), `page.tsx` (line 12). Then add 5th tab object `{ id: "account_admin", label: "⚙ Account", icon: "⚙️" }` to the roles array in RoleSelector with indigo accent styling (#818cf8), distinct from clinical role tabs
- [ ] T043 In `frontend/src/components/Dashboard.tsx`:
  - **B-01 fix**: `Role` type union already updated in T042 — do NOT re-define it here
  - Add rendering block in the slide panel area: `role === 'account_admin'` → render `<AccountPortal onBack={() => onRoleChange('front_desk')} />`
  - Update existing floating ⚙ button (currently navigates to `'settings' as any`) to show a mini-menu: "Integrations & Migration" → `onRoleChange('settings' as any)` (keep existing) + "Account & Billing" → `onRoleChange('account_admin')`
  - Add account status banner: fetch `/api/account` on mount, if `status === 'past_due'` show red banner at top; if `status === 'trial'` show amber trial banner with days_remaining
- [ ] T044 Create `frontend/src/components/AccountPortal.tsx`:
  - Fetches `/api/account` on mount; shows skeleton while loading
  - 3 sub-tab nav: "📋 Plan & Modules" | "🧾 Billing" | "🏥 Account & Clinics"
  - Routes sub-tab content to: `<ModuleMarketplace />` | `<BillingPanel />` | `<AccountClinicsPanel />`
  - Account name + plan badge in portal header
  - Trial countdown strip if status === 'trial'
  - Dark theme; glassmorphism card style matching existing UI
- [ ] T045 Test AccountPortal renders without errors; TypeScript compiles

---

## Phase 6 — Frontend: Module Marketplace (T046–T049)
*Module cards with add/remove/upgrade*

- [ ] T046 Create `frontend/src/components/ModuleMarketplace.tsx`:
  - Fetches `/api/account/modules` on mount
  - Renders 3×3 grid of module cards (one per MOD)
  - Each card: module name, emoji icon, one-line description, price badge, status chip
  - Status chip variants: `✅ Active` (green) | `➕ Add ($X/mo)` (indigo button) | `🔒 Upgrade Plan` (grey, tooltip) | `❌ Cancelled` (red muted)
  - "Add" → POST /api/account/modules/{id} → re-fetch list
  - "Remove" → confirm dialog (inline) → DELETE /api/account/modules/{id} → re-fetch list
  - "Upgrade Plan" → calls `onTabChange('plan')` to navigate to Plan tab (not implemented yet — just scroll to plan section)
  - All mutations show spinner on the card while in-flight
- [ ] T047 Module emoji map: MOD-FIN 💰 | MOD-COM 📨 | MOD-INV 💊 | MOD-TEL 📹 | MOD-ANL 📊 | MOD-MAR 📣 | MOD-STF 👥 | MOD-REF 🔗 | MOD-ENT 🏢
- [ ] T048 Plan tier display at top of marketplace: current tier chip + "X of 9 modules active" counter
- [ ] T049 Test: add MOD-REF (not in trial license) → card shows Active; remove it → shows Add button

---

## Phase 7 — Frontend: Billing Panel (T050–T052)
*Invoice list and payment method*

- [ ] T050 Create `frontend/src/components/BillingPanel.tsx`:
  - Fetches `/api/account/invoices` on mount
  - Mock payment method card: "Visa •••• 4242 — expires 08/28" (hardcoded in component)
  - Invoice table: invoice number | period | total | status badge
  - Expandable row: click → inline expand shows line items with amounts
  - Status badges: `✅ Paid` (green) | `⏳ Pending` (amber) | `❌ Failed` (red)
  - Empty state: "No invoices yet"
- [ ] T051 Format amounts: `(amount_cents / 100).toFixed(2)` → display as "$X.XX"
- [ ] T052 Test: 2 invoices show (INV-2026-001 Paid, INV-2026-002 Pending); expand each to see line items

---

## Phase 8 — Frontend: Account & Clinics Panel (T053–T056)
*Clinic roster, user list, add clinic form*

- [ ] T053 Create `frontend/src/components/AccountClinicsPanel.tsx`:
  - Fetches `/api/account/clinics` and `/api/account` on mount
  - **Clinic roster section**: card per clinic with color dot, name, address, status toggle (is_active)
  - **Add Clinic button**: shown if plan_tier !== 'starter'; opens inline form (name, address, color picker); submit → POST /api/account/clinics → re-fetch
  - **Starter locked state**: button greyed, hover tooltip "Upgrade to Professional to add locations"
  - **Account Users section**: list of users from seeded data (no edit in demo — display only)
  - **Account contact details**: editable inline form; submit → PUT /api/account → success toast
- [ ] T054 Color picker for new clinic: simple 6 preset swatches (`#6C63FF`, `#00BFA6`, `#F59E0B`, `#EF4444`, `#10B981`, `#8B5CF6`)
- [ ] T055 Test: both existing clinics show; add clinic form submits; new clinic appears in ClinicSwitcher after page refresh
- [ ] T056 Test: contact details update saves and reflects in portal header

---

## Phase 9 — Polish, Git, Smoke Test (T057–T062)
*Verification and commit*

- [ ] T057 Smoke test all API routes:
  ```bash
  curl http://127.0.0.1:8080/api/account
  curl http://127.0.0.1:8080/api/account/modules
  curl http://127.0.0.1:8080/api/account/invoices
  curl http://127.0.0.1:8080/api/account/clinics
  curl http://127.0.0.1:8080/api/account/plan
  curl -X POST http://127.0.0.1:8080/api/account/modules/MOD-REF -H 'Content-Type: application/json' -d '{}'
  curl -X DELETE http://127.0.0.1:8080/api/account/modules/MOD-REF
  curl http://127.0.0.1:8080/api/mods/fin/status
  ```
- [ ] T058 Verify `require_module` enforcement: cancel MOD-FIN license, hit `/api/mods/fin/status`, confirm 403 response
- [ ] T059 TypeScript build check: `cd frontend && npx tsc --noEmit` — must produce 0 errors
- [ ] T060 Verbose Log check: open AccountPortal, add/remove a module — confirm ACCOUNT AGENT lines appear in VerboseLog panel
- [ ] T061 Fresh DB test: delete `backend/scheduler.db`, restart backend, confirm seed runs and `/api/account` returns demo account
- [ ] T062 Git commit + push: `feat(accounts): spec-007 platform-accounts complete — 52 tasks`
