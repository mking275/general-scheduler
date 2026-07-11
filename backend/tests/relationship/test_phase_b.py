"""Phase B verification — T010 (LIMIT 1 kill), T011, T012, T013."""
import inspect

import pytest

from backend.models import ResolutionOutcome
from backend.relationship import review_queue as rq_mod
from backend.relationship.identity_resolver import IdentityResolver
from backend.relationship.review_queue import ReviewQueue
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-phase-b"


@pytest.fixture()
def seeded(repo):
    corpus = build_corpus(clinic_id=CLINIC)
    corpus.seed_into_repo(repo)
    return corpus


# --------------------------------------------------------------------------- #
#  T010 — the LIMIT 1 kill (ZERO-TOLERANCE)
# --------------------------------------------------------------------------- #
def test_t010_multi_match_never_returns_single(seeded, repo):
    r = IdentityResolver(repo)
    ak = seeded.answer_key
    for phone in ak["multi_match_phones"]:
        result = r.resolve(CLINIC, phone, "phone")
        # NOT ONCE a single candidate on a multi-match line
        assert result.match_count > 1, phone
        assert result.outcome != ResolutionOutcome.RESOLVED_SINGLE, phone
        assert result.outcome == ResolutionOutcome.AMBIGUOUS_MULTI, phone
        assert result.is_shared_line


def test_t010_resolved_single_only_on_exact_phone_single(seeded, repo):
    r = IdentityResolver(repo)
    ak = seeded.answer_key
    for phone in ak["single_match_phones"]:
        result = r.resolve(CLINIC, phone, "phone")
        assert result.outcome == ResolutionOutcome.RESOLVED_SINGLE
        assert result.match_count == 1


def test_t010_email_and_fuzzy_never_resolved_single(seeded, repo):
    r = IdentityResolver(repo)
    # an email that resolves to exactly one party still NEVER auto-IDs
    result = r.resolve(CLINIC, "jane.alvarez@example.com", "email")
    assert result.match_count == 1
    assert result.outcome != ResolutionOutcome.RESOLVED_SINGLE
    # a name (fuzzy) lookup never resolved_single either
    name_res = r.resolve(CLINIC, "Alvarez", "name")
    assert name_res.outcome != ResolutionOutcome.RESOLVED_SINGLE


def test_t010_unmatched(seeded, repo):
    r = IdentityResolver(repo)
    result = r.resolve(CLINIC, "5559990000", "phone")
    assert result.outcome == ResolutionOutcome.UNMATCHED
    assert result.match_count == 0


def test_t010_persisted_candidate_set_is_full(seeded, repo):
    r = IdentityResolver(repo)
    result = r.resolve(CLINIC, "5551110001", "phone")   # shared line, 2 parties
    events = [e for e in repo.get_resolution_events(CLINIC) if e["id"] == result.event_id]
    assert len(events) == 1
    persisted = events[0]["candidate_set_json"]
    assert len(persisted) == result.match_count == 2
    # persisted set carries STABLE IDs, never names (no PII in the audit log)
    for row in persisted:
        assert "party_id" in row and "entity_ref" in row
        assert "display_name" not in row


# --------------------------------------------------------------------------- #
#  T011 — disambiguation (open name, never enumerate)
# --------------------------------------------------------------------------- #
def test_t011_open_name_exact_one_resolves(seeded, repo):
    r = IdentityResolver(repo)
    shared = r.resolve(CLINIC, "5551110001", "phone")   # Jane Alvarez + Lan Nguyen
    out = r.disambiguate(shared, "Nguyen", CLINIC)
    assert out.outcome == ResolutionOutcome.RESOLVED_SINGLE
    assert out.confirmed_party_id is not None


def test_t011_zero_or_two_matches_stay_unresolved(seeded, repo):
    r = IdentityResolver(repo)
    shared = r.resolve(CLINIC, "5551110005", "phone")   # Marie + Marie (dup)
    two = r.disambiguate(shared, "Marie", CLINIC)        # matches BOTH
    assert two.outcome == ResolutionOutcome.AMBIGUOUS_MULTI
    assert two.confirmed_party_id is None
    zero = r.disambiguate(shared, "Zangief", CLINIC)     # matches none
    assert zero.confirmed_party_id is None


def test_t011_no_candidate_name_emitted_to_caller(seeded, repo):
    r = IdentityResolver(repo)
    shared = r.resolve(CLINIC, "5551110001", "phone")
    # a multi-candidate result never surfaces a name in the caller-facing payload
    resp = r.auto_id_response(shared)
    assert resp["mode"] == "neutral_prompt"
    assert "Alvarez" not in str(resp) and "Nguyen" not in str(resp)


# --------------------------------------------------------------------------- #
#  T012 — review queue (never auto-merge)
# --------------------------------------------------------------------------- #
def test_t012_duplicate_and_collision_land_pending_rows(seeded, repo):
    rq = ReviewQueue(repo)
    rq.scan_and_propose(CLINIC)
    items = repo.get_review_items(CLINIC, status="pending")
    types = {i["proposal_type"] for i in items}
    assert "probable_duplicate" in types    # Marie/Marie shared line
    assert "collision" in types             # Alvarez/Nguyen shared line
    for i in items:
        assert i["status"] == "pending"
        assert i["evidence_json"] and "shared_phone" in i["evidence_json"]


def test_t012_no_auto_merge_call_path_exists():
    # static/import assertion (AST, not prose): no function/method whose name
    # implies a merge exists anywhere in the module.
    import ast
    tree = ast.parse(inspect.getsource(rq_mod))
    defnames = [n.name for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert not any("merge" in n.lower() for n in defnames), defnames
    assert not hasattr(ReviewQueue, "merge")
    assert not hasattr(ReviewQueue, "auto_merge")
    public = [m for m in dir(ReviewQueue) if not m.startswith("_")]
    assert set(public) == {"propose_grouping", "scan_and_propose"}


def test_t012_probable_duplicate_not_auto_identified(seeded, repo):
    r = IdentityResolver(repo)
    # the duplicate's shared phone still resolves as ambiguous_multi, not a pick
    result = r.resolve(CLINIC, "5551110005", "phone")
    assert result.outcome == ResolutionOutcome.AMBIGUOUS_MULTI
    assert r.auto_id_response(result)["mode"] == "neutral_prompt"


# --------------------------------------------------------------------------- #
#  T013 — auto-ID + soft-confirm gating
# --------------------------------------------------------------------------- #
def test_t013_resolved_single_soft_confirms_by_name(seeded, repo):
    r = IdentityResolver(repo)
    result = r.resolve(CLINIC, "5551110002", "phone")   # Tom Alvarez, single
    resp = r.auto_id_response(result)
    assert resp["mode"] == "soft_confirm_by_name"
    assert resp["display_name"] == "Tom Alvarez"
    assert resp["authorizes_change"] is False


def test_t013_audit_only_records_event_but_returns_neutral(seeded, repo):
    r = IdentityResolver(repo, audit_only=True)
    before = len(repo.get_resolution_events(CLINIC))
    result = r.resolve(CLINIC, "5551110002", "phone")   # would be single-match
    after = len(repo.get_resolution_events(CLINIC))
    assert after == before + 1                          # event recorded
    resp = r.auto_id_response(result)
    assert resp["mode"] == "neutral_prompt"             # but no name spoken
    assert "display_name" not in resp
    assert "Alvarez" not in str(resp)


def test_t013_rejected_soft_confirm_reopens_neutrally(seeded, repo):
    r = IdentityResolver(repo)
    reopen = r.neutral_reopen()
    assert reopen["mode"] == "neutral_prompt"
    assert "display_name" not in reopen
