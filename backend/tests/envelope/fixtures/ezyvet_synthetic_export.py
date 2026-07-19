"""Feature 009 — T005 synthetic ezyVet-shaped complete-export fixture.

The substrate the whole build stands on until the real ~Aug 3 delivery lands
(``backend/scripts/generate_avimark_fixture.py`` pattern: seeded, reproducible
ZIP-of-CSVs). Emits three variants per practice —

  * ``complete``  — all six §5 categories present
  * ``partial``   — attachments/imaging omitted (US8 partial-delivery)
  * ``delta``     — ONLY the missing attachments (arriving later; US8 delta)

— each carrying deliberately-planted **dirty data** (shared phones, duplicate
owners, deceased pets, orphaned refs, malformed rows) and a **financial answer
key** (true AR / invoice / payment totals, the source's *reported* figures, a
planted AR variance in one practice, and a >20%-unusable practice). The
generator emits both the seed export bytes (for vault receipt + checksum) and
the ground-truth ``AnswerKey`` the completeness / quality / reconciliation /
identity harnesses assert against — so a false "complete", a missed AR variance,
and a false-positive auto-ID are each detectable.

Everything is deterministic from an integer seed.
"""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from random import Random
from typing import Any, Optional

# Canonical §5 categories -> the ezyVet source entities that satisfy each.
CATEGORY_ENTITIES: dict[str, list[str]] = {
    "patient_client": ["clients", "patients"],
    "scheduling": ["appointments", "providers"],
    "invoicing_billing_payments": ["invoices", "ledger", "payments", "ar_balances"],
    "communications": ["communications"],
    "attachments_imaging": ["attachments"],
    "configuration": ["products", "inventory"],
}

# Fixed CSV column order per entity (deterministic bytes).
ENTITY_COLUMNS: dict[str, list[str]] = {
    "clients": ["client_id", "first_name", "last_name", "phone", "email", "address"],
    "patients": ["patient_id", "client_id", "name", "species", "breed", "status"],
    "providers": ["provider_id", "name", "role"],
    "appointments": ["appointment_id", "patient_id", "provider_id", "start", "type"],
    "invoices": ["invoice_id", "client_id", "total", "status", "issued_at"],
    "ledger": ["ledger_id", "account", "amount", "entry_type", "posted_at"],
    "payments": ["payment_id", "client_id", "amount", "method", "received_at"],
    "ar_balances": ["ar_id", "client_id", "balance", "as_of"],
    "inventory": ["inventory_id", "product_id", "qty_on_hand", "unit", "last_counted_at"],
    "communications": ["communication_id", "client_id", "channel", "body"],
    "attachments": ["attachment_id", "patient_id", "kind", "filename"],
    "products": ["product_id", "name", "unit_price"],
}

_FIRST = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
          "Linda", "William", "Barbara", "David", "Elizabeth", "Richard", "Susan"]
_LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
         "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson", "Thomas"]
_PETS = ["Bella", "Max", "Charlie", "Luna", "Cooper", "Lucy", "Buddy", "Bailey",
         "Rex", "Cleo", "Nala", "Simba", "Zeus", "Lola", "Milo", "Gus"]
_SPECIES = ["dog", "dog", "cat", "cat", "bird", "rabbit"]


@dataclass
class AnswerKey:
    """Ground truth for a single practice export — the harnesses assert against
    this so a false 'complete', a missed AR variance, and a false-positive
    auto-ID are each detectable."""
    practice_id: str
    variant: str
    planted: str
    categories_present: list[str]
    categories_absent: list[str]
    # financial ground truth (from the delivered data)
    ar_balance_total: float
    invoice_count: int
    payment_total: float
    # the source system's OWN reported figures (what reconciliation ties to)
    reported_ar_total: float
    reported_invoice_count: int
    reported_payment_total: float
    ar_variance: float                      # delivered - reported (0.0 when clean)
    has_planted_ar_variance: bool
    # data-quality ground truth
    total_sampled_records: int
    unusable_record_ids: list[str]
    usable_record_share: float
    below_floor: bool
    duplicate_owner_client_ids: list[list[str]]   # each inner list is one dup set
    deceased_patient_ids: list[str]
    orphaned_ref_ids: list[str]
    malformed_ids: list[str]
    # identity ground truth — phone -> the client_ids reachable
    shared_phone_groups: dict[str, list[str]] = field(default_factory=dict)
    single_match_phones: list[str] = field(default_factory=list)
    multi_match_phones: list[str] = field(default_factory=list)


