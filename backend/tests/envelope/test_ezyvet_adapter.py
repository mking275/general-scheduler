"""Feature 009 — T015 ezyVet adapter + T016 unmapped-entities-flagged acceptance.

T015:
- the adapter resolves through the registry and maps the fixture's ezyVet
  entities to canonical targets; the core calls it only via the port.
T016:
- a fixture entity absent from the mapping config is surfaced as a flagged
  unmapped item (not dropped);
- a delivered variant the adapter cannot fully map flags for adapter work rather
  than forcing a wrong mapping.
"""
from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.pims import load_adapters
from backend.envelope.pims.port import PimsAdapterPort, resolve_adapter
from backend.relationship import entity_ref as eref
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"

EXPECTED_CATEGORIES = {
    "provider", "client", "patient", "appointment", "invoice", "ledger",
    "payment", "ar_balance", "inventory", "communication", "attachment",
    "product_service",
}


def _adapter(pid, variant="complete_v1"):
    load_adapters()
    return resolve_adapter("ezyvet", variant, clinic_id=CLINIC, practice_id=pid,
                           practice_database_id="pdb1",
                           extraction_port=SimExtractionPort())


def test_adapter_resolves_through_registry_and_is_a_port():
    a = _adapter("p1")
    assert isinstance(a, PimsAdapterPort)


def test_adapter_maps_all_entities_to_canonical_targets():
    pid = "p-map"
    exp = generate_practice_export(pid, seed=7, variant="complete")
    a = _adapter(pid)
    profile = a.profile(exp)
    result = a.normalize(profile, exp)

    categories = {r.category for r in result.records}
    assert EXPECTED_CATEGORIES.issubset(categories), EXPECTED_CATEGORIES - categories

    # every record carries non-empty entity_ref + source_id lineage
    assert all(r.entity_ref and r.source_id for r in result.records)
    # 011-handoff key shapes
    clients = [r for r in result.records if r.category == "client"]
    patients = [r for r in result.records if r.category == "patient"]
    providers = [r for r in result.records if r.category == "provider"]
    assert all(r.entity_ref.startswith("client:ezyvet_c") for r in clients)
    assert all(r.entity_ref.startswith("patient:ezyvet_p") for r in patients)
    assert all(r.entity_ref.startswith("staff:") for r in providers)
    # a financial record maps to a canonical target with synthesized lineage
    ars = [r for r in result.records if r.category == "ar_balance"]
    assert ars and all(r.entity_ref.startswith("ar_balance:") for r in ars)


def test_unmapped_entity_is_flagged_not_dropped():
    pid = "p-unmapped"
    exp = generate_practice_export(pid, seed=7, variant="complete")
    # inject an entity the mapping config does not know about
    exp.entities["custom_forms"] = [{"custom_forms_id": "1", "label": "consent"}]
    a = _adapter(pid)
    result = a.normalize(a.profile(exp), exp)
    assert "custom_forms" in result.unmapped_entities
    # profile() also flags it in unmapped_flags
    assert "custom_forms" in a.profile(exp).unmapped_flags


def test_unrecognized_variant_flags_for_adapter_work():
    pid = "p-variant"
    exp = generate_practice_export(pid, seed=7, variant="complete")
    # remove core entities so the extraction cannot recognize the ezyVet variant
    for e in ("invoices", "patients"):
        exp.entities.pop(e, None)
    a = _adapter(pid, variant="some_unknown_variant")  # resolves via ("ezyvet","*")
    profile = a.profile(exp)
    # flagged for adapter work rather than force-fit to a wrong mapping
    assert profile.export_variant == "unrecognized_variant"


def test_core_never_imports_the_concrete_adapter():
    """The orchestration core reaches the adapter only via the port registry."""
    import ast
    import os

    from backend.envelope import state_machine
    core_root = os.path.dirname(state_machine.__file__)
    for mod in ("state_machine.py", "format_discovery.py"):
        tree = ast.parse(open(os.path.join(core_root, mod)).read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{a.name}" for a in node.names)
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
        assert not any("ezyvet_adapter" in i for i in imported), \
            f"{mod} must not import the concrete adapter"
