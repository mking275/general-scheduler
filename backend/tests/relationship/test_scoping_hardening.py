"""C6 cutover prep — shim hardening reconciliations (shim-retirement.md §4).

Cutover itself is DEFERRED pending rail contract convergence (escalated to
core); these are the sanctioned safe-subset reconciliations, authored in the
shim now because they only ever TIGHTEN scoping:

§4b — an UNRECOGNIZED scope predicate FAILS CLOSED: a typo'd or future
      predicate in policy data withholds (``unrecognized_predicate``), never
      silently no-ops (the old fail-open weakened scoping).
§4a — a NULL subject under an ACTIVE scope predicate DENIES: an unattributed
      row is not "explicitly permitted" for a party-scoped audience (FR-014;
      core's ``vera/memory.py`` entity_ref semantic). A None ``entity_scope``
      likewise denies — an unresolved caller reveals nothing.

The red-team matrix half of §4a (null-household fact through ``ScopedRecall``)
lives in ``test_scoping_red_team.py::test_t031_null_household_fact_withheld_from_scoped_client``.
"""
from uuid import uuid4

import pytest

from backend.relationship.reveal_log import RevealLog
from backend.relationship.scoped_recall import Fact, ScopedRecall, ThothStub
from backend.relationship.scoping_policy import ScopingPolicy

CLINIC = "clinic-hardening"
HH = "hh-hardening-a"


def _policy(predicates: list[str]) -> ScopingPolicy:
    """A minimal policy where `appointment` IS allowed for client_verified —
    so any withhold below is attributable to the predicate under test."""
    return ScopingPolicy(
        allow_classes={"client_verified": ["schedule"]},
        scope_predicates={"client_verified": predicates},
        kind_to_class={"appointment": "schedule"},
    )


# --------------------------------------------------------------------------- #
#  §4b — unrecognized predicate FAILS CLOSED (evaluator)
# --------------------------------------------------------------------------- #
def test_4b_unrecognized_predicate_withholds_at_evaluator():
    # a typo'd predicate ('own_hosuehold_only') must DENY, not no-op.
    d = _policy(["own_hosuehold_only"]).evaluate(
        "appointment", "client_verified",
        subject_household=HH, subject_clinic=CLINIC,
        entity_scope=[HH, CLINIC])
    assert not d.allowed
    assert d.reason == "unrecognized_predicate"
    assert d.fact_class == "schedule"          # class WAS allowed; predicate denied


def test_4b_future_predicate_also_withholds():
    # a future/unknown-but-plausible predicate string fails closed too.
    d = _policy(["own_species_only"]).evaluate(
        "appointment", "client_verified",
        subject_household=HH, subject_clinic=CLINIC,
        entity_scope=[HH, CLINIC])
    assert not d.allowed and d.reason == "unrecognized_predicate"


def test_4b_recognized_predicates_still_allow_in_scope_rows():
    # guard: the else-branch does not swallow the two KNOWN predicates.
    d = _policy(["own_clinic_only", "own_household_only"]).evaluate(
        "appointment", "client_verified",
        subject_household=HH, subject_clinic=CLINIC,
        entity_scope=[HH, CLINIC])
    assert d.allowed and d.reason == "explicit_allow"


async def test_4b_end_to_end_recall_withholds_and_audits_per_fact(repo):
    # Through the full rail: a bogus predicate means NOTHING reveals, and every
    # fact still gets its own reveal-decision audit row (per-fact granularity).
    ref = f"call:4b:{uuid4()}"                 # run-unique (append-only log)
    facts = [
        Fact("appointment", "Tue 3pm", entity_ref="pat:1",
             subject_household=HH, subject_clinic=CLINIC),
        Fact("appointment", "Wed 9am", entity_ref="pat:2",
             subject_household=HH, subject_clinic=CLINIC),
    ]
    sr = ScopedRecall(ThothStub(facts), _policy(["own_hosuehold_only"]),
                      RevealLog(repo, CLINIC, interaction_ref=ref))
    out = await sr.recall("anything", audience="client_verified",
                          entity_scope=[HH, CLINIC])
    assert out == []                           # fail-closed: zero reveals
    mine = [r for r in repo.get_reveal_decisions(CLINIC)
            if r["interaction_ref"] == ref]
    assert len(mine) == len(facts)             # one audit row PER FACT
    assert all(r["decision"] == "withheld" for r in mine)
    assert {r["reason"] for r in mine} == {"unrecognized_predicate"}


# --------------------------------------------------------------------------- #
#  §4a — null subject / null scope under an active predicate DENIES (pinned)
# --------------------------------------------------------------------------- #
def test_4a_null_household_under_own_household_only_denies():
    d = _policy(["own_household_only"]).evaluate(
        "appointment", "client_verified",
        subject_household=None, subject_clinic=CLINIC,
        entity_scope=[HH, CLINIC])
    assert not d.allowed and d.reason == "wrong_household"


def test_4a_null_clinic_under_own_clinic_only_denies():
    d = _policy(["own_clinic_only"]).evaluate(
        "appointment", "client_verified",
        subject_household=HH, subject_clinic=None,
        entity_scope=[HH, CLINIC])
    assert not d.allowed and d.reason == "default_deny_no_rule"


def test_4a_null_entity_scope_under_active_predicate_denies():
    # an unresolved caller (no entity scope) reveals nothing under a predicate —
    # even for a row that IS attributed.
    d = _policy(["own_household_only"]).evaluate(
        "appointment", "client_verified",
        subject_household=HH, subject_clinic=CLINIC,
        entity_scope=None)
    assert not d.allowed and d.reason == "wrong_household"


def test_4a_goldsmith_policy_null_household_denies_for_client():
    # the same pin against the SHIPPED goldsmith config (not just the minimal
    # fixture): client_verified carries own_clinic_only + own_household_only.
    policy = ScopingPolicy.load()
    d = policy.evaluate("visit_summary", "client_verified",
                        subject_household=None, subject_clinic=CLINIC,
                        entity_scope=[HH, CLINIC])
    assert not d.allowed and d.reason == "wrong_household"


def test_4a_attributed_in_scope_row_still_reveals():
    # guard: the tightening denies ONLY ambiguous inputs — the fully attributed,
    # in-scope row keeps revealing.
    policy = ScopingPolicy.load()
    d = policy.evaluate("visit_summary", "client_verified",
                        subject_household=HH, subject_clinic=CLINIC,
                        entity_scope=[HH, CLINIC])
    assert d.allowed and d.reason == "explicit_allow"
