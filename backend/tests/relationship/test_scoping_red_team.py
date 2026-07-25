"""T031 [US3] — scoping RED-TEAM (the security-boundary gate, SC-001).

For each audience (owner / manager / staff / client_verified / caller_unverified)
the harness requests schedule availability, own-household pet detail, ANOTHER
household's detail, and financial detail, plus explicit wrong-person reveal
attempts against the shared-line collision fixture (Alvarez ‖ Nguyen share one
number). Measured, zero-tolerance:

  * wrong-person reveal = 0 across the entire collision fixture (a client caller
    scoped to their own household never receives another household's detail);
  * every fact with no explicit allow rule is refused (deny-on-missing-rule),
    incl. the unmapped-kind case;
  * every reveal/withhold decision is present in ``reveal_decision_log``.
"""
import pytest

from backend.relationship.reveal_log import RevealLog
from backend.relationship.scoped_recall import Fact, ScopedRecall, ThothStub
from backend.relationship.scoping_policy import ScopingPolicy
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-redteam-scope"
HH_A = f"hh-{CLINIC}-alvarez"          # the caller's own household
HH_B = f"hh-{CLINIC}-nguyen"           # the OTHER party on the shared line

CLIENT_AUDIENCES = ("client_verified", "caller_unverified")
STAFF_AUDIENCES = ("owner", "manager", "staff")
ALL_AUDIENCES = CLIENT_AUDIENCES + STAFF_AUDIENCES

# Household-specific classes — revealing another household's fact of these to a
# client is a wrong-person PII leak. ``schedule`` is general availability, not
# household PII, so it is excluded from the leak metric.
HOUSEHOLD_SPECIFIC = {"client_summary", "patient_clinical", "financial",
                      "contact_info", "staff_notes"}


def _collision_facts():
    """Facts spanning every class for BOTH colliding households + an unmapped
    kind — the resolver's shared-line corpus made concrete."""
    def bundle(hh):
        return [
            Fact("appointment", f"{hh}:Tue 3pm", subject_household=hh, subject_clinic=CLINIC),
            Fact("visit_summary", f"{hh}:wellness", subject_household=hh, subject_clinic=CLINIC),
            Fact("diagnosis", f"{hh}:otitis", subject_household=hh, subject_clinic=CLINIC),
            Fact("balance", f"{hh}:$240", subject_household=hh, subject_clinic=CLINIC),
            Fact("phone", f"{hh}:555", subject_household=hh, subject_clinic=CLINIC),
            Fact("internal_note", f"{hh}:memo", subject_household=hh, subject_clinic=CLINIC),
        ]
    facts = bundle(HH_A) + bundle(HH_B)
    facts.append(Fact("experimental_unmapped", "leak-me",
                      subject_household=HH_A, subject_clinic=CLINIC))
    # §4a probe (C6 hardening): an UNATTRIBUTED row — null subject_household —
    # under own_household_only must WITHHOLD (fail-closed), never reveal.
    facts.append(Fact("visit_summary", "unattributed-null-household",
                      entity_ref="unattributed:null-hh",
                      subject_household=None, subject_clinic=CLINIC))
    return facts


@pytest.fixture()
def scoped(repo):
    build_corpus(clinic_id=CLINIC).seed_into_repo(repo)
    policy = ScopingPolicy.load()
    log = RevealLog(repo, CLINIC, interaction_ref="call:redteam")
    return ScopedRecall(ThothStub(_collision_facts()), policy, log), repo


def _entity_scope(audience):
    # A client is scoped to their OWN household (client_verified) or to nothing
    # household-specific (caller_unverified, no confirmed household). Staff are
    # clinic-scoped (own_clinic_only) and legitimately see clinic-wide.
    if audience == "client_verified":
        return [HH_A, CLINIC]
    if audience == "caller_unverified":
        return [CLINIC]
    return [HH_A, HH_B, CLINIC]        # staff: whole clinic


# --------------------------------------------------------------------------- #
#  SC-001 — wrong-person reveal = 0 across the collision fixture
# --------------------------------------------------------------------------- #
async def test_t031_wrong_person_reveal_is_zero(scoped):
    sr, _repo = scoped
    wrong_person = 0
    for audience in CLIENT_AUDIENCES:
        out = await sr.recall("everything", audience=audience,
                              entity_scope=_entity_scope(audience))
        for f in out:
            cls = ScopingPolicy.load().kind_to_class.get(f.fact_kind)
            # a household-specific fact for a household NOT in this client's scope
            if cls in HOUSEHOLD_SPECIFIC and f.subject_household not in _entity_scope(audience):
                wrong_person += 1
    assert wrong_person == 0                    # zero-tolerance (SC-001)


