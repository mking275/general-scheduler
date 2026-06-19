"""
spec-007 Account Agent
Handles: seed_demo_account, module status, plan validation, invoice generation.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

# ── T021: Module constants ──────────────────────────────────────────────────

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
PLAN_CLINIC_LIMITS = {"starter": 1, "professional": 5, "enterprise": 9999}

PLAN_ORDER = ["starter", "professional", "enterprise"]


# ── T022: Seed demo account (W-02 fix: split guard) ────────────────────────

def seed_demo_account(db, log_fn):
    """
    W-02 fix: Split guard.
    - Create account only if not exists (guarded).
    - Always run UPDATE clinics SET account_id='account-demo' WHERE account_id IS NULL.
    - All inserts are INSERT OR IGNORE — idempotent.
    """
    from ..models import Account

    now = datetime.utcnow()
    trial_ends = (now + timedelta(days=14)).isoformat()

    # Guard: create account only if not exists
    if not db.get_default_account():
        demo = Account(
            id="account-demo",
            name="Paws & Claws Veterinary Group",
            contact_name="Dr. Sarah Mitchell",
            contact_email="admin@pawsandclaws.demo",
            contact_phone="+1 (555) 842-0110",
            address="1200 Pacific Coast Hwy, Los Angeles, CA 90272",
            plan_tier="professional",
            status="trial",
            trial_ends_at=trial_ends,
            created_at=now.isoformat(),
            stripe_customer_id="cus_demo_mock",
            stripe_subscription_id="sub_demo_mock",
        )
        db.create_account(demo)

    # Always: assign all unassigned clinics to demo account
    from ..repository import _get_conn
    with _get_conn() as conn:
        conn.execute(
            "UPDATE clinics SET account_id='account-demo' WHERE account_id IS NULL"
        )

    # Seed module licenses (all 9, INSERT OR IGNORE)
    purchased = now.isoformat()
    for module_id, price_cents in MODULE_PRICING.items():
        lic_id = f"lic-demo-{module_id.lower().replace('-', '')}"
        from ..repository import _get_conn as _gc
        with _gc() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO module_licenses
                   (id, account_id, module_id, status, billing_interval, price_cents, purchased_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (lic_id, "account-demo", module_id, "active", "monthly", price_cents, purchased)
            )

    # Seed 2 invoices (INSERT OR IGNORE)
    june_line_items_json = '[{"description": "VPMA Professional Plan", "amount_cents": 24900}, {"description": "MOD-FIN Financial Operations", "amount_cents": 7900}]'
    db.create_account_invoice({
        "id": "inv-demo-001",
        "account_id": "account-demo",
        "invoice_number": "INV-2026-001",
        "period_start": "2026-06-01",
        "period_end": "2026-06-30",
        "line_items": [
            {"description": "VPMA Professional Plan", "amount_cents": 24900},
            {"description": "MOD-FIN Financial Operations", "amount_cents": 7900},
        ],
        "subtotal_cents": 32800,
        "total_cents": 32800,
        "status": "paid",
        "paid_at": "2026-06-01T00:00:00",
        "created_at": "2026-06-01T00:00:00",
    })
    db.create_account_invoice({
        "id": "inv-demo-002",
        "account_id": "account-demo",
        "invoice_number": "INV-2026-002",
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "line_items": [
            {"description": "VPMA Professional Plan", "amount_cents": 24900},
            {"description": "MOD-FIN Financial Operations", "amount_cents": 7900},
        ],
        "subtotal_cents": 32800,
        "total_cents": 32800,
        "status": "pending",
        "paid_at": None,
        "created_at": "2026-07-01T00:00:00",
    })

    # Seed 2 account users (INSERT OR IGNORE)
    db.create_account_user({
        "id": "user-demo-admin",
        "account_id": "account-demo",
        "name": "Dr. Sarah Mitchell",
        "email": "admin@pawsandclaws.demo",
        "role": "admin",
        "created_at": now.isoformat(),
    })
    db.create_account_user({
        "id": "user-demo-member",
        "account_id": "account-demo",
        "name": "James Kowalski",
        "email": "jkowalski@pawsandclaws.demo",
        "role": "member",
        "created_at": now.isoformat(),
    })

    log_fn("ACCOUNT AGENT: Demo account seeded — Paws & Claws Veterinary Group")


# ── T023: get_modules_with_status ──────────────────────────────────────────

def get_modules_with_status(db, account_id: str) -> list:
    """Return list of all 9 modules with license status for this account."""
    licenses_map = {}
    for lic in db.get_module_licenses(account_id):
        licenses_map[lic["module_id"]] = lic

    result = []
    for module_id in MODULE_PRICING.keys():
        name, description = MODULE_DESCRIPTIONS[module_id]
        price_cents = MODULE_PRICING[module_id]
        tier_required = MODULE_TIER_REQUIREMENTS[module_id]
        lic = licenses_map.get(module_id)
        licensed = lic is not None and lic.get("status") == "active"
        result.append({
            "module_id": module_id,
            "name": name,
            "description": description,
            "price_cents": price_cents,
            "billing_interval": lic["billing_interval"] if lic else "monthly",
            "tier_required": tier_required,
            "licensed": licensed,
            "license_status": lic["status"] if lic else None,
            "purchased_at": lic["purchased_at"] if lic else None,
        })
    return result


# ── T024: compute_trial_days_remaining ─────────────────────────────────────

def compute_trial_days_remaining(trial_ends_at: str) -> int:
    try:
        end = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
        end = end.replace(tzinfo=None)
        delta = end - datetime.utcnow()
        return max(0, delta.days)
    except Exception:
        return 0


# ── T025: validate_module_add ──────────────────────────────────────────────

def validate_module_add(account: dict, module_id: str, db=None) -> Optional[str]:
    """Returns error string if blocked, None if allowed."""
    # Trial: always allowed
    if account.get("status") == "trial":
        return None

    # Already active
    if db and db.account_has_module(account["id"], module_id):
        return f"{module_id} is already active for this account."

    # Plan tier check
    required_tier = MODULE_TIER_REQUIREMENTS.get(module_id)
    if required_tier:
        current_tier = account.get("plan_tier", "starter")
        if PLAN_ORDER.index(current_tier) < PLAN_ORDER.index(required_tier):
            return f"{module_id} requires {required_tier.capitalize()} plan. Current plan: {current_tier}."

    return None


# ── T026: generate_invoice_line_items ─────────────────────────────────────

def generate_invoice_line_items(account: dict, licenses: list) -> list:
    """Generate line items: base plan + one per active module license."""
    tier = account.get("plan_tier", "starter")
    items = [{"description": f"VPMA {tier.capitalize()} Plan", "amount_cents": PLAN_PRICES[tier]}]
    for lic in licenses:
        if lic.get("status") == "active":
            mod_id = lic["module_id"]
            name, _ = MODULE_DESCRIPTIONS.get(mod_id, (mod_id, ""))
            items.append({"description": f"{mod_id} {name}", "amount_cents": lic["price_cents"]})
    return items


# ── T027: next_invoice_number ──────────────────────────────────────────────

def next_invoice_number(db, account_id: str) -> str:
    year = datetime.utcnow().year
    from ..repository import _get_conn
    with _get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM account_invoices WHERE account_id=? AND invoice_number LIKE ?",
            (account_id, f"INV-{year}-%")
        ).fetchone()[0]
    return f"INV-{year}-{str(count + 1).zfill(3)}"
