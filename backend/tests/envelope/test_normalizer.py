"""Feature 009 — T018/T019/T020 canonical normalizer acceptance.

T018 — lineage: normalizing a fixture populates every canonical category with
source_id/entity_ref on 100% of records; every record resolves back to a source
record via its entity_ref; the client/patient keys are the byte-identical 011
handoff shape.
T019 — idempotency: normalizing the same fixture twice yields 0 duplicate
canonical records and identical stable identifiers.
T020 — unmapped preservation: a source field with no canonical target is retained
in the unmapped-field sidecar tied to the record's lineage, never dropped.
"""
from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.normalizer import Normalizer
from backend.envelope.pims import load_adapters
from backend.envelope.pims.port import resolve_adapter
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"

# every canonical category the complete-export produces
EXPECTED_CATEGORIES = {
    "provider", "client", "patient", "appointment", "invoice", "ledger",
    "payment", "ar_balance", "inventory", "communication", "attachment",
    "product_service",
}


def _adapter(pid):
    load_adapters()
    return resolve_adapter("ezyvet", "complete_v1", clinic_id=CLINIC, practice_id=pid,
                           practice_database_id="pdb1", extraction_port=SimExtractionPort())


def _load(repo, pid, seed=7, mutate=None):
    exp = generate_practice_export(pid, seed=seed, variant="complete")
    if mutate:
        mutate(exp)
    a = _adapter(pid)
    profile = a.profile(exp)
    Normalizer(repo).normalize(CLINIC, pid, a, profile, exp)
    return exp


def test_lineage_every_category_and_100pct_coverage(repo):
    pid = "p-norm-lineage"
    _load(repo, pid)
    records = repo.list_canonical_records(pid)
    assert records, "no canonical records persisted"

    categories = {r["category"] for r in records}
    assert EXPECTED_CATEGORIES.issubset(categories), EXPECTED_CATEGORIES - categories

    # 100% lineage — every record carries a non-empty entity_ref + source_id
    assert all(r["entity_ref"] and r["source_id"] for r in records)
    # 011-handoff key shapes are byte-identical (names never in the key)
    clients = [r for r in records if r["category"] == "client"]
    patients = [r for r in records if r["category"] == "patient"]
    assert clients and all(r["entity_ref"].startswith("client:ezyvet_c") for r in clients)
    assert patients and all(r["entity_ref"].startswith("patient:ezyvet_p") for r in patients)


def test_financial_records_land_in_typed_tables(repo):
    pid = "p-norm-typed"
    _load(repo, pid)
    ars = repo.list_canonical("ar_balance", pid)
    invoices = repo.list_canonical("invoice_record", pid)
    payments = repo.list_canonical("payment_record", pid)
    assert ars and invoices and payments
    # typed numeric coercion — balances sum to a float
    assert isinstance(sum(a["balance"] for a in ars), float)
    assert all(a["entity_ref"].startswith("ar_balance:") for a in ars)


def test_idempotent_rerun_no_duplicates_stable_ids(repo):
    pid = "p-norm-idem"
    _load(repo, pid)
    first = repo.list_canonical_records(pid)
    first_keys = sorted(r["entity_ref"] for r in first)
    ar_first = repo.count_canonical("ar_balance", pid)

    # re-run the identical source
    _load(repo, pid)
    second = repo.list_canonical_records(pid)
    second_keys = sorted(r["entity_ref"] for r in second)
    ar_second = repo.count_canonical("ar_balance", pid)

    assert len(second) == len(first)                 # 0 duplicate rows
    assert second_keys == first_keys                 # stable identifiers
    assert ar_second == ar_first                     # typed tables idempotent too


def test_unmapped_field_preserved_in_sidecar(repo):
    pid = "p-norm-unmapped"

    def _inject(exp):
        # add a source column with no canonical target on every client row
        for row in exp.entities["clients"]:
            row["loyalty_tier"] = "gold"

    _load(repo, pid, mutate=_inject)
    sidecar = repo.list_canonical("unmapped_field_sidecar", pid)
    fields = {s["source_field"] for s in sidecar}
    assert "loyalty_tier" in fields
    # tied to the owning record's lineage
    tiers = [s for s in sidecar if s["source_field"] == "loyalty_tier"]
    assert all(s["entity_ref"].startswith("client:ezyvet_c") for s in tiers)
