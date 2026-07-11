"""T001–T003 setup verification: package import + config fixtures parse."""
import os

import yaml

from backend.tests.relationship.conftest import CONFIG_REL

CLOSED_CLASSES = {
    "schedule", "client_summary", "patient_clinical",
    "financial", "contact_info", "staff_notes",
}


def _load(name):
    with open(os.path.join(CONFIG_REL, name)) as f:
        return yaml.safe_load(f)


def test_t001_package_imports():
    import backend.relationship  # noqa: F401


def test_t003_memory_scoping_shape_and_default_deny():
    cfg = _load("memory_scoping.goldsmith.yaml")
    # Exactly the three-field shape (contract C / H1).
    assert set(cfg.keys()) == {"allow_classes", "scope_predicates", "kind_to_class"}

    allow = cfg["allow_classes"]
    # At least one (audience, class) pair OMITTED -> default-deny exercisable.
    omitted = [(aud, c) for aud in allow for c in CLOSED_CLASSES if c not in allow[aud]]
    assert omitted, "no omitted (audience, class) pair — default-deny not exercisable"

    # kind_to_class is intentionally NON-EXHAUSTIVE -> unmapped-kind deny exercisable.
    k2c = cfg["kind_to_class"]
    assert "experimental_unmapped" not in k2c and "insurance_claim" not in k2c
    # every mapped class is in the closed vocabulary
    assert set(k2c.values()) <= CLOSED_CLASSES


def test_t003_verification_policy_tiers():
    cfg = _load("verification_policy.goldsmith.yaml")
    sens = cfg["sensitivity"]
    assert sens["contact_edit"] == "high" and sens["refill_request"] == "high"
    assert sens["reschedule"] == "low" and sens["cancel"] == "low"
    assert cfg["factors_required"]["low"] == 1 and cfg["factors_required"]["high"] == 2


def test_t003_inbound_keywords_has_stop():
    cfg = _load("inbound_keywords.en.yaml")
    assert cfg["keywords"]["STOP"] == "opt_out"
    assert "START" in cfg["keywords"] and "HELP" in cfg["keywords"]
