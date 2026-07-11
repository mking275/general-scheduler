"""Phase C verification — T015 (tiered bar), T016 (escalation), T017 (adapter)."""
from typing import get_args

import pytest

from backend.models import VerificationState
from backend.relationship.verification import (
    PresentedFactor, VerificationPolicy, VerificationService, VerificationSession,
    derive_audience, reconcile_binding_tier,
)
from backend.voice.shims.channel_binding_shim import VerificationLevel
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-verify"
HH = f"hh-{CLINIC}-alvarez"          # Rex + Bella active, Buddy deceased
TOM = f"party-{CLINIC}-c1002"


@pytest.fixture()
def seeded(repo):
    corpus = build_corpus(clinic_id=CLINIC)
    corpus.seed_into_repo(repo)
    return corpus


@pytest.fixture()
def svc(repo):
    # 010 booking store stub: the Alvarez household has a Tuesday appointment.
    return VerificationService(
        repo,
        appointment_source=lambda hid: ["Tuesday"] if hid == HH else [],
    )


# --------------------------------------------------------------------------- #
#  T015 — tiered bar; caller-ID / soft-confirm authorizes ZERO changes (SC-005)
# --------------------------------------------------------------------------- #
def test_t015_soft_confirm_alone_authorizes_no_change(seeded, svc):
    # No knowledge factors presented — pure caller-ID/soft-confirm.
    res = svc.require_verification("reschedule", TOM, binding_level="soft_confirmed",
                                   household_id=HH, clinic_id=CLINIC)
    assert res.outcome == "failed"
    assert res.authorizes_change is False


def test_t015_low_sensitivity_one_factor_passes(seeded, svc):
    res = svc.require_verification(
        "reschedule", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("pet_name", "Rex")],
    )
    assert res.outcome == "passed"
    assert res.factors_required == 1
    assert res.core_tier == "code_verified"


def test_t015_high_sensitivity_needs_two_factors(seeded, svc):
    one = svc.require_verification(
        "contact_edit", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("pet_name", "Rex")],
    )
    assert one.outcome == "failed"          # 1 of 2 — blocked
    two = svc.require_verification(
        "contact_edit", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("pet_name", "Rex"),
                           PresentedFactor("appointment_day", "Tuesday")],
    )
    assert two.outcome == "passed"
    assert two.factors_required == 2
    assert two.core_tier == "identity_confirmed"


def test_t015_high_sensitivity_may_defer_to_staff_callback(seeded, svc):
    res = svc.require_verification(
        "refill_request", TOM, household_id=HH, clinic_id=CLINIC,
        prefer_staff_callback=True,
    )
    assert res.outcome == "deferred_staff_callback"


def test_t015_wrong_pet_name_fails_and_leaves_state_unchanged(seeded, svc, repo):
    before = len(repo.get_verification_challenges(CLINIC))
    res = svc.require_verification(
        "reschedule", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("pet_name", "Fido")],   # not in roster
    )
    assert res.outcome == "failed"
    assert res.staff_callback_offered is False   # low tier cannot defer
    rows = repo.get_verification_challenges(CLINIC)
    assert len(rows) == before + 1
    last = rows[-1]
    assert last["outcome"] == "failed"
    # the raw secret value is never persisted — only factor name + pass/fail
    assert last["factors_presented_json"] == [{"factor": "pet_name", "passed": False}]
    assert "Fido" not in str(last)


def test_t015_deceased_pet_never_satisfies_factor(seeded, svc):
    # "Buddy" exists in the household but is DECEASED — must fail (corpus red-team).
    res = svc.require_verification(
        "reschedule", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("pet_name", "Buddy")],
    )
    assert res.outcome == "failed"


def test_t015_wrong_appointment_day_fails(seeded, svc):
    res = svc.require_verification(
        "reschedule", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("appointment_day", "Friday")],  # real day is Tue
    )
    assert res.outcome == "failed"


def test_t015_first_token_pet_name_matches(seeded, svc):
    # roster carries "Rex" already, but exercise exact-or-first-token on a full name
    res = svc.require_verification(
        "reschedule", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("pet_name", "rex")],   # case-folded
    )
    assert res.outcome == "passed"


# --------------------------------------------------------------------------- #
#  T016 — mid-call sensitivity escalation re-gate
# --------------------------------------------------------------------------- #
def test_t016_escalation_reapplies_higher_bar(seeded, svc):
    session = VerificationSession(svc, clinic_id=CLINIC, party_id=TOM, household_id=HH)
    # cleared the low bar for a reschedule with 1 factor
    low = session.request("reschedule",
                          [PresentedFactor("pet_name", "Rex")])
    assert low.outcome == "passed"
    # escalate to a contact edit (high, 2 factors) with NO new factor -> blocked
    blocked = session.request("contact_edit")
    assert blocked.outcome == "failed"
    assert blocked.factors_required == 2
    # supply the second factor -> the accumulated set (2) clears the higher bar
    cleared = session.request("contact_edit",
                              [PresentedFactor("appointment_day", "Tuesday")])
    assert cleared.outcome == "passed"
    assert session.passed_factors == {"pet_name", "appointment_day"}


# --------------------------------------------------------------------------- #
#  T017 — non-mutating boundary adapter (R5); enumerates BOTH 010 enums
# --------------------------------------------------------------------------- #
def test_t017_adapter_total_over_both_enums():
    expected = {
        "unverified": "unverified",
        "none": "unverified",
        "soft_confirmed": "phone_match",
        "strong": "identity_confirmed",
    }
    # every VerificationState value
    for member in VerificationState:
        assert reconcile_binding_tier(member.value) == expected[member.value]
    # every shim VerificationLevel value
    for value in get_args(VerificationLevel):
        assert reconcile_binding_tier(value) == expected[value]


def test_t017_code_verified_is_not_a_boundary_target():
    assert "code_verified" not in set(
        reconcile_binding_tier(v) for v in ("unverified", "none", "soft_confirmed", "strong")
    )


def test_t017_no_reverse_write_into_010_enums():
    # The adapter is one-way: it returns a plain core string, never a 010 enum,
    # and the 010 enum members are untouched.
    out = reconcile_binding_tier(VerificationState.SOFT_CONFIRMED.value)
    assert out == "phone_match"
    assert not isinstance(out, VerificationState)
    # 010 strings preserved
    assert VerificationState.SOFT_CONFIRMED.value == "soft_confirmed"
    assert VerificationState.UNVERIFIED.value == "unverified"
    assert set(get_args(VerificationLevel)) == {"none", "soft_confirmed", "strong"}


def test_t017_phone_match_binding_authorizes_only_unverified_scope():
    # a phone_match (caller-ID) binding -> caller_unverified audience, not client_verified
    assert derive_audience("phone_match") == "caller_unverified"
    assert derive_audience("unverified") == "caller_unverified"
    # only a knowledge factor grants client_verified
    assert derive_audience("code_verified") == "client_verified"
    assert derive_audience("identity_confirmed") == "client_verified"


def test_t017_audience_computed_from_tier_plus_role_not_caller_id():
    # staff role sets the staff-side audience regardless of tier
    assert derive_audience("phone_match", staff_role="manager") == "manager"
    assert derive_audience("unverified", staff_role="owner") == "owner"
    assert derive_audience("identity_confirmed", staff_role="staff") == "staff"
