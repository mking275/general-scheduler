# Data Model — 007-platform-accounts

---

## New Tables

### `accounts`
```sql
CREATE TABLE IF NOT EXISTS accounts (
    id                     TEXT PRIMARY KEY,
    name                   TEXT NOT NULL,
    contact_name           TEXT NOT NULL,
    contact_email          TEXT NOT NULL,
    contact_phone          TEXT DEFAULT '',
    address                TEXT DEFAULT '',
    plan_tier              TEXT NOT NULL DEFAULT 'starter',
    status                 TEXT NOT NULL DEFAULT 'trial',
    trial_ends_at          TEXT,
    created_at             TEXT NOT NULL,
    stripe_customer_id     TEXT DEFAULT '',
    stripe_subscription_id TEXT DEFAULT ''
);
```

### `module_licenses`
```sql
CREATE TABLE IF NOT EXISTS module_licenses (
    id                          TEXT PRIMARY KEY,
    account_id                  TEXT NOT NULL,
    module_id                   TEXT NOT NULL,
    status                      TEXT NOT NULL DEFAULT 'active',
    billing_interval            TEXT NOT NULL DEFAULT 'monthly',
    price_cents                 INTEGER NOT NULL DEFAULT 0,
    purchased_at                TEXT NOT NULL,
    expires_at                  TEXT,
    stripe_subscription_item_id TEXT DEFAULT '',
    UNIQUE(account_id, module_id)
);
```

### `account_invoices`
```sql
CREATE TABLE IF NOT EXISTS account_invoices (
    id                TEXT PRIMARY KEY,
    account_id        TEXT NOT NULL,
    invoice_number    TEXT NOT NULL,
    period_start      TEXT NOT NULL,
    period_end        TEXT NOT NULL,
    line_items        TEXT NOT NULL DEFAULT '[]',
    subtotal_cents    INTEGER NOT NULL DEFAULT 0,
    total_cents       INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'pending',
    stripe_invoice_id TEXT DEFAULT '',
    paid_at           TEXT,
    created_at        TEXT NOT NULL
);
```

### `account_users`
```sql
CREATE TABLE IF NOT EXISTS account_users (
    id         TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    role       TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL,
    UNIQUE(account_id, email)
);
```

---

## Modified Tables

### `clinics` — Add `account_id` column
```sql
ALTER TABLE clinics ADD COLUMN account_id TEXT;
-- Populated by seed_demo_account() for existing clinics
```

---

## Relationships

```
accounts (1) ──── (N) clinics          [clinics.account_id → accounts.id]
accounts (1) ──── (N) module_licenses  [module_licenses.account_id → accounts.id]
accounts (1) ──── (N) account_invoices [account_invoices.account_id → accounts.id]
accounts (1) ──── (N) account_users    [account_users.account_id → accounts.id]
```

---

## Pydantic Models (backend/models.py additions)

```python
class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    contact_name: str
    contact_email: str
    contact_phone: str = ""
    address: str = ""
    plan_tier: str = "starter"       # starter | professional | enterprise
    status: str = "trial"            # trial | active | past_due | suspended | cancelled
    trial_ends_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""

class ModuleLicense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    module_id: str                   # MOD-FIN | MOD-COM | etc.
    status: str = "active"           # active | suspended | cancelled
    billing_interval: str = "monthly"
    price_cents: int = 0
    purchased_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    stripe_subscription_item_id: str = ""

class AccountInvoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    invoice_number: str
    period_start: str
    period_end: str
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    subtotal_cents: int = 0
    total_cents: int = 0
    status: str = "pending"          # pending | paid | failed | void
    stripe_invoice_id: str = ""
    paid_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AccountUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    name: str
    email: str
    role: str = "admin"              # admin | member
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AccountUpdateRequest(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None

class ModuleSubscribeRequest(BaseModel):
    billing_interval: str = "monthly"  # monthly | annual

class PlanUpgradeRequest(BaseModel):
    plan_tier: str   # starter | professional | enterprise
```

---

## Seed Data

```python
# account-demo (seeded by seed_demo_account() in account_agent.py)
{
    "id": "account-demo",
    "name": "Paws & Claws Veterinary Group",
    "contact_name": "Dr. Sarah Mitchell",
    "contact_email": "admin@pawsandclaws.demo",
    "contact_phone": "+1 (555) 842-0110",
    "address": "1200 Pacific Coast Hwy, Los Angeles, CA 90272",
    "plan_tier": "professional",
    "status": "trial",
    "trial_ends_at": NOW + 14 days,
    "stripe_customer_id": "cus_demo_mock",
    "stripe_subscription_id": "sub_demo_mock",
}

# module_licenses — all 9, seeded as active in trial
# account_invoices — 2 seeded:
#   INV-2026-001: paid, June 1–30 2026, $328 (Professional $249 + MOD-FIN $79)
#   INV-2026-002: pending, July 1–31 2026, $328
# account_users — 2 seeded:
#   Dr. Sarah Mitchell, admin@pawsandclaws.demo, role=admin
#   James Kowalski, jkowalski@pawsandclaws.demo, role=member
```
