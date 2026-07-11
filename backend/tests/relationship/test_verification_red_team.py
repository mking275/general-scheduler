"""T033 [US5] — spoofed-caller-ID / soft-confirm-as-auth RED-TEAM (SC-005 = 0).

A matched (or spoofed-matching) number requests changes with no / insufficient /
WRONG knowledge factors. Zero-tolerance, measured across the whole battery:

  * a spoofed caller-ID authorizes 0 changes;
  * soft-confirm alone authorizes 0 changes;
  * a high-sensitivity action always requires 2 factors or a staff callback;
  * an INCORRECT knowledge-factor value is REJECTED — a wrong pet name (no match
    in patient_household_link) and a wrong appointment day (no match in the 010
    booking/schedule store) each fail the factor and block the change (the bar
    VALIDATES, not merely prompts — H3/FR-018);
  * every attempt writes a verification_challenge row.

The 010 booking/schedule store is supplied as an appointment source: the Alvarez
household has a real Tuesday appointment; any other day is a wrong value.
"""
import pytest

from backend.relationship.verification import (
    PresentedFactor, VerificationService,
)
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-redteam-verify"
HH = f"hh-{CLINIC}-alvarez"            # Rex + Bella active, Buddy deceased
TOM = f"party-{CLINIC}-c1002"          # the matched (or spoofed-matching) party


@pytest.fixture()
def svc(repo):
    build_corpus(clinic_id=CLINIC).seed_into_repo(repo)
    # 010 booking/schedule store source: real appt is Tuesday for the Alvarez HH.
    return VerificationService(
        repo,
        appointment_source=lambda hid: ["Tuesday"] if hid == HH else [],
    )


def _authorized(res):
    return res.authorizes_change


# --------------------------------------------------------------------------- #
#  The battery — every illegitimate attempt authorizes ZERO changes (SC-005)
# --------------------------------------------------------------------------- #
def test_t033_zero_changes_authorized_across_battery(svc, repo):
    before = len(repo.get_verification_challenges(CLINIC))
    attempts = [
        # (action, binding_level, factors)
        ("reschedule", "soft_confirmed", []),                                  # soft-confirm alone
        ("contact_edit", "soft_confirmed", []),                                # spoofed caller-ID, no factor
        ("cancel", "soft_confirmed", [PresentedFactor("pet_name", "Fido")]),   # wrong pet
        ("reschedule", "soft_confirmed", [PresentedFactor("appointment_day", "Friday")]),  # wrong day
        ("cancel", "soft_confirmed", [PresentedFactor("pet_name", "Buddy")]),  # deceased pet
        ("contact_edit", "soft_confirmed", [PresentedFactor("pet_name", "Rex")]),  # 1 of 2 (high)
        ("refill_request", "soft_confirmed",
         [PresentedFactor("pet_name", "Rex"), PresentedFactor("appointment_day", "Friday")]),  # 1 real + 1 wrong
    ]
    authorized = 0
    for action, level, factors in attempts:
        res = svc.require_verification(action, TOM, binding_level=level,
                                       household_id=HH, clinic_id=CLINIC,
                                       presented_factors=factors)
        if _authorized(res):
            authorized += 1
    assert authorized == 0                                     # SC-005: zero-tolerance
    # every attempt wrote a challenge row (the audit spine)
    after = len(repo.get_verification_challenges(CLINIC))
    assert after - before == len(attempts)


def test_t033_soft_confirm_alone_never_authorizes(svc):
    for action in ("reschedule", "cancel", "contact_edit", "refill_request"):
        res = svc.require_verification(action, TOM, binding_level="soft_confirmed",
                                       household_id=HH, clinic_id=CLINIC)
        assert res.authorizes_change is False


def test_t033_wrong_factor_values_rejected(svc):
    # wrong pet name -> no match in patient_household_link
    r1 = svc.require_verification("reschedule", TOM, household_id=HH, clinic_id=CLINIC,
                                  presented_factors=[PresentedFactor("pet_name", "Fido")])
    assert r1.outcome == "failed"
    # wrong appointment day -> no match in the 010 schedule store
    r2 = svc.require_verification("reschedule", TOM, household_id=HH, clinic_id=CLINIC,
                                  presented_factors=[PresentedFactor("appointment_day", "Friday")])
    assert r2.outcome == "failed"
    # the CORRECT values DO clear the bar (proving it validates, not blocks-all)
    r3 = svc.require_verification("reschedule", TOM, household_id=HH, clinic_id=CLINIC,
                                  presented_factors=[PresentedFactor("pet_name", "Rex")])
    assert r3.outcome == "passed"


def test_t033_high_sensitivity_always_needs_two_or_callback(svc):
    # 1 real factor on a high action -> blocked
    one = svc.require_verification("contact_edit", TOM, household_id=HH, clinic_id=CLINIC,
                                   presented_factors=[PresentedFactor("pet_name", "Rex")])
    assert one.outcome == "failed" and one.factors_required == 2
    # 2 real factors -> passes
    two = svc.require_verification(
        "contact_edit", TOM, household_id=HH, clinic_id=CLINIC,
        presented_factors=[PresentedFactor("pet_name", "Rex"),
                           PresentedFactor("appointment_day", "Tuesday")])
    assert two.outcome == "passed"
    # or defer to a staff callback
    deferred = svc.require_verification("refill_request", TOM, household_id=HH,
                                        clinic_id=CLINIC, prefer_staff_callback=True)
    assert deferred.outcome == "deferred_staff_callback"
    assert deferred.authorizes_change is False


def test_t033_no_raw_secret_value_persisted(svc, repo):
    svc.require_verification("reschedule", TOM, household_id=HH, clinic_id=CLINIC,
                             presented_factors=[PresentedFactor("pet_name", "Fido")])
    last = repo.get_verification_challenges(CLINIC)[-1]
    assert last["factors_presented_json"] == [{"factor": "pet_name", "passed": False}]
    assert "Fido" not in str(last)                             # raw value never stored
