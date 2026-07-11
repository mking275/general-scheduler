"""Feature 011 — T028 real ``HouseholdSummary`` provider (backs the 010
contract-A4 stub in ``backend/voice/prefetch.py``).

The 010 prefetch path consumes a VP-4a household summary through the frozen A4
field shape (``party_id``, ``display_name_for_greeting``, ``household_patients``,
``last_visit_summary_line``, ``audience_scope``, ``verification_level``). Until
4a landed, the provider was absent and the stub returned ``None`` (Vera then ran
unverified, no greeting-name leak). This module supplies the **real** provider:
an audience-scoped projection built from the household read path + the
``ScopedRecall`` rail — the field contract is unchanged, the values are now
populated per audience / tier.

Privacy invariants preserved:
  * ``display_name_for_greeting`` is populated ONLY for a soft-confirmed /
    resolved caller (``verification_level`` in {``soft_confirmed``, ``strong``}).
    An unverified caller gets ``None`` — no greeting-name leak.
  * ``last_visit_summary_line`` comes through ``ScopedRecall`` with
    ``entity_scope=[household_id, clinic_id]`` — BOTH the household AND clinic
    refs (``own_clinic_only`` is checked before ``own_household_only``; a missing
    clinic ref denies everything). Another household's detail is never returned.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Optional


def _run(coro):
    """Drive an async ScopedRecall call from the sync prefetch path (sim)."""
    return asyncio.run(coro)


def build_household_provider(
    repo,
    scoped_recall,
    clinic_id: str,
    *,
    audience: str,
    verification_level: str = "none",
    summary_kind: str = "last_visit",
) -> Callable[[str], Optional[object]]:
    """Return a ``HouseholdProvider`` (``Callable[[str], Optional[HouseholdSummary]]``)
    the 010 ``Prefetcher`` plugs in unchanged.

    ``audience`` is the recall audience used for the scoped ``last_visit`` line;
    ``verification_level`` gates the greeting name. The returned callable is sync
    (the prefetch seam is sync); it drives ``ScopedRecall`` internally.
    """
    # Imported here (not at module top) so backend.relationship carries no
    # import-time dependency on backend.voice — the seam stays one-way.
    from backend.voice.prefetch import HouseholdSummary, PatientRef

    def provider(party_id: str) -> Optional[object]:
        contact = repo.get_contact(party_id)
        if not contact:
            return None
        household_id = contact["household_id"]
        proj = repo.household_projection(household_id)

        patients = [
            PatientRef(name=p.get("name"), species=p.get("species"))
            for p in proj.get("patients", [])
            if p.get("status") == "active"          # deceased/rehomed never greeted
        ]

        # Greeting name only for a soft-confirmed / resolved caller (A4:
        # "soft-confirm/greeting only"). Unverified -> None (no name leak).
        greeting = (contact.get("display_name")
                    if verification_level in ("soft_confirmed", "strong") else None)

        # Scoped last-visit line: entity_scope carries BOTH refs (household +
        # clinic). ScopedRecall applies the T018 default-deny filter and writes
        # the T019 audit; a foreign-household fact is withheld (never returned).
        entity_scope = [household_id, clinic_id]
        facts = _run(scoped_recall.recall_by_kind(
            summary_kind, audience=audience, entity_scope=entity_scope))
        last_line = facts[0].content if facts else None

        return HouseholdSummary(
            party_id=party_id,
            display_name_for_greeting=greeting,
            household_patients=patients,
            last_visit_summary_line=last_line,
            audience_scope=audience,
            verification_level=verification_level,
        )

    return provider