@dataclass
class SyntheticExport:
    practice_id: str
    variant: str
    entities: dict[str, list[dict]]
    reported_figures: dict[str, Any]
    answer_key: AnswerKey

    # -- ZIP-of-CSVs, deterministic bytes (fixed member timestamps) -------- #
    def raw_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(self.entities.keys()):
                rows = self.entities[name]
                # known entities use the fixed column order; an injected/unknown
                # entity derives columns from its first row (test robustness).
                cols = ENTITY_COLUMNS.get(name) or (list(rows[0].keys()) if rows else [])
                sbuf = io.StringIO()
                w = csv.DictWriter(sbuf, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c, "") for c in cols})
                info = zipfile.ZipInfo(f"{name}.csv", date_time=(1980, 1, 1, 0, 0, 0))
                zf.writestr(info, sbuf.getvalue().encode("utf-8"))
            # manifest of reported figures (the source's own numbers)
            info = zipfile.ZipInfo("_reported_figures.txt", date_time=(1980, 1, 1, 0, 0, 0))
            lines = [f"{k}={self.reported_figures[k]}" for k in sorted(self.reported_figures)]
            zf.writestr(info, "\n".join(lines).encode("utf-8"))
        return buf.getvalue()

    def checksum(self) -> str:
        return hashlib.sha256(self.raw_bytes()).hexdigest()

    def byte_count(self) -> int:
        return len(self.raw_bytes())


def _phone(rng: Random) -> str:
    return f"({rng.randint(200, 999)}) {rng.randint(200, 999)}-{rng.randint(1000, 9999)}"


