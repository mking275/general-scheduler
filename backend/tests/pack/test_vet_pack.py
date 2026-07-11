"""Program #6 Cycle 6c — vet domain pack validation (Tier-1 administrative).

Guards the pack's non-negotiables:
  * every YAML parses;
  * pack.yaml is self-consistent (semver, DRAFT, referenced files exist);
  * every constraints.yaml instance uses ONLY the 4 generic engine types;
  * every file carries provenance + signed_by + a DRAFT marker;
  * ZERO clinical-tier keys leak into any Tier-1 file (denylist grep).

Run: `pytest backend/tests/pack/test_vet_pack.py -v`
"""
import hashlib
import re
from pathlib import Path

import pytest
import yaml

# repo root = .../backend/tests/pack/test_vet_pack.py -> parents[3]
REPO = Path(__file__).resolve().parents[3]
PACK = REPO / "domains" / "vet"

# The FOUR generic engine types a pack may instance. Adding a type is a CORE
# change, never a pack change.
GENERIC_CONSTRAINT_TYPES = {
    "resource_capacity",
    "procedure_gate",
    "role_requirement",
    "licensure_ratio",
}

# Tier-2 clinical content that must NEVER appear as a KEY in a Tier-1 file.
# Matched as YAML keys (start-of-line, optional list dash), not as prose — the
# Tier-1 files legitimately *mention* these words when drawing the boundary.
CLINICAL_KEY_DENYLIST = [
    "dose", "doses", "dosage", "dosing",
    "mg_kg", "mg_per_kg", "mcg_kg",
    "contraindication", "contraindications",
    "drug_interaction", "drug_interactions", "interaction_severity",
    "treatment_plan", "treatment_protocol",
    "prescription_content", "rx_content", "differential_diagnosis",
]
_DENY_RE = re.compile(
    r"^\s*-?\s*(" + "|".join(CLINICAL_KEY_DENYLIST) + r")\s*:",
    re.IGNORECASE,
)

# clinical/ is the Tier-2 STUB: it declares (in prose) what clinical content
# WILL live there and is allowed to name dosing/drug-interactions. It carries no
# Tier-2 *content*. Excluded from the Tier-1 denylist scan only.
TIER2_DIR = PACK / "clinical"


def _yaml_files():
    return sorted(p for p in PACK.rglob("*.yaml"))


def _all_files():
    return sorted(p for p in PACK.rglob("*") if p.is_file())


def _load(p: Path):
    with p.open() as fh:
        return yaml.safe_load(fh)


# --------------------------------------------------------------------------- #
#  1. every YAML parses
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _yaml_files(), ids=lambda p: str(p.relative_to(PACK)))
def test_yaml_parses(path):
    doc = _load(path)
    assert doc is not None, f"{path} parsed to None"


# --------------------------------------------------------------------------- #
#  2. pack.yaml self-consistency
# --------------------------------------------------------------------------- #
def test_pack_manifest_self_consistent():
    m = _load(PACK / "pack.yaml")
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(m["version"])), "version must be semver"
    assert m["version"] == "0.1.0"
    assert m["status"] == "DRAFT"
    assert m["locale"] == "en-US"
    assert m["currency"] == "USD"

    # active capability modules named in the brief
    mods = m["capability_modules"]
    for expected in ("workforce", "scheduling", "compliance", "comms"):
        assert mods[expected]["active"] is True, f"module {expected} must be active"

    # every pack-internal referenced file exists
    referenced = []
    for mod in mods.values():
        referenced += mod.get("configures", [])
    referenced.append(m["knowledge"]["glossary"])
    referenced.append(m["metrics"]["kpis"])
    referenced.append(m["clinical"]["readme"])
    for rel in referenced:
        assert (PACK / rel).exists(), f"pack references missing file: {rel}"

    # clinical tier declared but empty of content
    assert m["clinical"]["status"] == "gated"
    assert m["clinical"]["content_present"] is False


def test_comms_references_resolve_and_checksums_match():
    """Include-by-reference contract: referenced live configs exist and their
    sha256/16 matches the recorded checksum (drift detector)."""
    refs = _load(PACK / "comms" / "references.yaml")["references"]
    assert refs, "comms references must be non-empty"
    for ref in refs:
        target = REPO / ref["path"]
        assert target.exists(), f"referenced config missing: {ref['path']}"
        digest = hashlib.sha256(target.read_bytes()).hexdigest()[:16]
        assert digest == ref["checksum_sha256_16"], (
            f"checksum drift on {ref['path']}: recorded {ref['checksum_sha256_16']}, "
            f"actual {digest} — referenced config changed; re-review before ship"
        )


# --------------------------------------------------------------------------- #
#  3. constraints.yaml — only the 4 generic types, well-formed instances
# --------------------------------------------------------------------------- #
def test_constraints_use_only_generic_types():
    doc = _load(PACK / "workforce" / "constraints.yaml")
    instances = doc["constraints"]
    assert instances, "constraints must be non-empty"
    for c in instances:
        assert c["type"] in GENERIC_CONSTRAINT_TYPES, (
            f"constraint {c.get('id')} uses non-generic type {c.get('type')!r}"
        )
        assert c.get("id"), "constraint missing id"
        assert isinstance(c.get("params"), dict) and c["params"], (
            f"constraint {c['id']} missing params"
        )
        assert c.get("severity") in {"hard", "soft"}, (
            f"constraint {c['id']} severity must be hard|soft"
        )
        # every instance is briefing-explainable: evidence + provenance
        assert c.get("evidence"), f"constraint {c['id']} missing evidence"
        assert c.get("provenance"), f"constraint {c['id']} missing provenance"

    # the declared summary must also be a subset of the 4
    used = set(doc["constraint_types_used"])
    assert used <= GENERIC_CONSTRAINT_TYPES
    # and must match what's actually instanced
    assert used == {c["type"] for c in instances}


# --------------------------------------------------------------------------- #
#  4. provenance + signed_by + DRAFT on every file
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _yaml_files(), ids=lambda p: str(p.relative_to(PACK)))
def test_yaml_has_provenance_and_signed_by(path):
    doc = _load(path)
    assert "provenance" in doc, f"{path} missing top-level provenance block"
    assert "signed_by" in doc, f"{path} missing signed_by"
    assert doc["signed_by"] is None, f"{path} must be UNSIGNED in v0.1.0"
    prov = doc["provenance"]
    assert prov.get("review_status") == "DRAFT", f"{path} not marked DRAFT"
    assert prov.get("sources"), f"{path} provenance has no sources"


@pytest.mark.parametrize(
    "path",
    [p for p in _all_files() if p.suffix == ".md"],
    ids=lambda p: str(p.relative_to(PACK)),
)
def test_markdown_has_provenance_markers(path):
    text = path.read_text().lower()
    assert "provenance" in text, f"{path} missing provenance"
    assert "signed_by" in text, f"{path} missing signed_by"
    assert "draft" in text, f"{path} missing DRAFT marker"


# --------------------------------------------------------------------------- #
#  5. denylist — zero clinical-tier keys in any Tier-1 file
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path",
    [p for p in _all_files() if TIER2_DIR not in p.parents and p != TIER2_DIR],
    ids=lambda p: str(p.relative_to(PACK)),
)
def test_no_clinical_tier_keys(path):
    offending = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if _DENY_RE.match(line):
            offending.append((i, line.strip()))
    assert not offending, (
        f"{path.relative_to(PACK)} has clinical-tier keys (Tier-2 must be gated): {offending}"
    )
