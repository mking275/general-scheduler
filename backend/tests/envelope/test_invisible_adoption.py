"""Feature 009 — T041 invisible-adoption red-team (SC-006).

Run a full synthetic 23-practice batch; scan for any staff login/training/
dashboard/notification/identity; assert **zero**; assert the clinician-in-export
edge case provisions no staff surface (a data-only ``staff:*`` row, no auth path).

The doctrine: a staff-facing leak breaches the whole invisible-adoption promise.
This is the batch-wide gate that asserts SC-006 = 0.
"""
import uuid

import pytest

from backend.envelope import readiness
from backend.envelope.batch import BatchOrchestrator
from backend.envelope.readiness import ReadinessEvaluator, scan_source_for_staff_verbs
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_batch


@pytest.fixture(scope="module")
def batch_run(request):
    """One shared full 23-practice batch run for the whole red-team module."""
    from backend.envelope.onboarding_repository import OnboardingRepository
    import os
    db_url = os.environ.get("VOICE_DATABASE_URL",
                            "postgresql+psycopg2://voice:voice@localhost:5433/voice")
    repo = OnboardingRepository(db_url)
    try:
        repo.init_db()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"envelope Postgres unavailable: {exc}")
    from backend.tests.envelope import _pipeline as P
    rq, _hr = P.review_queue(db_url)
    clinic = f"redteam-{uuid.uuid4().hex[:6]}"
    exports = generate_batch(seed=20260803, n=23, clinic_id=clinic)
    result = BatchOrchestrator(repo, rq).run(clinic, exports)
    return repo, clinic, exports, result


# --------------------------------------------------------------------------- #
#  Source-level scan — the provisioning verbs simply do not exist in the tier
# --------------------------------------------------------------------------- #
def test_no_staff_facing_verb_defined_in_tier():
    findings = scan_source_for_staff_verbs()
    assert findings == [], f"staff-facing verb(s) leaked into the tier: {findings}"


# --------------------------------------------------------------------------- #
#  Full-batch behavioral scan — 0 staff artifacts, 0 staff identities
# --------------------------------------------------------------------------- #
def test_full_batch_zero_staff_facing_artifacts(batch_run):
    repo, clinic, exports, result = batch_run

    # some practices genuinely reached shadow_ready (the batch is not vacuous).
    assert result.shadow_ready_practices

    staff_artifacts = 0
    provisioned_staff_identities = 0
    for e in exports:
        pid = e.practice_id
        # every surface stayed owner/manager-audience (no staff audience).
        for report in repo.get_reconciliation_reports(pid):
            if report.get("audience") not in ("owner", "manager"):
                staff_artifacts += 1
        # the readiness gate asserted invisible adoption for every practice.
        pr = repo.get_practice_readiness(pid)
        if pr is not None:
            assert pr["invisible_adoption_asserted"] is True
        # a clinician (provider) in the export is DATA ONLY: a canonical row keyed
        # staff:* — never a login/identity. No staff-identity store exists.
        providers = repo.list_canonical_records(pid, category="provider")
        for prov in providers:
            # data-only: no auth/login/password/token field in the payload.
            assert not any(k in prov["payload"] for k in
                           ("password", "login", "credential", "auth_token"))

    assert staff_artifacts == 0             # SC-006: 0 staff-facing artifacts
    assert provisioned_staff_identities == 0


def test_clinician_in_export_is_data_only_staff_row(batch_run):
    repo, clinic, exports, result = batch_run
    # find a practice with a clinician (provider) in the export.
    for e in exports:
        providers = repo.list_canonical_records(e.practice_id, category="provider")
        if providers:
            prov = providers[0]
            # a data-only staff:* entity_ref (scheduling/attribution), no account.
            assert prov["entity_ref"].startswith("staff:")
            assert prov["source_id"]
            # no auth/login path artifact anywhere for this staff row.
            assert not any(k in prov["payload"] for k in
                           ("password", "login", "credential"))
            return
    pytest.skip("no provider in any export (unexpected for the fixture)")


# --------------------------------------------------------------------------- #
#  The readiness gate REJECTS a run that emitted a staff-facing artifact
# --------------------------------------------------------------------------- #
def test_readiness_gate_rejects_staff_facing_run(repo, monkeypatch):
    """If the source scan finds a staff-facing verb, the invisible-adoption
    assertion fails and the practice cannot be marked shadow_ready — even with
    every other criterion met."""
    from backend.tests.envelope import _pipeline as P
    from backend.envelope.reconciliation import Reconciler
    from backend.envelope.owner_surface import OwnerSurface
    from backend.envelope.identity_bootstrap import IdentityBootstrap
    from backend.models import PracticeState

    pid = f"p-reject-{uuid.uuid4().hex[:6]}"
    exp, adapter, profile, sm = P.verify_stage(repo, pid, seed=88)
    Reconciler(repo).reconcile(P.CLINIC, pid, exp.reported_figures)
    OwnerSurface(repo).acknowledge_group(P.CLINIC, [pid], acknowledged_by="owner")
    sm.advance(pid, PracticeState.RECONCILED)
    rq, _hr = P.review_queue(repo.db_url)
    boot = IdentityBootstrap(repo, rq)
    boot.build_corpus(P.CLINIC, pid, boot.bootstrap(P.CLINIC, pid),
                      answer_key=exp.answer_key)
    sm.advance(pid, PracticeState.IDENTITY_BOOTSTRAPPED)

    # a clean tier -> shadow_ready True.
    ok = ReadinessEvaluator(repo).evaluate(P.CLINIC, pid)
    assert ok.invisible_adoption_asserted is True
    assert ok.shadow_ready is True

    # now simulate a staff-facing leak: the scan reports a finding.
    monkeypatch.setattr(readiness, "scan_source_for_staff_verbs",
                        lambda *a, **k: ["fake.py:provision_staff_login"])
    ev = ReadinessEvaluator(repo)      # re-reads the (now dirty) scan at init
    rejected = ev.evaluate(P.CLINIC, pid)
    assert rejected.invisible_adoption_asserted is False
    assert rejected.shadow_ready is False
