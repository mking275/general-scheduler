"""Feature 009 — T028 identity bootstrap + T029 identity audit corpus.

T028 — identity bootstrap emits household/party grouping proposals with full
lineage; every collision/duplicate lands a pending household_review_queue row
with evidence (practice_id carried inside evidence/subject_refs); no auto-merge
code path exists; 0 silent merges.
T029 — the corpus is built on 011's entity_ref keying + candidate-set shape;
scored against the answer key it enumerates single-match vs multi-match precision;
no runtime auto-ID / soft-confirm / verification-bar code exists in this tier.
"""
import uuid

from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.identity_bootstrap import IdentityBootstrap
from backend.envelope.normalizer import Normalizer
from backend.envelope.pims import load_adapters
from backend.envelope.pims.port import resolve_adapter
from backend.relationship.household_repository import HouseholdRepository
from backend.relationship.review_queue import ReviewQueue
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"


def _adapter(pid):
    load_adapters()
    return resolve_adapter("ezyvet", "complete_v1", clinic_id=CLINIC, practice_id=pid,
                           practice_database_id="pdb1", extraction_port=SimExtractionPort())


def _ingest(repo, pid, seed=31):
    exp = generate_practice_export(pid, seed=seed, variant="complete")
    a = _adapter(pid)
    Normalizer(repo).normalize(CLINIC, pid, a, a.profile(exp), exp)
    return exp


def _review_queue(db_url):
    hr = HouseholdRepository(db_url)
    hr.init_db()
    return ReviewQueue(hr), hr


def test_bootstrap_proposals_lineage_and_pending_review_rows(repo, db_url):
    pid = f"p-id-{uuid.uuid4().hex[:6]}"
    _ingest(repo, pid)
    rq, hr = _review_queue(db_url)
    result = IdentityBootstrap(repo, rq).bootstrap(CLINIC, pid)

    # household grouping proposals carry full lineage (entity_ref + household:vah_*)
    assert result.proposals
    assert all(p["entity_ref"].startswith("client:ezyvet_c") for p in result.proposals)
    assert all(p["household_ref"].startswith("household:vah_") for p in result.proposals)

    # every collision/duplicate landed a pending review row with evidence
    assert result.review_item_ids
    pending = hr.get_review_items(CLINIC, status="pending")
    landed = {row["id"] for row in pending}
    assert set(result.review_item_ids).issubset(landed)
    # practice_id is carried inside evidence + subject_refs (F6 — no schema fork)
    mine = [row for row in pending if row["id"] in result.review_item_ids]
    assert all(row["evidence_json"].get("practice_id") == pid for row in mine)
    assert all(all(s.get("practice_id") == pid for s in row["subject_refs_json"])
               for row in mine)
    # proposal types are only propose-types; nothing is merged
    assert all(row["proposal_type"] in ("probable_duplicate", "collision")
               for row in mine)
    assert all(row["status"] == "pending" for row in mine)


def test_no_auto_merge_code_path_exists():
    """Static assertion: neither the bootstrap module nor the reused review queue
    defines a merge / auto-merge function (reusing the 011 guard). AST-based so
    docstring prose about the *absence* of a merge does not trip it."""
    import ast

    import backend.envelope.identity_bootstrap as ib
    import backend.relationship.review_queue as rq
    for mod in (ib, rq):
        tree = ast.parse(open(mod.__file__).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert "merge" not in node.name.lower(), f"{mod.__file__}:{node.name}"
    # the only queue write is propose_grouping; no merge method exists
    assert hasattr(rq.ReviewQueue, "propose_grouping")
    assert not hasattr(rq.ReviewQueue, "merge")


def test_corpus_scored_against_answer_key(repo, db_url):
    pid = f"p-id-corpus-{uuid.uuid4().hex[:6]}"
    exp = _ingest(repo, pid)
    rq, _ = _review_queue(db_url)
    boot = IdentityBootstrap(repo, rq)
    result = boot.bootstrap(CLINIC, pid)
    corpus = boot.build_corpus(CLINIC, pid, result, answer_key=exp.answer_key)

    scored = corpus.answer_key_scored_precision
    # enumerates single-match vs multi-match
    assert "single_match_phones" in scored and "multi_match_phones" in scored
    # we only flag genuinely-shared lines -> no single-match false positive
    assert scored["false_positives"] == []
    assert scored["precision"] == 1.0
    # the planted duplicate + collision are both surfaced
    assert scored["duplicate_count"] >= 1
    assert scored["collision_count"] >= 1
    # persisted + built on 011's entity_ref keying
    assert repo.get_identity_audit_corpus(pid) is not None
    assert all(p["entity_ref"].startswith("client:") for p in corpus.proposals)


def test_no_runtime_autoid_soft_confirm_in_tier():
    """The 009 tier defines the audit corpus but implements no runtime auto-ID /
    soft-confirm / verification-bar (those are 011)."""
    import backend.envelope.identity_bootstrap as ib
    src = open(ib.__file__).read()
    for forbidden in ("soft_confirm", "auto_identify", "verification_bar",
                      "def resolve_runtime"):
        assert forbidden not in src
