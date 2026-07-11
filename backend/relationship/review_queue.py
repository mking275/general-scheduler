"""Feature 011 — T012 review queue (contract R3). NEVER auto-merge.

Probable duplicates, shared-line collisions, and merge candidates are written to
``household_review_queue`` with ``status="pending"`` and evidence. Staff
approve/reject/defer; automatic identification proceeds only on unambiguous
single matches (FR-004).

**There is deliberately no merge / auto_merge function in this module.** The
only write path is ``propose_grouping``, which creates a *pending* proposal —
it never mutates or combines household/contact records. (A static assertion in
``test_phase_b.py`` enforces the absence of any merge call path.)
"""
from __future__ import annotations

from typing import Literal

from backend.models import HouseholdReviewQueue

ProposalType = Literal["probable_duplicate", "collision", "merge_candidate"]


class ReviewQueue:
    def __init__(self, repo):
        self.repo = repo

    # ------------------------------------------------------------------ #
    #  R3 — propose_grouping (the ONLY write path; always pending)
    # ------------------------------------------------------------------ #
    def propose_grouping(self, clinic_id: str, evidence: dict,
                         proposal_type: ProposalType,
                         subject_refs: list | None = None) -> str:
        item = HouseholdReviewQueue(
            clinic_id=clinic_id, proposal_type=proposal_type,
            subject_refs_json=subject_refs or evidence.get("party_ids", []),
            evidence_json=evidence, status="pending",
        )
        self.repo.create_review_item(item)
        return item.id

    # ------------------------------------------------------------------ #
    #  Detection: scan identifiers, propose (never act) on dupes/collisions
    # ------------------------------------------------------------------ #
    def scan_and_propose(self, clinic_id: str) -> list[str]:
        """Group contacts by shared normalized phone. A shared phone whose
        parties look like the SAME person (same normalized name) -> a
        ``probable_duplicate`` proposal; otherwise a ``collision``. Returns the
        created review-item ids. Proposes only — merges nothing."""
        phones = self.repo.list_identifiers(clinic_id, "phone")
        by_value: dict[str, list[str]] = {}
        for row in phones:
            by_value.setdefault(row["value_normalized"], []).append(row["party_id"])

        created: list[str] = []
        for value, party_ids in by_value.items():
            uniq = list(dict.fromkeys(party_ids))
            if len(uniq) < 2:
                continue
            contacts = {pid: self.repo.get_contact(pid) for pid in uniq}
            names = {(_norm_name(c["display_name"]) if c else "") for c in contacts.values()}
            same_person = len(names) == 1 and "" not in names
            proposal_type: ProposalType = "probable_duplicate" if same_person else "collision"
            evidence = {
                "shared_phone": value,
                "party_ids": uniq,
                "entity_refs": [contacts[p]["entity_ref"] for p in uniq if contacts[p]],
                "reason": ("same normalized name on a shared line"
                           if same_person else "distinct names on a shared line"),
            }
            created.append(self.propose_grouping(clinic_id, evidence, proposal_type, uniq))
        return created


def _norm_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum() or ch.isspace()).strip()