def generate_practice_export(
    practice_id: str,
    seed: int,
    variant: str = "complete",
    planted: str = "clean",
    num_clients: int = 16,
    num_patients: int = 24,
) -> SyntheticExport:
    """Generate one practice's ezyVet-shaped export deterministically.

    ``planted`` ∈ {``clean``, ``ar_variance``, ``dirty``}:
      * ``clean``       — light shared-phone/dup planting, well above the floor,
                          reported figures == delivered.
      * ``ar_variance`` — one open balance the source *reports* but that did NOT
                          transfer (the Digitail gap): reported_ar > delivered_ar.
      * ``dirty``       — >20% of sampled records unusable (breaches the floor).
    """
    rng = Random(seed)
    unusable_ids: list[str] = []
    deceased_ids: list[str] = []
    orphaned_ids: list[str] = []
    malformed_ids: list[str] = []
    dup_sets: list[list[str]] = []

    # ---- clients ---------------------------------------------------------- #
    clients: list[dict] = []
    for i in range(1, num_clients + 1):
        cid = str(i)
        clients.append({
            "client_id": cid,
            "first_name": rng.choice(_FIRST),
            "last_name": rng.choice(_LAST),
            "phone": _phone(rng),
            "email": f"client{i}.p{practice_id}@example.com",
            "address": f"{rng.randint(100, 9999)} Main St",
        })

    # planted duplicate owners — a second client row for the SAME person
    # (same normalized name + shared phone). one dup set in clean/dirty.
    def _add_duplicate(of: dict) -> str:
        new_id = str(len(clients) + 1)
        clients.append({
            "client_id": new_id,
            "first_name": of["first_name"],
            "last_name": of["last_name"],
            "phone": of["phone"],                     # shared line
            "email": f"dup{new_id}.p{practice_id}@example.com",
            "address": of["address"],
        })
        return new_id

    dup_a = clients[0]
    dup_b_id = _add_duplicate(dup_a)
    dup_sets.append(sorted([dup_a["client_id"], dup_b_id]))
    unusable_ids.append(f"clients:{dup_b_id}")        # the duplicate copy is unusable

    # planted shared phone across DISTINCT people (a collision, not a dup)
    coll_phone = _phone(rng)
    clients[1]["phone"] = coll_phone
    clients[2]["phone"] = coll_phone

    if planted == "dirty":
        # push unusable share over 20%: extra duplicates + malformed clients
        for _ in range(4):
            d_id = _add_duplicate(clients[rng.randint(0, 3)])
            unusable_ids.append(f"clients:{d_id}")
        # malformed client rows (blank required name)
        for _ in range(2):
            mid = str(len(clients) + 1)
            clients.append({
                "client_id": mid, "first_name": "", "last_name": "",
                "phone": "", "email": "", "address": "",
            })
            malformed_ids.append(f"clients:{mid}")
            unusable_ids.append(f"clients:{mid}")

    client_ids = {c["client_id"] for c in clients}

    # ---- patients --------------------------------------------------------- #
    patients: list[dict] = []
    for i in range(1, num_patients + 1):
        pid = str(i)
        owner = rng.choice(clients)
        status = "active"
        # a few deceased pets (valid history — flagged, not dropped)
        if i % 9 == 0:
            status = "deceased"
            deceased_ids.append(f"patients:{pid}")
        patients.append({
            "patient_id": pid,
            "client_id": owner["client_id"],
            "name": rng.choice(_PETS),
            "species": rng.choice(_SPECIES),
            "breed": "Mixed",
            "status": status,
        })

    # planted orphaned refs — patients pointing at a nonexistent client
    for _ in range(2 if planted != "dirty" else 4):
        opid = str(len(patients) + 1)
        patients.append({
            "patient_id": opid,
            "client_id": "999999",                    # no such client
            "name": rng.choice(_PETS),
            "species": rng.choice(_SPECIES),
            "breed": "Mixed",
            "status": "active",
        })
        orphaned_ids.append(f"patients:{opid}")
        unusable_ids.append(f"patients:{opid}")

    # ---- providers / appointments ---------------------------------------- #
    providers = [{"provider_id": str(i), "name": rng.choice(_FIRST) + " DVM",
                  "role": "veterinarian"} for i in range(1, 4)]
    appointments = []
    for i in range(1, num_patients + 1):
        pat = patients[(i - 1) % len(patients)]
        appointments.append({
            "appointment_id": str(i),
            "patient_id": pat["patient_id"],
            "provider_id": rng.choice(providers)["provider_id"],
            "start": f"2026-07-{(i % 28) + 1:02d}T10:00:00",
            "type": "wellness",
        })

    # ---- financials ------------------------------------------------------- #
    invoices, ledger, payments, ar_balances = [], [], [], []
    for i, c in enumerate(clients, start=1):
        if c["client_id"] in {mid.split(":")[1] for mid in malformed_ids}:
            continue
        total = round(rng.uniform(40, 600), 2)
        invoices.append({"invoice_id": str(i), "client_id": c["client_id"],
                         "total": total, "status": "closed",
                         "issued_at": f"2026-06-{(i % 28) + 1:02d}"})
        ledger.append({"ledger_id": str(i), "account": "revenue", "amount": total,
                       "entry_type": "invoice", "posted_at": f"2026-06-{(i % 28) + 1:02d}"})
        pay = round(total * rng.choice([1.0, 1.0, 0.5]), 2)
        payments.append({"payment_id": str(i), "client_id": c["client_id"],
                         "amount": pay, "method": "card",
                         "received_at": f"2026-06-{(i % 28) + 2:02d}"})
        bal = round(total - pay, 2)
        if bal > 0:
            ar_balances.append({"ar_id": str(i), "client_id": c["client_id"],
                                "balance": bal, "as_of": "2026-07-01"})

    delivered_ar = round(sum(a["balance"] for a in ar_balances), 2)
    invoice_count = len(invoices)
    payment_total = round(sum(p["amount"] for p in payments), 2)

    # the source system's OWN reported figures
    reported_ar = delivered_ar
    ar_variance = 0.0
    has_ar_var = False
    if planted == "ar_variance":
        # one open balance the source REPORTS but that did not transfer
        dropped = round(rng.uniform(150, 900), 2)
        reported_ar = round(delivered_ar + dropped, 2)
        ar_variance = round(delivered_ar - reported_ar, 2)   # negative shortfall
        has_ar_var = True

    # ---- config / comms / attachments ------------------------------------ #
    products = [{"product_id": str(i), "name": f"Service {i}",
                 "unit_price": round(rng.uniform(10, 200), 2)} for i in range(1, 6)]
    inventory = [{"inventory_id": str(i), "product_id": str(i),
                  "qty_on_hand": rng.randint(0, 100), "unit": "unit",
                  "last_counted_at": "2026-07-01"} for i in range(1, 6)]
    communications = [{"communication_id": str(i),
                       "client_id": rng.choice(clients)["client_id"],
                       "channel": "sms", "body": "Reminder: annual visit due."}
                      for i in range(1, 8)]
    attachments = [{"attachment_id": str(i),
                    "patient_id": rng.choice(patients)["patient_id"],
                    "kind": "xray", "filename": f"img_{i}.dcm"}
                   for i in range(1, 6)]

    entities: dict[str, list[dict]] = {
        "clients": clients, "patients": patients, "providers": providers,
        "appointments": appointments, "invoices": invoices, "ledger": ledger,
        "payments": payments, "ar_balances": ar_balances, "products": products,
        "inventory": inventory, "communications": communications,
        "attachments": attachments,
    }

    # partial variant omits the attachments/imaging category
    if variant == "partial":
        entities.pop("attachments", None)

    categories_present, categories_absent = [], []
    for cat, ents in CATEGORY_ENTITIES.items():
        if any(e in entities and entities[e] for e in ents):
            categories_present.append(cat)
        else:
            categories_absent.append(cat)

    # identity ground truth — group client phones
    phone_groups: dict[str, list[str]] = {}
    for c in clients:
        if not c["phone"]:
            continue
        phone_groups.setdefault(c["phone"], []).append(c["client_id"])
    single = sorted([ph for ph, ids in phone_groups.items() if len(set(ids)) == 1])
    multi = sorted([ph for ph, ids in phone_groups.items() if len(set(ids)) > 1])

    total_sampled = len(clients) + len(patients)
    usable_share = round(1.0 - len(set(unusable_ids)) / max(total_sampled, 1), 4)

    answer = AnswerKey(
        practice_id=practice_id, variant=variant, planted=planted,
        categories_present=sorted(categories_present),
        categories_absent=sorted(categories_absent),
        ar_balance_total=delivered_ar, invoice_count=invoice_count,
        payment_total=payment_total,
        reported_ar_total=reported_ar, reported_invoice_count=invoice_count,
        reported_payment_total=payment_total, ar_variance=ar_variance,
        has_planted_ar_variance=has_ar_var,
        total_sampled_records=total_sampled,
        unusable_record_ids=sorted(set(unusable_ids)),
        usable_record_share=usable_share,
        below_floor=(usable_share < 0.80),
        duplicate_owner_client_ids=dup_sets,
        deceased_patient_ids=sorted(deceased_ids),
        orphaned_ref_ids=sorted(orphaned_ids),
        malformed_ids=sorted(malformed_ids),
        shared_phone_groups={ph: sorted(set(ids)) for ph, ids in phone_groups.items()},
        single_match_phones=single, multi_match_phones=multi,
    )

    reported_figures = {
        "ar_balance_total": reported_ar,
        "invoice_count": invoice_count,
        "payment_total": payment_total,
    }
    return SyntheticExport(practice_id=practice_id, variant=variant,
                           entities=entities, reported_figures=reported_figures,
                           answer_key=answer)


