"""Feature 011 — T018 scoping policy evaluator (contract C / H1).

Loads the **three-field** ``memory_scoping`` policy (``allow_classes`` +
``scope_predicates`` + ``kind_to_class``) and evaluates a recall ``fact_kind``
for an audience with **structural default-deny**:

1. Resolve ``fact_kind -> fact_class`` via ``kind_to_class`` — an **unmapped
   kind is DENIED** (``reason=unmapped_kind``), never revealed by omission.
2. The resolved class must be in ``allow_classes[audience]`` (audience absent,
   or class not listed → ``default_deny_no_rule``).
3. Every ``scope_predicate`` for the audience is applied as a row filter:
   ``own_household_only`` → ``wrong_household`` on a foreign-household row;
   ``own_clinic_only`` → cross-clinic withhold.

Default-deny is structural in BOTH directions: a class not listed, an audience
absent, and an unmapped kind all deny. Nothing is revealed by omission.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml

# The ONLY fact classes the evaluator recognises (closed vocabulary).
CLOSED_CLASSES = frozenset({
    "schedule", "client_summary", "patient_clinical",
    "financial", "contact_info", "staff_notes",
})

Reason = str  # explicit_allow | default_deny_no_rule | wrong_household | unmapped_kind


@dataclass
class ScopeDecision:
    decision: str                       # "revealed" | "withheld"
    reason: Reason
    fact_class: Optional[str] = None     # None when kind is unmapped
    rule_matched: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.decision == "revealed"


class ScopingPolicy:
    def __init__(self, allow_classes: dict, scope_predicates: dict,
                 kind_to_class: dict):
        self.allow_classes = allow_classes or {}
        self.scope_predicates = scope_predicates or {}
        self.kind_to_class = kind_to_class or {}

    # ------------------------------------------------------------------ #
    #  Loaders
    # ------------------------------------------------------------------ #
    @classmethod
    def from_yaml(cls, text: str) -> "ScopingPolicy":
        data = yaml.safe_load(text) or {}
        return cls(
            allow_classes=data.get("allow_classes", {}),
            scope_predicates=data.get("scope_predicates", {}),
            kind_to_class=data.get("kind_to_class", {}),
        )

    @classmethod
    def load(cls, path: Optional[str] = None) -> "ScopingPolicy":
        path = path or _default_policy_path()
        with open(path) as f:
            return cls.from_yaml(f.read())

    # ------------------------------------------------------------------ #
    #  T018 — evaluate (default-deny, fail-closed)
    # ------------------------------------------------------------------ #
    def evaluate(self, fact_kind: str, audience: str, *,
                 subject_household: Optional[str] = None,
                 subject_clinic: Optional[str] = None,
                 entity_scope: Optional[list[str]] = None) -> ScopeDecision:
        # (1) kind -> class; unmapped kind is denied (fail-closed).
        fact_class = self.kind_to_class.get(fact_kind)
        if fact_class is None:
            return ScopeDecision("withheld", "unmapped_kind", None)

        # (2) class must be allowed for this audience.
        allowed = self.allow_classes.get(audience)
        if not allowed or fact_class not in allowed:
            return ScopeDecision("withheld", "default_deny_no_rule", fact_class)

        # (3) row-level scope predicates (filters applied AFTER the class allow).
        for pred in self.scope_predicates.get(audience, []):
            if pred == "own_household_only":
                if subject_household is not None and (
                    entity_scope is None or subject_household not in entity_scope
                ):
                    return ScopeDecision("withheld", "wrong_household", fact_class)
            elif pred == "own_clinic_only":
                if subject_clinic is not None and (
                    entity_scope is None or subject_clinic not in entity_scope
                ):
                    # cross-clinic withhold — no rule permits this tenant's row
                    return ScopeDecision("withheld", "default_deny_no_rule", fact_class)

        return ScopeDecision(
            "revealed", "explicit_allow", fact_class,
            rule_matched=f"allow_classes[{audience}]:{fact_class}",
        )


def _default_policy_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(root, "config", "relationship",
                        "memory_scoping.goldsmith.yaml")
