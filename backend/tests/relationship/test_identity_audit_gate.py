"""Feature 009+011 — identity audit gate (the 009→011 resolver trust seam).

Proves the gate is DEFAULT-DENY and that it correctly wires the 009
``IdentityAuditCorpus`` into the 011 resolver's auto-ID trust: no corpus /
below-threshold precision / undisposed collisions keep auto-ID untrusted (the
resolver stays neutral), while a clean audit lifts the bar. The soft-confirm /
verification fallback is unaffected either way.
"""
import uuid

import pytest

from backend.models import (
    HouseholdReviewQueue, IdentityAuditCorpus, ResolutionOutcome,
)
from backend.relationship.identity_audit_gate import (
    DEFAULT_MIN_PRECISION, IdentityAuditGate, build_gated_resolver,
)
from backend.relationship.identity_resolver import IdentityResolver
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-audit-gate"


# --------------------------------------------------------------------------- #
#  Fixtures — an OnboardingRepository (corpus store) alongside the shared PG
# --------------------------------------------------------------------------- #
@pytest.fixture()
def audit_repo(db_url):
    from backend.envelope.onboarding_repository import OnboardingRepository

    r = OnboardingRepository(db_url)
    try:
        r.init_db()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"envelope Postgres unavailable at {db_url}: {exc}")
    return r


def _pid() -> str:
    return f"p-gate-{uuid.uuid4().hex[:8]}"


def _seed_corpus(audit_repo, practice_id, *, precision, clinic=CLINIC,
                 collisions=1, duplicates=0, false_positives=0):
    scored = {
        "flagged_phone_count": collisions + duplicates,
        "proposal_count": 3,
        "collision_count": collisions,
        "duplicate_count": duplicates,
        "false_positives": [f"555000{i:04d}" for i in range(false_positives)],
        "true_positives": ["5551110000"],
    }
    if precision is not None:
        scored["precision"] = precision
    audit_repo.append_identity_audit_corpus(IdentityAuditCorpus(
        clinic_id=clinic, practice_id=practice_id,
        proposals=[{"practice_id": practice_id, "entity_ref": "client:ezyvet_c1",
                    "household_ref": "household:vah_x", "source_id": "1"}],
        collisions=[{"practice_id": practice_id, "shared_phone": "5551110000",
                     "entity_refs": ["client:ezyvet_c1", "client:ezyvet_c2"],
                     "proposal_type": "collision", "review_item_id": "r1"}],
        answer_key_scored_precision=scored,
    ))


# --------------------------------------------------------------------------- #
#  DEFAULT-DENY paths
# --------------------------------------------------------------------------- #
def test_no_corpus_denies(audit_repo):
    gate = IdentityAuditGate(audit_repo)
    dec = gate.evaluate(_pid())
    assert dec.passed is False
    assert dec.corpus_present is False
    assert "no_corpus" in dec.reasons
    # convenience answers agree
    assert gate.passed(dec.practice_id) is False
    assert gate.trust_auto_id(dec.practice_id) is False


def test_precision_below_threshold_denies(audit_repo):
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=0.50)
    dec = IdentityAuditGate(audit_repo).evaluate(pid)
    assert dec.passed is False
    assert dec.precision == 0.50
    assert "precision_below_threshold" in dec.reasons


def test_unscored_precision_denies(audit_repo):
    # real-export corpus: no answer key -> precision omitted -> default-deny.
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=None)
    dec = IdentityAuditGate(audit_repo).evaluate(pid)
    assert dec.passed is False
    assert dec.precision_scored is False
    assert "precision_unscored" in dec.reasons


def test_false_positive_denies(audit_repo):
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=0.99, false_positives=2)
    dec = IdentityAuditGate(audit_repo).evaluate(pid)
    assert dec.passed is False
    assert dec.false_positive_count == 2
    assert "false_positives_present" in dec.reasons


# --------------------------------------------------------------------------- #
#  PASS path
# --------------------------------------------------------------------------- #
def test_clean_high_precision_corpus_passes(audit_repo):
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=1.0)
    dec = IdentityAuditGate(audit_repo).evaluate(pid)
    assert dec.passed is True
    assert dec.reasons == []
    assert dec.precision == 1.0
    assert dec.collision_count == 1


def test_threshold_boundary_passes_at_floor(audit_repo):
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=DEFAULT_MIN_PRECISION)
    assert IdentityAuditGate(audit_repo).passed(pid) is True


