"""Feature 009 — T042 identity-handoff shape + no-auto-merge harness (SC-008).

Assert the audit corpus matches the frozen ``identity-handoff.md`` (011-consumed)
shape; every collision/duplicate lands a ``pending`` ``household_review_queue``
row; **0** auto-merges (static assertion: no merge call path, reusing the 011
guard).
"""
import ast
import uuid

from backend.envelope.identity_bootstrap import IdentityBootstrap
from backend.relationship.household_repository import HouseholdRepository
from backend.relationship.review_queue import ReviewQueue
from backend.tests.envelope import _pipeline as P

CLINIC = "goldsmith"


def _review_queue(db_url):
    hr = HouseholdRepository(db_url)
    hr.init_db()
    return ReviewQueue(hr), hr


def _bootstrap(repo, db_url, seed=81):
    pid = f"p-hand-{uuid.uuid4().hex[:6]}"
    exp, *_ = P.normalize_once(repo, pid, clinic=CLINIC, seed=seed)
    rq, hr = _review_queue(db_url)
    boot = IdentityBootstrap(repo, rq)
    res = boot.bootstrap(CLINIC, pid)
    corpus = boot.build_corpus(CLINIC, pid, res, answer_key=exp.answer_key)
    return pid, res, corpus, hr


# --------------------------------------------------------------------------- #
#  §2 — IdentityAuditCorpus conforms to the frozen handoff shape
# --------------------------------------------------------------------------- #
def test_corpus_conforms_to_frozen_shape(repo, db_url):
    pid, res, corpus, _hr = _bootstrap(repo, db_url)

    # proposals: [{practice_id, entity_ref, household_ref, source_id}] w/ lineage
    assert corpus.proposals
    for p in corpus.proposals:
        assert set(p) >= {"practice_id", "entity_ref", "household_ref", "source_id"}
        assert p["practice_id"] == pid
        assert p["entity_ref"].startswith("client:ezyvet_c")
        assert p["household_ref"].startswith("household:vah_")

    # collisions: [{practice_id, shared_phone, entity_refs, proposal_type, review_item_id}]
    for c in corpus.collisions:
        assert set(c) >= {"practice_id", "shared_phone", "entity_refs",
                          "proposal_type", "review_item_id"}
        assert c["proposal_type"] in ("probable_duplicate", "collision")

    # answer_key_scored_precision: the build-time scoring block (§2 of the contract)
    scored = corpus.answer_key_scored_precision
    for key in ("flagged_phone_count", "proposal_count", "collision_count",
                "duplicate_count", "single_match_phones", "multi_match_phones",
                "true_positives", "false_positives", "precision"):
        assert key in scored, f"missing scored field {key}"


# --------------------------------------------------------------------------- #
#  §3 — every collision/duplicate -> a pending review row (practice_id carried)
# --------------------------------------------------------------------------- #
def test_every_collision_lands_pending_review_row(repo, db_url):
    pid, res, corpus, hr = _bootstrap(repo, db_url)
    assert res.review_item_ids

    pending = hr.get_review_items(CLINIC, status="pending")
    landed = {row["id"] for row in pending}
    assert set(res.review_item_ids).issubset(landed)

    mine = [row for row in pending if row["id"] in res.review_item_ids]
    for row in mine:
        assert row["status"] == "pending"
        assert row["proposal_type"] in ("probable_duplicate", "collision")
        # practice_id carried in evidence + each subject ref (F6 — no schema fork).
        assert row["evidence_json"].get("practice_id") == pid
        assert all(s.get("practice_id") == pid for s in row["subject_refs_json"])


# --------------------------------------------------------------------------- #
#  §4 — zero auto-merge (static assertion; reuses the 011 guard)
# --------------------------------------------------------------------------- #
def test_zero_auto_merge_call_path():
    import backend.envelope.identity_bootstrap as ib
    import backend.relationship.review_queue as rq
    for mod in (ib, rq):
        tree = ast.parse(open(mod.__file__).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert "merge" not in node.name.lower(), f"{mod.__file__}:{node.name}"
    # the only queue write path is propose_grouping; no merge method exists.
    assert hasattr(rq.ReviewQueue, "propose_grouping")
    assert not hasattr(rq.ReviewQueue, "merge")


def test_precision_no_false_positive_auto_id(repo, db_url):
    """Scored against the answer key: 0 single-match false positives (a false
    auto-ID is detectable), precision 1.0."""
    _pid, _res, corpus, _hr = _bootstrap(repo, db_url, seed=82)
    scored = corpus.answer_key_scored_precision
    assert scored["false_positives"] == []
    assert scored["precision"] == 1.0
