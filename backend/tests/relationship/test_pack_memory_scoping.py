"""011 shim-retirement prep — validate the vet pack memory_scoping policy data.

The core c6 scoped-recall rail DENIES any unmapped kind, so a vet memory kind
that is used in backend/ but NOT registered in the pack's ``kind_to_class`` would
SILENTLY DISAPPEAR at cutover. This test scans backend/ for every memory kind
referenced in code/tests and asserts each appears in
``domains/vet/comms/memory_scoping.yaml`` — the build fails if a kind is missing.

It also asserts the pack's three-field shape matches the live evaluator's closed
vocabulary and the live goldsmith config, so the pack copy cannot drift silently.
"""
import os
import re

import yaml

from backend.relationship.scoping_policy import CLOSED_CLASSES, ScopingPolicy

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_PACK = os.path.join(_ROOT, "domains", "vet", "comms", "memory_scoping.yaml")
_LIVE = os.path.join(_ROOT, "config", "relationship", "memory_scoping.goldsmith.yaml")

# Deliberate deny-probes: these exercise the unmapped-kind default-deny path and
# MUST NOT be registered (registering one would break the red-team assertions).
_INTENTIONALLY_UNMAPPED = {"experimental_unmapped", "insurance_claim"}

# Kind-bearing call shapes across backend/ code + tests:
#   Fact("kind", ...)  |  fact_kind="kind"  |  fact_kind == "kind"  |  summary_kind="kind"
_PATTERNS = [
    re.compile(r"""\bFact\(\s*["']([a-z_]+)["']"""),
    re.compile(r"""\bfact_kind\s*=\s*["']([a-z_]+)["']"""),
    re.compile(r"""\bfact_kind\s*==\s*["']([a-z_]+)["']"""),
    re.compile(r"""\bsummary_kind\s*[=:]\s*["']([a-z_]+)["']"""),
]


def _load_pack() -> dict:
    with open(_PACK) as f:
        return yaml.safe_load(f)


def _scan_referenced_kinds() -> set[str]:
    found: set[str] = set()
    backend_dir = os.path.join(_ROOT, "backend")
    this_file = os.path.basename(__file__)
    for dirpath, _dirs, files in os.walk(backend_dir):
        for name in files:
            if not name.endswith(".py") or name == this_file:
                continue  # skip THIS scanner (its docstring shows example shapes)
            with open(os.path.join(dirpath, name)) as f:
                text = f.read()
            for pat in _PATTERNS:
                found.update(pat.findall(text))
    # keep only the field-name-shaped identifiers, drop the deny-probes
    return {k for k in found if k not in _INTENTIONALLY_UNMAPPED}


# --------------------------------------------------------------------------- #
#  The load-bearing coverage guarantee
# --------------------------------------------------------------------------- #
def test_every_backend_kind_is_registered_in_pack():
    pack = _load_pack()
    registered = set(pack["kind_to_class"])
    referenced = _scan_referenced_kinds()
    assert referenced, "scan found no memory kinds — the scanner is broken"
    missing = referenced - registered
    assert not missing, (
        f"vet memory kinds used in backend/ but NOT registered in the pack "
        f"kind_to_class (they would silently deny at the core-rail cutover): "
        f"{sorted(missing)}"
    )


def test_deny_probes_stay_unregistered():
    # The red-team suite depends on these NOT being mapped.
    registered = set(_load_pack()["kind_to_class"])
    assert not (_INTENTIONALLY_UNMAPPED & registered)


# --------------------------------------------------------------------------- #
#  Shape / no-drift guarantees
# --------------------------------------------------------------------------- #
def test_pack_classes_are_the_closed_vocabulary():
    pack = _load_pack()
    used = set(pack["kind_to_class"].values())
    for audience, classes in pack["allow_classes"].items():
        used.update(classes)
    assert used <= CLOSED_CLASSES, f"pack references unknown class(es): {used - CLOSED_CLASSES}"


def test_pack_loads_through_the_live_evaluator():
    # The pack data must be consumable by the SAME evaluator the rail uses.
    with open(_PACK) as f:
        policy = ScopingPolicy.from_yaml(f.read())
    # a registered kind for an allowed audience reveals; an unmapped kind denies.
    ok = policy.evaluate("appointment", "caller_unverified", subject_clinic="c1",
                         entity_scope=["c1"])
    assert ok.allowed and ok.reason == "explicit_allow"
    denied = policy.evaluate("experimental_unmapped", "owner")
    assert not denied.allowed and denied.reason == "unmapped_kind"


def test_pack_matches_live_goldsmith_three_fields():
    pack = _load_pack()
    with open(_LIVE) as f:
        live = yaml.safe_load(f)
    assert pack["allow_classes"] == live["allow_classes"]
    assert pack["scope_predicates"] == live["scope_predicates"]
    # pack kind_to_class is a SUPERSET of (or equal to) the live config's.
    for kind, cls in live["kind_to_class"].items():
        assert pack["kind_to_class"].get(kind) == cls, f"drift on kind {kind}"