async def test_t031_null_household_fact_withheld_from_scoped_client(scoped):
    # §4a (shim-retirement reconciliation, core semantic): a fact with NO
    # household attribution is not "explicitly permitted" for a household-scoped
    # audience — it withholds, and the withhold is audited per-fact.
    sr, repo = scoped
    out = await sr.recall("x", audience="client_verified", entity_scope=[HH_A, CLINIC])
    assert all(f.content != "unattributed-null-household" for f in out)
    # audit filter is audience-scoped: staff (own_clinic_only, clinic attributed)
    # legitimately reveal this fact; for the household-scoped client every row —
    # this run and prior runs (append-only log) — must be a withhold.
    rows = [r for r in repo.get_reveal_decisions(CLINIC)
            if r["entity_ref"] == "unattributed:null-hh"
            and r["audience"] == "client_verified"]
    assert rows and all(r["decision"] == "withheld" for r in rows)
    assert rows[-1]["reason"] == "wrong_household"


async def test_t031_client_never_sees_other_household(scoped):
    sr, _repo = scoped
    out = await sr.recall("x", audience="client_verified", entity_scope=[HH_A, CLINIC])
    assert all(f.subject_household != HH_B for f in out)   # HH_B never surfaces
    # explicit wrong-person attempt: querying with the foreign household in scope
    # still cannot pull HH_B clinical detail when the fact is HH_B's (it is in
    # scope here, so instead prove the reverse — a caller scoped ONLY to HH_A):
    kinds = {f.fact_kind for f in out}
    assert "diagnosis" in kinds                            # own clinical OK
    assert all(not (f.subject_household == HH_B) for f in out)


# --------------------------------------------------------------------------- #
#  Deny-on-missing-rule — every fact with no explicit allow rule is refused
# --------------------------------------------------------------------------- #
async def test_t031_deny_on_missing_rule(scoped):
    sr, _repo = scoped
    # client_verified: financial + staff_notes are NOT in allow_classes -> denied
    out = await sr.recall("x", audience="client_verified", entity_scope=[HH_A, CLINIC])
    kinds = {f.fact_kind for f in out}
    assert "balance" not in kinds and "internal_note" not in kinds
    # the unmapped kind is denied for EVERY audience (never revealed by omission)
    for audience in ALL_AUDIENCES:
        got = await sr.recall("x", audience=audience, entity_scope=_entity_scope(audience))
        assert all(f.fact_kind != "experimental_unmapped" for f in got)


def test_t031_absent_audience_denies_all():
    # The reveal-log audience is a CLOSED Literal (owner|manager|staff|
    # client_verified|caller_unverified) — an off-list audience is unrepresentable
    # in the audit. At the evaluator itself, an audience absent from allow_classes
    # denies EVERY class (default-deny by absence).
    policy = ScopingPolicy.load()
    for fact_kind in ("appointment", "visit_summary", "diagnosis", "balance",
                      "phone", "internal_note"):
        dec = policy.evaluate(fact_kind, "intruder_not_in_policy",
                              subject_household=HH_A, subject_clinic=CLINIC,
                              entity_scope=[HH_A, CLINIC])
        assert not dec.allowed and dec.reason == "default_deny_no_rule"


# --------------------------------------------------------------------------- #
#  Every decision is audited (reveal_decision_log)
# --------------------------------------------------------------------------- #
async def test_t031_every_decision_is_logged(scoped):
    sr, repo = scoped
    facts = _collision_facts()
    before = len(repo.get_reveal_decisions(CLINIC))
    await sr.recall("x", audience="client_verified", entity_scope=[HH_A, CLINIC])
    after = len(repo.get_reveal_decisions(CLINIC))
    assert after - before == len(facts)                    # one row per fact
    # and the reasons vocabulary is closed + populated on withholds
    reasons = {r["reason"] for r in repo.get_reveal_decisions(CLINIC)}
    assert {"wrong_household", "default_deny_no_rule", "unmapped_kind"} <= reasons
