# speckit.analyze — 007-platform-accounts
## Analysis Report

**Date**: 2026-06-19  
**Result**: 2 Blockers, 5 Warnings — all self-resolved below

---

## 🔴 Blockers

### B-01: `Role` type is defined in TWO places — both must be updated
**Finding**: `type Role` is defined independently in both `page.tsx` (line 12) and `Dashboard.tsx` (line 16), and also in `RoleSelector.tsx` (line 3). All three use `"front_desk" | "vet_tech" | "vet" | "regional_manager"` as a literal union. Adding `'account_admin'` to only one will cause TypeScript errors.

**Resolution**: T042 and T043 must update the `Role` type in **all three files**: `page.tsx`, `Dashboard.tsx`, and `RoleSelector.tsx`. Additionally, the `"settings"` role is already used in Dashboard via `("settings" as any)` cast — that's the existing Integrations/Migration panel. The new `account_admin` role follows the same pattern but should be added cleanly to the type union to avoid proliferating `as any` casts.

**Fix applied to tasks.md**: T042 explicitly states "update Role type in RoleSelector.tsx, Dashboard.tsx, and page.tsx". T043 updated similarly.

---

### B-02: `create_clinic` in repository doesn't accept `account_id`
**Finding**: `db.create_clinic(clinic: Clinic)` (repository.py:825) takes a `Clinic` model that has no `account_id` field. The `POST /api/account/clinics` route (T037) needs to set `account_id` on the new clinic after creation, or the `Clinic` model must be extended.

**Resolution**: The cleanest fix (no model change needed): after `db.create_clinic(clinic)`, do a direct `UPDATE clinics SET account_id=? WHERE id=?` to assign the account. Add this as a new `db.set_clinic_account(clinic_id, account_id)` method — one line of SQL.

**Fix applied to tasks.md**: T009b added: `def set_clinic_account(clinic_id: str, account_id: str)`. T037 updated to call it after create_clinic.

---

## 🟡 Warnings

### W-01: Floating settings button uses `onRoleChange("settings" as any)`
**Finding**: The existing Batch 0 floating ⚙ button (Dashboard.tsx:298) navigates to the settings view via `onRoleChange("settings" as any)` — a type cast hack. Adding `account_admin` as a real type is the right fix; but care must be taken that the existing `"settings"` string (for Integrations/Migration) doesn't break when we clean up the types.

**Resolution**: Keep `"settings"` as a separate internal role string (it already works as `as any`). Add `"account_admin"` to the proper Role union. The two views (settings panel and account portal) are separate roles, separate views. No conflict.

---

### W-02: `seed_demo_account()` UPDATE clinics may run before clinics are seeded
**Finding**: `on_startup` calls seeds in order: patients → clinics → westside → phase3 → integration_definitions → (new) seed_demo_account. `seed_demo_account` does `UPDATE clinics SET account_id=...` but clinics are seeded by the earlier call. **Order is correct** — but the guard `if db.get_default_account(): return` must only skip account creation, not the `UPDATE clinics` step, since clinics might have been added after the account was first seeded.

**Resolution**: Separate the guard: create account only if it doesn't exist, but always run `UPDATE clinics SET account_id='account-demo' WHERE account_id IS NULL` (so new clinics added later also get assigned). Task T022 updated to reflect this.

---

### W-03: `get_clinics_for_account` needs to handle the `account_id IS NULL` edge case
**Finding**: After migration, `clinics.account_id` starts as NULL for all existing clinics until `seed_demo_account()` runs. If `GET /api/account/clinics` runs before startup completes (e.g. in tests), it returns empty.

**Resolution**: The `seed_demo_account()` guard handles this. No additional change needed — document in task T036 that the route assumes seed has run.

---

### W-04: `RoleSelector.tsx` has hardcoded 4 roles — adding 5th changes layout
**Finding**: RoleSelector renders roles from a fixed array of 4. A 5th tab needs to fit without overflowing the header. The existing tabs use flex layout — should be fine, but the "⚙ Account" tab should use a shorter label to prevent wrapping on smaller screens.

**Resolution**: Use label "⚙ Account" (short). Task T042 specifies this label. No layout change needed.

---

### W-05: `POST /api/account/modules/{module_id}` body is optional — FastAPI may reject empty body
**Finding**: The contract shows `{ "billing_interval": "monthly" }` as the request body, but the task for T032 says "body: ModuleSubscribeRequest". If the caller sends no body at all, FastAPI raises a 422. The demo UI will always send a body, but the smoke test in T057 sends `{}`.

**Resolution**: Make `ModuleSubscribeRequest.billing_interval` default to "monthly" and make the body itself optional using `body: ModuleSubscribeRequest = Body(default=ModuleSubscribeRequest())`. Task T003 (models) updated to include `Body` import and default.
