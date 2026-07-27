"""Feature 011 — T019 append-only reveal-decision audit (FR-016).

Writes a ``reveal_decision_log`` row on **every** scoping decision — revealed
AND withheld — the staff-visible audit spine. The reason vocabulary is closed:
``explicit_allow | default_deny_no_rule | wrong_household | unmapped_kind |
unrecognized_predicate`` (the last added by the C6 §4b fail-closed hardening;
coordinate the string with core's rail vocabulary at cutover).
"""
from __future__ import annotations

from typing import Optional

from backend.models import RevealDecision, RevealDecisionLog
from backend.relationship.scoping_policy import ScopeDecision


class RevealLog:
    def __init__(self, repo, clinic_id: str, interaction_ref: str = ""):
        self.repo = repo
        self.clinic_id = clinic_id
        self.interaction_ref = interaction_ref

    def record(self, *, audience: str, fact_kind: str, decision: ScopeDecision,
               entity_ref: Optional[str] = None,
               interaction_ref: Optional[str] = None) -> dict:
        row = RevealDecisionLog(
            clinic_id=self.clinic_id,
            interaction_ref=interaction_ref if interaction_ref is not None else self.interaction_ref,
            audience=audience, fact_kind=fact_kind, fact_class=decision.fact_class,
            entity_ref=entity_ref,
            decision=RevealDecision.REVEALED if decision.allowed else RevealDecision.WITHHELD,
            rule_matched=decision.rule_matched, reason=decision.reason,
        )
        return self.repo.append_reveal_decision(row)
