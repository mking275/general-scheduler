"""Feature 009 — T045 final checkpoint (the go-live gate; the SC harness).

Re-verifies, at the go-live checkpoint, the four hard gates + the SC harness:

  * **counsel-gate-before-normalize (FR-004)** — across a full batch, **0**
    databases reach ``profiled``/``normalized`` without a recorded
    ``counsel_signoff`` row (the whole-spec legal gate; the previously-missing
    dedicated harness, added by analyze remediation F4). No engineering bypass.
  * **re-run-diff idempotency proof (SC-003)** — reran as the go-live gate.
  * **scope guard** — the on-ramp ends at ``shadow_ready``: no delta-sync /
    dual-path-write / verb-promotion / cutover verb exists in the tier.
  * **the SC gate harnesses exist** — every SC-001…SC-010 build-time gate has a
    dedicated harness (SC-007 timing is Pilot-Activation-homed).

No practice reaches ``shadow_ready`` unless every SC gate passes (proven by the
batch: the AR-variance / dirty / partial practices never reach it).
"""
import os
import uuid

from backend.envelope.batch import BatchOrchestrator
from backend.envelope.idempotency import rerun_diff
from backend.envelope.onboarding_repository import OnboardingRepository
from backend.envelope.readiness import (
    scan_source_for_scope_leak, scan_source_for_staff_verbs,
)
from backend.relationship.household_repository import HouseholdRepository
from backend.relationship.review_queue import ReviewQueue
from backend.tests.envelope import _pipeline as P
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_batch

_NORMALIZED_PLUS = {"normalized", "verified", "reconciled",
                    "identity_bootstrapped", "shadow_ready", "delta"}
_PROFILED_PLUS = _NORMALIZED_PLUS | {"profiled"}


def _batch(db_url, *, counsel_signed, n=6, seed=999):
    repo = OnboardingRepository(db_url)
    repo.init_db()
    hr = HouseholdRepository(db_url)
    hr.init_db()
    clinic = f"gate-{uuid.uuid4().hex[:6]}"
    exports = generate_batch(seed=seed, n=n, clinic_id=clinic)
    result = BatchOrchestrator(repo, ReviewQueue(hr)).run(
        clinic, exports, counsel_signed=counsel_signed)
    return repo, clinic, exports, result


# --------------------------------------------------------------------------- #
#  The counsel gate — the whole-spec legal gate (F4 remediation)
# --------------------------------------------------------------------------- #
def test_counsel_gate_no_normalize_without_signoff_full_batch(db_url):
    """With NO counsel sign-off, 0 databases reach profiled/normalized across the
    whole batch — the gate has no engineering bypass."""
    repo, clinic, exports, result = _batch(db_url, counsel_signed=False)
    for e in exports:
        pdb = repo.get_practice_database_by_practice(e.practice_id)
        assert pdb["state"] not in _PROFILED_PLUS, (
            f"{e.practice_id} reached {pdb['state']} without a counsel_signoff")
        assert not repo.has_counsel_signoff(e.practice_id)
    # nothing normalized -> the canonical store never populated for any practice.
    assert all(repo.count_canonical("canonical_record", e.practice_id) == 0
               for e in exports)


def test_counsel_gate_every_normalized_practice_has_signoff(db_url):
    """With sign-off, every practice that reached profiled/normalized+ carries a
    recorded counsel_signoff row (0 exceptions)."""
    repo, clinic, exports, result = _batch(db_url, counsel_signed=True)
    normalized_seen = 0
    for e in exports:
        pdb = repo.get_practice_database_by_practice(e.practice_id)
        if pdb["state"] in _PROFILED_PLUS:
            normalized_seen += 1
            assert repo.has_counsel_signoff(e.practice_id), (
                f"{e.practice_id} at {pdb['state']} without a counsel_signoff")
    assert normalized_seen > 0            # the batch actually normalized practices


# --------------------------------------------------------------------------- #
#  Re-run-diff idempotency proof — reran as the go-live gate (SC-003)
# --------------------------------------------------------------------------- #
def test_rerun_diff_idempotency_proof_holds(repo):
    pid = f"p-gate-idem-{uuid.uuid4().hex[:6]}"
    exp, adapter, profile, _sm = P.normalize_once(repo, pid, seed=1234)
    report = rerun_diff(repo, P.CLINIC, pid, adapter, profile, exp)
    assert report.is_idempotent
    assert report.duplicate_count == 0
    assert report.lineage_coverage == 1.0
    assert report.diff == []


# --------------------------------------------------------------------------- #
#  No practice reaches shadow_ready unless every gate passes (the batch proof)
# --------------------------------------------------------------------------- #
def test_no_gated_practice_reaches_shadow_ready(db_url):
    repo, clinic, exports, result = _batch(db_url, counsel_signed=True, n=6)
    for pid, o in result.outcomes.items():
        if o.shadow_ready:
            # a shadow_ready practice cleared EVERY criterion.
            pr = repo.get_practice_readiness(pid)
            assert pr["shadow_ready"] is True
            assert all(pr["criteria"].values())
            assert pr["invisible_adoption_asserted"] is True
        else:
            # a not-ready practice failed at least one gate (held/blocked/partial).
            assert repo.get_practice_database_by_practice(pid)["state"] != "shadow_ready"


# --------------------------------------------------------------------------- #
#  Scope guard — the on-ramp ends at shadow_ready
# --------------------------------------------------------------------------- #
def test_scope_guard_no_ongoing_operations_verb():
    leaks = scan_source_for_scope_leak()
    assert leaks == [], f"ongoing-operations verb leaked into the on-ramp tier: {leaks}"


def test_invisible_adoption_scan_clean():
    assert scan_source_for_staff_verbs() == []


# --------------------------------------------------------------------------- #
#  SC coverage — every build-time SC gate has a dedicated harness
# --------------------------------------------------------------------------- #
def test_all_sc_gate_harnesses_present():
    here = os.path.dirname(os.path.abspath(__file__))
    # SC -> the dedicated harness file (SC-007 is Pilot-Activation-homed: no file).
    sc_harness = {
        "SC-001": "test_chain_of_custody.py",
        "SC-002": "test_profile_gate.py",
        "SC-003": "test_idempotency_lineage.py",
        "SC-004": "test_financial_recon.py",
        "SC-005": "test_reconciliation.py",       # produced+delivered pre-shadow_ready
        "SC-006": "test_invisible_adoption.py",
        "SC-008": "test_identity_handoff.py",
        "SC-009": "test_partial_delta.py",
        "SC-010": "test_batch.py",
    }
    for sc, fname in sc_harness.items():
        assert os.path.exists(os.path.join(here, fname)), f"{sc} harness {fname} missing"