def generate_delta_export(practice_id: str, seed: int) -> SyntheticExport:
    """The delta: ONLY the attachments/imaging category that was omitted from
    the matching ``partial`` export, arriving later (US8). Deterministic from the
    same seed used for the partial export."""
    full = generate_practice_export(practice_id, seed, variant="complete")
    attachments = full.entities["attachments"]
    export = SyntheticExport(
        practice_id=practice_id, variant="delta",
        entities={"attachments": attachments},
        reported_figures={},
        answer_key=AnswerKey(
            practice_id=practice_id, variant="delta", planted="clean",
            categories_present=["attachments_imaging"],
            categories_absent=[],
            ar_balance_total=0.0, invoice_count=0, payment_total=0.0,
            reported_ar_total=0.0, reported_invoice_count=0, reported_payment_total=0.0,
            ar_variance=0.0, has_planted_ar_variance=False,
            total_sampled_records=len(attachments), unusable_record_ids=[],
            usable_record_share=1.0, below_floor=False,
            duplicate_owner_client_ids=[], deceased_patient_ids=[],
            orphaned_ref_ids=[], malformed_ids=[],
        ),
    )
    return export


# Batch profile: which practice index gets which planted condition / variant.
def _batch_plan(n: int) -> dict[int, tuple[str, str]]:
    """index -> (variant, planted). Practice 0 = clean; 1 = planted AR variance;
    2 = >20% dirty (held); 3 = partial delivery; the rest clean."""
    plan = {i: ("complete", "clean") for i in range(n)}
    if n > 1:
        plan[1] = ("complete", "ar_variance")
    if n > 2:
        plan[2] = ("complete", "dirty")
    if n > 3:
        plan[3] = ("partial", "clean")
    return plan


def generate_batch(seed: int = 20260803, n: int = 23,
                   clinic_id: str = "goldsmith") -> list[SyntheticExport]:
    """A deterministic multi-practice batch. Exactly one planted AR variance,
    one >20%-unusable (held) practice, and one partial delivery; the rest clean."""
    plan = _batch_plan(n)
    out: list[SyntheticExport] = []
    for i in range(n):
        variant, planted = plan[i]
        pid = f"{clinic_id}-practice-{i:03d}"
        out.append(generate_practice_export(pid, seed + i, variant=variant, planted=planted))
    return out


if __name__ == "__main__":  # pragma: no cover
    batch = generate_batch(n=23)
    for exp in batch[:4]:
        ak = exp.answer_key
        print(f"{exp.practice_id} variant={exp.variant} planted={ak.planted} "
              f"AR={ak.ar_balance_total} reportedAR={ak.reported_ar_total} "
              f"usable={ak.usable_record_share} below_floor={ak.below_floor} "
              f"present={ak.categories_present}")
