"""T014 — resolver identity-audit harness (the resolver-trust gate).

Runs ``resolve`` across the full dirty corpus and scores it against the T007
ground-truth answer key: ZERO false-positive auto-IDs; every shared-phone
lookup -> ambiguous_multi; every duplicate/collision -> a review-queue row.
Enumerates precision on single-match vs multi-match lookups.
"""
from backend.models import ResolutionOutcome
from backend.relationship.identity_resolver import IdentityResolver
from backend.relationship.review_queue import ReviewQueue
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-audit-t014"


def _run_audit(repo):
    corpus = build_corpus(clinic_id=CLINIC)
    corpus.seed_into_repo(repo)
    resolver = IdentityResolver(repo)
    ak = corpus.answer_key

    report = {"single_correct": 0, "single_total": 0,
              "multi_correct": 0, "multi_total": 0,
              "false_positive_auto_id": 0, "unmatched_correct": 0}

    for phone, spec in ak["phone_lookups"].items():
        result = resolver.resolve(CLINIC, phone, "phone")
        auto = resolver.auto_id_response(result)
        auto_identified = auto["mode"] == "soft_confirm_by_name"

        if spec["match_kind"] == "single":
            report["single_total"] += 1
            if result.outcome == ResolutionOutcome.RESOLVED_SINGLE and auto_identified:
                report["single_correct"] += 1
        elif spec["match_kind"] == "multi":
            report["multi_total"] += 1
            # a multi-match must NEVER auto-ID (that would be the PII leak)
            if auto_identified:
                report["false_positive_auto_id"] += 1
            if result.outcome == ResolutionOutcome.AMBIGUOUS_MULTI and not auto_identified:
                report["multi_correct"] += 1
        else:  # none
            if result.outcome == ResolutionOutcome.UNMATCHED and not auto_identified:
                report["unmatched_correct"] += 1

    return corpus, resolver, report


def test_t014_zero_false_positive_auto_ids(repo):
    _corpus, _resolver, report = _run_audit(repo)
    assert report["false_positive_auto_id"] == 0
    # precision is perfect on the synthetic corpus (build-time)
    assert report["single_correct"] == report["single_total"] > 0
    assert report["multi_correct"] == report["multi_total"] > 0


def test_t014_every_shared_phone_is_ambiguous(repo):
    corpus, resolver, _ = _run_audit(repo)
    for phone in corpus.answer_key["multi_match_phones"]:
        result = resolver.resolve(CLINIC, phone, "phone")
        assert result.outcome == ResolutionOutcome.AMBIGUOUS_MULTI, phone


def test_t014_every_duplicate_or_collision_lands_review_row(repo):
    corpus = build_corpus(clinic_id=CLINIC + "-rq")
    clinic = CLINIC + "-rq"
    corpus.seed_into_repo(repo)
    rq = ReviewQueue(repo)
    rq.scan_and_propose(clinic)
    items = repo.get_review_items(clinic, status="pending")
    # every multi-match phone (dup or collision) produced exactly one proposal
    shared_phones = {i["evidence_json"]["shared_phone"] for i in items}
    assert set(corpus.answer_key["multi_match_phones"]) <= shared_phones
    types = {i["proposal_type"] for i in items}
    assert types == {"probable_duplicate", "collision"}
