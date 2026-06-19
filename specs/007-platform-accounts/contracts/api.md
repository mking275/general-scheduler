# API Contracts — 007-platform-accounts

All routes prefixed `/api/account`. All return JSON.

---

## GET /api/account
Returns the demo account with computed fields.

**Response 200:**
```json
{
  "id": "account-demo",
  "name": "Paws & Claws Veterinary Group",
  "contact_name": "Dr. Sarah Mitchell",
  "contact_email": "admin@pawsandclaws.demo",
  "contact_phone": "+1 (555) 842-0110",
  "address": "1200 Pacific Coast Hwy, Los Angeles, CA 90272",
  "plan_tier": "professional",
  "status": "trial",
  "trial_ends_at": "2026-07-03T15:25:00Z",
  "trial_days_remaining": 14,
  "created_at": "2026-06-19T...",
  "stripe_customer_id": "cus_demo_mock",
  "active_module_count": 9
}
```

---

## PUT /api/account
Update account contact details.

**Request body:**
```json
{
  "name": "Paws & Claws Group",
  "contact_name": "Dr. Sarah Mitchell",
  "contact_phone": "+1 (555) 000-0000"
}
```
**Response 200:** Updated account object (same shape as GET /api/account)

---

## GET /api/account/modules
Returns all 9 modules with license status for this account.

**Response 200:**
```json
[
  {
    "module_id": "MOD-FIN",
    "name": "Financial Operations",
    "description": "Invoice drafting, payment terminal, collections",
    "price_cents": 7900,
    "billing_interval": "monthly",
    "tier_required": "professional",
    "licensed": true,
    "license_status": "active",
    "purchased_at": "2026-06-19T..."
  },
  {
    "module_id": "MOD-ENT",
    "name": "Enterprise",
    "description": "Multi-location ownership, benchmarking, SSO",
    "price_cents": 14900,
    "billing_interval": "monthly",
    "tier_required": "enterprise",
    "licensed": false,
    "license_status": null,
    "purchased_at": null
  }
]
```

---

## POST /api/account/modules/{module_id}
Purchase (activate) a module license.

**Path param:** `module_id` e.g. `MOD-FIN`

**Request body:**
```json
{ "billing_interval": "monthly" }
```

**Response 200:**
```json
{
  "module_id": "MOD-FIN",
  "status": "active",
  "price_cents": 7900,
  "purchased_at": "2026-06-19T..."
}
```

**Response 403** (plan tier too low):
```json
{ "detail": "MOD-ENT requires Enterprise plan. Current plan: professional." }
```

**Response 409** (already licensed):
```json
{ "detail": "MOD-FIN is already active for this account." }
```

---

## DELETE /api/account/modules/{module_id}
Cancel a module license (immediate in demo).

**Response 200:**
```json
{ "module_id": "MOD-FIN", "status": "cancelled" }
```

**Response 404** (not licensed):
```json
{ "detail": "MOD-FIN is not licensed for this account." }
```

---

## GET /api/account/invoices
List all invoices for the account, newest first.

**Response 200:**
```json
[
  {
    "id": "inv-001",
    "invoice_number": "INV-2026-001",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "line_items": [
      { "description": "VPMA Professional Plan", "amount_cents": 24900 },
      { "description": "MOD-FIN Financial Operations", "amount_cents": 7900 }
    ],
    "subtotal_cents": 32800,
    "total_cents": 32800,
    "status": "paid",
    "paid_at": "2026-06-01T...",
    "created_at": "2026-06-01T..."
  }
]
```

---

## GET /api/account/invoices/{invoice_id}
Single invoice detail.

**Response 200:** Same shape as single item from list above.
**Response 404:** `{ "detail": "Invoice not found" }`

---

## GET /api/account/clinics
All clinics belonging to this account.

**Response 200:**
```json
[
  {
    "id": "clinic-downtown",
    "name": "Paws & Claws Downtown",
    "color_hex": "#6C63FF",
    "address": "",
    "is_active": true,
    "account_id": "account-demo"
  }
]
```

---

## POST /api/account/clinics
Add a new clinic to the account. Professional+ only.

**Request body:**
```json
{
  "name": "Paws & Claws Eastside",
  "address": "500 E 6th St, Los Angeles CA",
  "timezone": "America/Los_Angeles",
  "color_hex": "#F59E0B"
}
```

**Response 201:** New clinic object.

**Response 403** (Starter plan):
```json
{ "detail": "Adding clinics requires Professional or Enterprise plan." }
```

---

## GET /api/account/plan
Current plan details + upgrade options.

**Response 200:**
```json
{
  "current_tier": "professional",
  "current_price_cents": 24900,
  "upgrade_options": [
    {
      "tier": "enterprise",
      "price_cents": 59900,
      "delta_cents": 35000,
      "features": ["Unlimited clinics", "MOD-ENT included", "Priority support"]
    }
  ],
  "downgrade_options": [
    {
      "tier": "starter",
      "price_cents": 9900,
      "delta_cents": -15000,
      "note": "Downgrading will cancel all active module licenses"
    }
  ]
}
```

---

## POST /api/account/plan/upgrade
Change plan tier.

**Request body:**
```json
{ "plan_tier": "enterprise" }
```

**Response 200:**
```json
{
  "account_id": "account-demo",
  "old_tier": "professional",
  "new_tier": "enterprise",
  "proration_cents": 17500,
  "message": "Plan upgraded to Enterprise. MOD-ENT has been added at no extra charge."
}
```

---

## Module Access Stubs (require_module enforcement)

These routes exist solely to demonstrate the enforcement pattern for future MOD implementations:

### GET /api/mods/fin/status
```
Depends(require_module("MOD-FIN"))
Returns: { "module": "MOD-FIN", "access": "granted" }
```

### GET /api/mods/com/status  
```
Depends(require_module("MOD-COM"))
Returns: { "module": "MOD-COM", "access": "granted" }
```

*(One stub per MOD — 9 total. These will be replaced by real route groups when each MOD is implemented.)*
