"""Phase D — T037 fact-taxonomy proof: BOTH allow AND deny paths of the T018
evaluator, across the closed class vocabulary and both scope predicates.

Config under proof: ``config/relationship/memory_scoping.goldsmith.yaml``
(``kind_to_class`` + ``allow_classes`` + ``scope_predicates``).
"""
import pytest

from backend.relationship.scoping_policy import CLOSED_CLASSES, ScopingPolicy

AUDIENCES = ["owner", "manager", "staff", "client_verified", "caller_unverified"]


@pytest.fixture(scope="module")
def policy() -> ScopingPolicy:
    return ScopingPolicy.load()


# (audience, fact_kind, expected_class) — a mapped kind whose class IS allowed.
ALLOW_CASES = [
    ("owner", "internal_note", "staff_notes"),      # owner is the only audience w/ staff_notes
    ("owner", "balance", "financial"),
    ("manager", "balance", "financial"),
    ("manager", "appointment", "schedule"),
    ("staff", "diagnosis", "patient_clinical"),
    ("staff", "phone", "contact_info"),
    ("client_verified", "appointment", "schedule"),
    ("client_verified", "visit_summary", "client_summary"),
    ("caller_unverified", "appointment", "schedule"),
    ("caller_unverified", "next_available", "schedule"),
]

# (audience, fact_kind, expected_class) — a mapped kind whose class is NOT allowed.
DENY_DEFAULT_CASES = [
    ("manager", "internal_note", "staff_notes"),        # manager lacks staff_notes
    ("staff", "balance", "financial"),                  # staff lacks financial
    ("staff", "internal_note", "staff_notes"),
    ("client_verified", "balance", "financial"),        # verified client sees no $ detail
    ("client_verified", "internal_note", "staff_notes"),
    ("caller_unverified", "visit_summary", "client_summary"),  # unverified: schedule only
    ("caller_unverified", "diagnosis", "patient_clinical"),
]


@pytest.mark.parametrize("audience,kind,klass", ALLOW_CASES)
def test_t037_allow_path(policy, audience, kind, klass):
    # §4a core semantic (C6 hardening): the allow path requires an ATTRIBUTED,
    # in-scope row — a null subject under an active predicate now denies.
    d = policy.evaluate(kind, audience,
                        subject_household="hhA", subject_clinic="clinic-taxonomy",
                        entity_scope=["hhA", "clinic-taxonomy"])
    assert d.allowed, (audience, kind)
    assert d.reason == "explicit_allow"
    assert d.fact_class == klass and klass in CLOSED_CLASSES


@pytest.mark.parametrize("audience,kind,klass", DENY_DEFAULT_CASES)
def test_t037_default_deny_path(policy, audience, kind, klass):
    d = policy.evaluate(kind, audience)
    assert not d.allowed, (audience, kind)
    assert d.reason == "default_deny_no_rule"
    assert d.fact_class == klass


@pytest.mark.parametrize("audience", AUDIENCES)
def test_t037_unmapped_kind_denies_for_every_audience(policy, audience):
    d = policy.evaluate("experimental_unmapped", audience)
    assert not d.allowed and d.reason == "unmapped_kind"
    assert d.fact_class is None


def test_t037_client_verified_wrong_household_denied(policy):
    # in-scope clinic so the household predicate is the one under test (§4a).
    d = policy.evaluate("diagnosis", "client_verified",
                        subject_household="hhB", subject_clinic="clinic-taxonomy",
                        entity_scope=["hhA", "clinic-taxonomy"])
    assert not d.allowed and d.reason == "wrong_household"


def test_t037_every_audience_has_both_allow_and_deny_proven(policy):
    # allow AND deny must BOTH be proven for every audience (incl. owner, whose
    # deny path is the unmapped-kind case since it allows all six classes).
    allow_auds = {a for a, _, _ in ALLOW_CASES}
    for aud in AUDIENCES:
        assert aud in allow_auds, f"no allow case for {aud}"
        # deny proven via a default-deny case OR the unmapped-kind case
        deny_default = any(a == aud for a, _, _ in DENY_DEFAULT_CASES)
        unmapped = not policy.evaluate("experimental_unmapped", aud).allowed
        assert deny_default or unmapped, f"no deny case for {aud}"


def test_t037_closed_class_vocabulary_is_exactly_six(policy):
    mapped_classes = set(policy.kind_to_class.values())
    assert mapped_classes <= CLOSED_CLASSES
    assert CLOSED_CLASSES == {
        "schedule", "client_summary", "patient_clinical",
        "financial", "contact_info", "staff_notes",
    }
