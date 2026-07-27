"""Phase D — T018 evaluator (default-deny) + T019 reveal-decision audit."""
from uuid import uuid4

import pytest

from backend.relationship.reveal_log import RevealLog
from backend.relationship.scoping_policy import ScopingPolicy

CLINIC = "clinic-scoping"


@pytest.fixture()
def policy() -> ScopingPolicy:
    return ScopingPolicy.load()


# --------------------------------------------------------------------------- #
#  T018 — evaluator: allow / default-deny / audience-absent / unmapped-kind
# --------------------------------------------------------------------------- #
def test_t018_mapped_kind_in_allow_classes_allows(policy):
    # §4a core semantic: an active scope predicate requires an ATTRIBUTED,
    # in-scope row — a null subject no longer passes (fail-closed).
    d = policy.evaluate("appointment", "client_verified",   # schedule ∈ allow
                        subject_household="hhA", subject_clinic=CLINIC,
                        entity_scope=["hhA", CLINIC])
    assert d.allowed and d.reason == "explicit_allow"
    assert d.fact_class == "schedule"


def test_t018_mapped_kind_class_absent_denies(policy):
    # client_verified has no `financial` in its allow_classes
    d = policy.evaluate("balance", "client_verified")
    assert not d.allowed and d.reason == "default_deny_no_rule"
    assert d.fact_class == "financial"


def test_t018_audience_absent_denies_all(policy):
    d = policy.evaluate("appointment", "intruder_role")     # audience not in allow_classes
    assert not d.allowed and d.reason == "default_deny_no_rule"


def test_t018_unmapped_kind_denied_never_by_omission(policy):
    d = policy.evaluate("experimental_unmapped", "owner")   # no kind_to_class entry
    assert not d.allowed and d.reason == "unmapped_kind"
    assert d.fact_class is None                              # class NULL when unmapped


def test_t018_own_household_only_wrong_household(policy):
    # subject_clinic supplied in-scope so own_clinic_only passes and the
    # household predicate is the one under test (§4a: null clinic would deny).
    d = policy.evaluate("visit_summary", "client_verified",
                        subject_household="hhB", subject_clinic=CLINIC,
                        entity_scope=["hhA", CLINIC])
    assert not d.allowed and d.reason == "wrong_household"


def test_t018_own_household_only_own_household_allows(policy):
    d = policy.evaluate("visit_summary", "client_verified",
                        subject_household="hhA", subject_clinic=CLINIC,
                        entity_scope=["hhA", CLINIC])
    assert d.allowed and d.reason == "explicit_allow"


# --------------------------------------------------------------------------- #
#  T019 — reveal-decision audit on EVERY decision
# --------------------------------------------------------------------------- #
def test_t019_revealed_and_withheld_each_write_one_row(repo, policy):
    ref = f"call:t019:{uuid4()}"           # run-unique (append-only log persists)
    log = RevealLog(repo, CLINIC, interaction_ref=ref)
    before = len(repo.get_reveal_decisions(CLINIC))

    allow = policy.evaluate("appointment", "client_verified",
                            subject_household="hhA", subject_clinic=CLINIC,
                            entity_scope=["hhA", CLINIC])
    log.record(audience="client_verified", fact_kind="appointment", decision=allow)

    deny = policy.evaluate("balance", "client_verified")
    log.record(audience="client_verified", fact_kind="balance", decision=deny)

    rows = repo.get_reveal_decisions(CLINIC)
    assert len(rows) == before + 2
    mine = [r for r in rows if r["interaction_ref"] == ref]
    revealed = [r for r in mine if r["decision"] == "revealed"]
    withheld = [r for r in mine if r["decision"] == "withheld"]
    assert len(revealed) == 1 and revealed[0]["reason"] == "explicit_allow"
    assert len(withheld) == 1 and withheld[0]["reason"] == "default_deny_no_rule"
    assert withheld[0]["fact_class"] == "financial"


def test_t019_default_deny_records_reason(repo, policy):
    refb = f"call:t019b:{uuid4()}"
    log = RevealLog(repo, CLINIC, interaction_ref=refb)
    dec = policy.evaluate("appointment", "ghost_audience")   # absent audience
    log.record(audience="caller_unverified", fact_kind="appointment", decision=dec)
    row = [r for r in repo.get_reveal_decisions(CLINIC)
           if r["interaction_ref"] == refb][-1]
    assert row["decision"] == "withheld"
    assert row["reason"] == "default_deny_no_rule"
