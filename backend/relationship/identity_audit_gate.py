"""Feature 009+011 — identity audit gate (the 009→011 resolver trust seam).

The 011 resolver's **auto-ID + soft-confirm** tier is *gated* on a real-export
identity audit before it is trusted (spec 011 §"Dirty-data risk (highest)" /
SC-004; contract ``specs/009-vera-envelope-onboarding/contracts/identity-handoff.md``
§4 — the proposed input gate). 009 produces the evidence (the
``IdentityAuditCorpus``: household grouping proposals, shared-line collisions, and
the answer-key-scored precision block). This module is the **consumable gate**: it
reads that corpus for a practice and answers exactly one question —

    "has practice X passed the identity audit?"  → DEFAULT-DENY.

**Default-deny is structural.** A missing corpus, an *unscored* precision block
(real export with no answer key), a precision below threshold, or undisposed
shared-line collisions all yield ``passed=False`` → auto-ID stays **untrusted**.
An untrusted practice runs the resolver in ``audit_only`` mode: every resolution
event is still recorded, but the caller always gets the neutral prompt. The
**soft-confirm / tiered-verification fallback paths are unaffected** — they are
the safe default and keep working whether or not the gate passes (identification
never authorizes a change on its own; that is FR-008/017, enforced in
``verification.py``).

This module **never enables auto-ID on its own.** Passing the gate only *lifts*
the default-deny; a caller must still opt an ``IdentityResolver`` into gated trust
via :func:`build_gated_resolver`. There is no path here that flips auto-ID on by
default anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

# Precision floor for the answer-key-scored collision detection. The corpus
# enumerates precision so a false-positive auto-ID is detectable (handoff §2);
# below this floor the flagging is not trustworthy enough to lift default-deny.
DEFAULT_MIN_PRECISION = 0.90


class _AuditRepo(Protocol):  # duck-typed; OnboardingRepository satisfies it
    def get_identity_audit_corpus(self, practice_id: str) -> Optional[dict]: ...


class _ReviewRepo(Protocol):  # duck-typed; HouseholdRepository satisfies it
    def get_review_items(self, clinic_id: str,
                         status: Optional[str] = None) -> list: ...


@dataclass
class AuditGateDecision:
    """The gate's verdict for one practice. ``passed`` is the single trust bit;
    ``reasons`` and the stat fields make *why* auditable (never silent)."""
    practice_id: str
    passed: bool
    reasons: list[str] = field(default_factory=list)
    # Surfaced corpus stats (all default to the deny-safe zero/None).
    corpus_present: bool = False
    precision: Optional[float] = None
    precision_scored: bool = False
    min_precision: float = DEFAULT_MIN_PRECISION
    collision_count: int = 0
    duplicate_count: int = 0
    false_positive_count: int = 0
    # Review-queue disposition (only populated when a review repo was supplied).
    disposition_evaluated: bool = False
    pending_review_count: int = 0
    resolved_review_count: int = 0

    @property
    def trust_auto_id(self) -> bool:
        return self.passed


class IdentityAuditGate:
    """Reads the 009 ``IdentityAuditCorpus`` (and, when supplied, the 011
    review-queue disposition) and decides whether a practice's auto-ID tier may
    be trusted. Default-deny: anything short of the full bar denies."""

    def __init__(self, audit_repo: _AuditRepo, *,
                 review_repo: Optional[_ReviewRepo] = None,
                 min_precision: float = DEFAULT_MIN_PRECISION,
                 require_disposition: bool = True):
        self.audit_repo = audit_repo
        # Optional: when present, undisposed (pending) shared-line collisions
        # block trust. Absent → disposition is not evaluated and cannot lift the
        # bar on its own (precision still gates).
        self.review_repo = review_repo
        self.min_precision = min_precision
        self.require_disposition = require_disposition

    # ------------------------------------------------------------------ #
    #  evaluate — the full default-deny decision
    # ------------------------------------------------------------------ #
    def evaluate(self, practice_id: str, *,
                 clinic_id: Optional[str] = None) -> AuditGateDecision:
        dec = AuditGateDecision(practice_id=practice_id, passed=False,
                                min_precision=self.min_precision)

        corpus = self.audit_repo.get_identity_audit_corpus(practice_id)
        if corpus is None:
            dec.reasons.append("no_corpus")
            return dec                      # default-deny: nothing to trust
        dec.corpus_present = True

        scored = _scored(corpus)
        dec.collision_count = int(scored.get("collision_count", 0) or 0)
        dec.duplicate_count = int(scored.get("duplicate_count", 0) or 0)
        dec.false_positive_count = len(scored.get("false_positives", []) or [])

        # (1) precision must be answer-key-scored AND at/above the floor.
        if "precision" not in scored or scored.get("precision") is None:
            dec.reasons.append("precision_unscored")   # real export w/o answer key
        else:
            dec.precision_scored = True
            dec.precision = float(scored["precision"])
            if dec.precision < self.min_precision:
                dec.reasons.append("precision_below_threshold")
            if dec.false_positive_count > 0:
                # a single-match number wrongly flagged is a detectable defect
                dec.reasons.append("false_positives_present")

        # (2) disposition: undisposed shared-line collisions block trust. With no
        # review reader wired, disposition is simply not evaluated (precision
        # alone gates); ``disposition_evaluated`` stays False so a caller cannot
        # mistake silence for a clean review.
        if self.review_repo is not None:
            self._eval_disposition(dec, corpus, clinic_id)

        dec.passed = not dec.reasons
        return dec

    def _eval_disposition(self, dec: AuditGateDecision, corpus: dict,
                          clinic_id: Optional[str]) -> None:
        cid = clinic_id or corpus.get("clinic_id")
        if not cid:
            dec.reasons.append("disposition_no_clinic")
            return
        items = self.review_repo.get_review_items(cid) or []
        pid = dec.practice_id
        mine = [it for it in items if _item_practice(it) == pid]
        dec.disposition_evaluated = True
        dec.pending_review_count = sum(1 for it in mine
                                       if it.get("status") == "pending")
        dec.resolved_review_count = sum(1 for it in mine
                                        if it.get("status") != "pending")
        if self.require_disposition and dec.pending_review_count > 0:
            dec.reasons.append("collisions_undisposed")

    # ------------------------------------------------------------------ #
    #  passed / trust_auto_id — the one-bit convenience answers
    # ------------------------------------------------------------------ #
    def passed(self, practice_id: str, *, clinic_id: Optional[str] = None) -> bool:
        return self.evaluate(practice_id, clinic_id=clinic_id).passed

    # alias — reads naturally at the resolver call site
    trust_auto_id = passed


def _scored(corpus: Any) -> dict:
    """Read ``answer_key_scored_precision`` off a corpus row (dict) or model."""
    if isinstance(corpus, dict):
        return corpus.get("answer_key_scored_precision") or {}
    return getattr(corpus, "answer_key_scored_precision", None) or {}


def _item_practice(item: dict) -> Optional[str]:
    """Recover the per-practice attribution 009 carries inside a clinic-scoped
    review row (handoff §3 / F6): ``evidence_json.practice_id`` (fallback: the
    first ``subject_refs_json`` entry). ``None`` when unattributed."""
    ev = item.get("evidence_json") or {}
    if isinstance(ev, dict) and ev.get("practice_id"):
        return ev["practice_id"]
    subs = item.get("subject_refs_json") or []
    if subs and isinstance(subs[0], dict):
        return subs[0].get("practice_id")
    return None


# ---------------------------------------------------------------------------- #
#  Resolver wiring — opt an IdentityResolver into GATED auto-ID trust.
# ---------------------------------------------------------------------------- #
def build_gated_resolver(repo, gate: IdentityAuditGate, practice_id: str, *,
                         clinic_id: Optional[str] = None, **resolver_kwargs):
    """Construct an :class:`IdentityResolver` whose auto-ID trust is DERIVED from
    the identity audit gate.

    ``audit_only`` is set to ``not gate.passed(...)`` — so a practice that has NOT
    cleared the audit (no corpus / below-threshold / undisposed collisions) gets a
    resolver that records events but always returns the neutral prompt. This is the
    only supported way to lift the resolver's default-deny, and it never enables
    auto-ID by default: an unknown practice denies.
    """
    from backend.relationship.identity_resolver import IdentityResolver

    trusted = gate.passed(practice_id, clinic_id=clinic_id)
    return IdentityResolver(repo, audit_only=not trusted, **resolver_kwargs)
