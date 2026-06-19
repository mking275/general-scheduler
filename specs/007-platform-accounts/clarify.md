# speckit.clarify — 007-platform-accounts
## Clarification Log

All questions resolved by architect. No user input required.

---

### Q1: Should the "Account Admin" role be in RoleSelector alongside Front Desk / Vet / etc?

**Decision**: Yes. Add as a 5th tab with distinct styling (indigo, not the teal/green of clinical roles). This keeps navigation consistent with the existing pattern. The tab label is "⚙ Account".

---

### Q2: What happens when a Starter account tries to add a module?

**Decision**: The "Add" button is replaced with a "🔒 Upgrade Plan" button that opens the Plan tab. No error — graceful upsell. Starter accounts can't add any modules; Professional unlocks P1+P2; Enterprise unlocks all.

**Module tier rules:**
- Starter: no modules
- Professional: MOD-FIN, MOD-COM, MOD-INV, MOD-TEL, MOD-ANL, MOD-MAR, MOD-STF, MOD-REF
- Enterprise: all of the above + MOD-ENT (also included at no extra charge)

---

### Q3: How are the two seeded demo clinics linked to the account?

**Decision**: `seed_demo_account()` runs at startup and does:
```python
UPDATE clinics SET account_id = 'account-demo' WHERE id IN ('clinic-downtown', 'clinic-westside')
```
Wrapped in try/except; idempotent.

---

### Q4: Should module removal be instant or scheduled for end of billing period?

**Decision**: Instant for demo purposes (status → 'cancelled' immediately). In production this would be end-of-period, but for demo the effect must be immediately visible.

---

### Q5: How does `require_module` interact with trial mode?

**Decision**: If `account.status == 'trial'`, skip all module checks — everything is allowed. This is checked first before any module license lookup, so the demo is always fully functional.

---

### Q6: Where does the "Add Clinic" flow go? Does it create a real clinic?

**Decision**: Yes — "Add Clinic" opens an inline form (name, address, timezone, color picker) and calls `POST /api/account/clinics`, which calls the existing `db.create_clinic()`. The new clinic is immediately available in ClinicSwitcher. Gated to Professional+ (Starter shows locked button with tooltip "Upgrade to Professional to add locations").

---

### Q7: Should `GET /api/account/modules` return all 9 MODs or only the ones for the account's plan tier?

**Decision**: Return all 9 always, with a `tier_required` field on each and a `licensed` boolean. This lets the frontend show the full module marketplace with proper locked/unlocked states in one call.

---

### Q8: What invoice number format?

**Decision**: `INV-{YYYY}-{NNN}` where NNN is zero-padded sequence per account per year. Seed: INV-2026-001 (paid, June 2026) and INV-2026-002 (pending, July 2026).

---

### Q9: Should module licensing be checked in the frontend independently?

**Decision**: Frontend always calls `GET /api/account/modules` on AccountPortal mount and stores module state in local component state. Individual feature components (future MOD implementations) will check this state before rendering. For now, the enforcement is only via the API middleware — frontend gating is implemented in AccountPortal only.

---

### Q10: Does `past_due` status affect any existing functionality?

**Decision**: In demo, `past_due` only shows a red banner in Dashboard header ("⚠ Payment overdue — update billing"). No features are blocked. Full suspension enforcement is out of scope for this spec.
