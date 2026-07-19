"""Feature 009 — T028 identity bootstrap + T029 identity audit corpus.

Seeds ``entity_ref``/``source_id`` lineage (already stamped on every canonical
record by the normalizer via ``backend/relationship/entity_ref.py``) and runs the
initial household/party-resolution **proposals** over the real export.
Collisions / probable-duplicates (shared phones, ex-spouses, duplicate owners)
route to ``backend/relationship/review_queue.py`` (``propose_grouping``,
``status="pending"``) **reused verbatim** — **never auto-merged** (FR-019/021).

**No auto-merge exists** in this module: the only identity write path is
``ReviewQueue.propose_grouping`` (which creates a *pending* proposal and mutates
nothing). During onboarding the queue surfaces to **owner/manager only** — it
creates no staff-facing queue.

``HouseholdReviewQueue`` is **clinic-scoped by column** (no `practice_id`); this
module does **not** fork the reused model — it carries `practice_id` inside
``evidence_json`` and each ``subject_refs`` entry so per-practice attribution +
reconciliation drill-down work without a schema change (data-model.md, Reused-
artifact seams).

**T029 — IdentityAuditCorpus** (the 009-defined 011 seam): the real-export
identity audit corpus — proposals + collisions + answer-key-scored precision
(single-match vs multi-match) — built on 011's concrete shared artifacts
(``entity_ref`` keying + the ``HouseholdReviewQueue`` candidate-set), **defined**
as the proposed input gate for 011's gated resolver to adopt (finding F5). This
spec implements **no** runtime auto-ID / soft-confirm / verification bar (011).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.models import IdentityAuditCorpus
from backend.relationship import entity_ref as eref


def _norm_name(first: Any, last: Any) -> str:
    s = f"{first or ''} {last or ''}".lower()
    return "".join(ch for ch in s if ch.isalnum() or ch.isspace()).strip()


@dataclass
class BootstrapResult:
    practice_id: str
    proposals: list[dict] = field(default_factory=list)     # household groupings w/ lineage
    collisions: list[dict] = field(default_factory=list)    # shared-line dup/collision sets
    review_item_ids: list[str] = field(default_factory=list)
    flagged_phones: list[str] = field(default_factory=list)


class IdentityBootstrap:
    def __init__(self, repo, review_queue):
        self.repo = repo
        self.review = review_queue          # relationship/review_queue.ReviewQueue

    # ------------------------------------------------------------------ #
    #  bootstrap — proposals + collisions (never a merge)
    # ------------------------------------------------------------------ #
    def bootstrap(self, clinic_id: str, practice_id: str) -> BootstrapResult:
        clients = self.repo.list_canonical_records(practice_id, category="client")
        result = BootstrapResult(practice_id=practice_id)

        # 1) household grouping proposals — one synthesized household:vah_* per
        #    client, deterministic from the source id (no name in the key).
        by_phone: dict[str, list[dict]] = {}
        for c in clients:
            payload = c["payload"]
            source_id = str(payload.get("source_id", c["source_id"]))
            household_ref = eref.synth_household_ref(f"{practice_id}:{source_id}")
            result.proposals.append({
                "practice_id": practice_id,
                "entity_ref": c["entity_ref"],
                "household_ref": household_ref,
                "source_id": source_id,
            })
            phone = str(payload.get("phone") or "").strip()
            if phone:
                by_phone.setdefault(phone, []).append(c)

        # 2) collisions / probable-duplicates on shared lines -> pending review.
        for phone, group in by_phone.items():
            refs = [g["entity_ref"] for g in group]
            if len(refs) < 2:
                continue
            names = {_norm_name(g["payload"].get("first_name"),
                                 g["payload"].get("last_name")) for g in group}
            same_person = len(names) == 1 and "" not in names
            proposal_type = "probable_duplicate" if same_person else "collision"
            evidence = {
                "practice_id": practice_id,          # per-practice attribution (F6)
                "shared_phone": phone,
                "entity_refs": refs,
                "reason": ("same normalized name on a shared line"
                           if same_person else "distinct names on a shared line"),
            }
            subject_refs = [{"practice_id": practice_id, "entity_ref": r} for r in refs]
            rid = self.review.propose_grouping(clinic_id, evidence, proposal_type, subject_refs)
            result.review_item_ids.append(rid)
            result.flagged_phones.append(phone)
            result.collisions.append({
                "practice_id": practice_id, "shared_phone": phone,
                "entity_refs": refs, "proposal_type": proposal_type,
                "review_item_id": rid,
            })
        return result

    # ------------------------------------------------------------------ #
    #  T029 — the identity audit corpus (append-only), answer-key-scored
    # ------------------------------------------------------------------ #
    def build_corpus(self, clinic_id: str, practice_id: str,
                     result: BootstrapResult,
                     answer_key: Optional[Any] = None) -> IdentityAuditCorpus:
        precision = self._score(result, answer_key)
        corpus = IdentityAuditCorpus(
            clinic_id=clinic_id, practice_id=practice_id,
            proposals=result.proposals, collisions=result.collisions,
            answer_key_scored_precision=precision,
        )
        self.repo.append_identity_audit_corpus(corpus)
        return corpus

    @staticmethod
    def _score(result: BootstrapResult, answer_key: Optional[Any]) -> dict:
        flagged = set(result.flagged_phones)
        scored: dict[str, Any] = {
            "flagged_phone_count": len(flagged),
            "proposal_count": len(result.proposals),
            "collision_count": sum(1 for c in result.collisions
                                   if c["proposal_type"] == "collision"),
            "duplicate_count": sum(1 for c in result.collisions
                                   if c["proposal_type"] == "probable_duplicate"),
        }
        if answer_key is None:
            return scored
        multi = set(getattr(answer_key, "multi_match_phones", []))
        single = set(getattr(answer_key, "single_match_phones", []))
        true_positives = sorted(flagged & multi)      # genuinely multi-match
        false_positives = sorted(flagged & single)    # single-match wrongly flagged
        scored.update({
            "single_match_phones": sorted(single),
            "multi_match_phones": sorted(multi),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "precision": round(len(true_positives) / max(len(flagged), 1), 4),
        })
        return scored