# --------------------------------------------------------------------------- #
#  Review-queue disposition gating
# --------------------------------------------------------------------------- #
def test_pending_collisions_deny(audit_repo, repo):
    # repo == HouseholdRepository (relationship conftest); write a PENDING row.
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=1.0)
    repo.create_review_item(HouseholdReviewQueue(
        clinic_id=CLINIC, proposal_type="collision",
        subject_refs_json=[{"practice_id": pid, "entity_ref": "client:ezyvet_c1"}],
        evidence_json={"practice_id": pid, "shared_phone": "5551110000"},
        status="pending"))
    gate = IdentityAuditGate(audit_repo, review_repo=repo)
    dec = gate.evaluate(pid, clinic_id=CLINIC)
    assert dec.passed is False
    assert dec.disposition_evaluated is True
    assert dec.pending_review_count == 1
    assert "collisions_undisposed" in dec.reasons


def test_dispositioned_collisions_pass(audit_repo, repo):
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=1.0)
    repo.create_review_item(HouseholdReviewQueue(
        clinic_id=CLINIC, proposal_type="collision",
        subject_refs_json=[{"practice_id": pid, "entity_ref": "client:ezyvet_c1"}],
        evidence_json={"practice_id": pid, "shared_phone": "5551110000"},
        status="rejected"))
    gate = IdentityAuditGate(audit_repo, review_repo=repo)
    dec = gate.evaluate(pid, clinic_id=CLINIC)
    assert dec.passed is True
    assert dec.disposition_evaluated is True
    assert dec.pending_review_count == 0
    assert dec.resolved_review_count == 1


def test_disposition_scoped_to_practice(audit_repo, repo):
    # a PENDING row for a DIFFERENT practice must not block this practice.
    pid, other = _pid(), _pid()
    _seed_corpus(audit_repo, pid, precision=1.0)
    repo.create_review_item(HouseholdReviewQueue(
        clinic_id=CLINIC, proposal_type="collision",
        subject_refs_json=[{"practice_id": other, "entity_ref": "client:ezyvet_c9"}],
        evidence_json={"practice_id": other, "shared_phone": "5559990000"},
        status="pending"))
    dec = IdentityAuditGate(audit_repo, review_repo=repo).evaluate(pid, clinic_id=CLINIC)
    assert dec.passed is True
    assert dec.pending_review_count == 0


# --------------------------------------------------------------------------- #
#  Resolver wiring — the actual 011 auto-ID trust behaviour
# --------------------------------------------------------------------------- #
def _seed_household(repo):
    """Seed the household read path so a single-match phone RESOLVES_SINGLE."""
    corpus = build_corpus(clinic_id=CLINIC)
    corpus.seed_into_repo(repo)
    return corpus


def _single_match_phone(corpus):
    for phone, spec in corpus.answer_key["phone_lookups"].items():
        if spec["match_kind"] == "single":
            return phone
    raise AssertionError("fixture has no single-match phone")


def test_gated_resolver_denies_auto_id_without_audit(audit_repo, repo):
    corpus = _seed_household(repo)
    phone = _single_match_phone(corpus)
    pid = _pid()                                    # NO audit corpus seeded
    gate = IdentityAuditGate(audit_repo)
    resolver = build_gated_resolver(repo, gate, pid)
    assert resolver.audit_only is True              # default-deny
    result = resolver.resolve(CLINIC, phone, "phone")
    assert result.outcome == ResolutionOutcome.RESOLVED_SINGLE   # match still found
    auto = resolver.auto_id_response(result)
    assert auto["mode"] == "neutral_prompt"         # ...but no name spoken


def test_gated_resolver_trusts_auto_id_after_clean_audit(audit_repo, repo):
    corpus = _seed_household(repo)
    phone = _single_match_phone(corpus)
    pid = _pid()
    _seed_corpus(audit_repo, pid, precision=1.0)
    gate = IdentityAuditGate(audit_repo)
    resolver = build_gated_resolver(repo, gate, pid)
    assert resolver.audit_only is False             # audit lifted default-deny
    result = resolver.resolve(CLINIC, phone, "phone")
    assert result.outcome == ResolutionOutcome.RESOLVED_SINGLE
    auto = resolver.auto_id_response(result)
    assert auto["mode"] == "soft_confirm_by_name"   # now trusted to greet by name
    assert auto["authorizes_change"] is False       # ...still identification only


def test_soft_confirm_fallback_unaffected_by_gate(audit_repo, repo):
    # Even with a FAILING gate (untrusted), disambiguation via the neutral prompt
    # still resolves a caller — the fallback path is never broken by the gate.
    corpus = _seed_household(repo)
    phone = _single_match_phone(corpus)
    pid = _pid()                                    # no corpus -> untrusted
    resolver = build_gated_resolver(repo, IdentityAuditGate(audit_repo), pid)
    result = resolver.resolve(CLINIC, phone, "phone")
    # the neutral prompt is always available regardless of trust
    assert resolver.auto_id_response(result)["prompt"] == IdentityResolver.NEUTRAL_PROMPT
