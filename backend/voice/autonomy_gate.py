"""Feature 010 — Vera Voice: T027 autonomy gate (contract B3 / C4).

A **synchronous** gate that authorizes every write and every escalation on a
live voice turn. On a synchronous live call there is no mid-call human-approval
loop, so the C4 autonomy ladder **collapses**: the live gate is restricted to
**``do`` | ``reject`` | ``escalate``** (act now / deny / hand to a human).

The ``advise`` and ``propose`` classes never speak or act on-call — they are
deferred to **post-call artifacts**:
  * ``advise``  -> a morning-briefing item
  * ``propose`` -> a draft for staff/vet review (e.g. the refill draft)

Two hard guards, enforced below the model:
  * **No auto-approval on voice.** Any ``auto_approved`` disposition is rejected.
  * **``do`` is never enabled for clinical/assessment verbs.** A clinical verb
    asking to *act* is blocked (it can only ever become a draft/escalation).

The four-value ``gate_decision`` is still *persisted* (audit of intent) while
only three act live — hence ``classify_full`` returns the persisted decision +
the live action + the post-call artifact, and ``classify`` returns the
live-restricted decision the ``turn_loop`` consumes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional

from backend.models import GateDecision

# Verbs that make (or assert) a clinical/assessment decision. ``do`` is NEVER
# enabled for these on voice — they can only defer to a draft or escalate.
# NB: capturing a refill *request* as a draft (``refill_draft``) is NOT clinical;
# *approving* a refill / prescribing / dosing / assessing IS.
CLINICAL_VERBS = frozenset({
    "refill", "approve_refill", "prescribe", "dose", "dosage",
    "diagnose", "assess", "triage_assessment", "medical_advice",
})

# The dispositions that must never act autonomously on the voice channel.
_AUTO_APPROVE_DISPOSITIONS = frozenset({"auto_approved", "auto-approve", "auto_approve"})

LiveAction = Literal["do", "reject", "escalate", "none"]
PostCallArtifact = Literal["briefing_item", "draft"]


class AutoApprovalRejected(RuntimeError):
    """Raised when an ``auto_approved`` disposition is attempted on voice."""


@dataclass
class GateContext:
    verb: str
    ladder: str = "know"                 # know | advise | propose | do (C4 ladder)
    disposition: Optional[str] = None    # e.g. an upstream "auto_approved"
    is_write: bool = False
    audience_scope: str = "caller_unverified"


@dataclass
class GateResult:
    persisted_decision: GateDecision     # 4-value + escalate — audited intent
    live_action: LiveAction              # what actually happens on-call
    post_call_artifact: Optional[PostCallArtifact] = None
    reason: str = ""


class AutonomyGate:
    def __init__(self, clinical_verbs=CLINICAL_VERBS):
        self.clinical_verbs = set(clinical_verbs)

    # --- full C4 classification (persisted intent + live collapse) ------
    def classify_full(self, ctx: GateContext) -> GateResult:
        # Hard guard 1: no auto-approval ever acts on voice.
        if (ctx.disposition or "").lower() in _AUTO_APPROVE_DISPOSITIONS:
            return GateResult(GateDecision.REJECT, "reject", None,
                              reason="auto_approved disposition rejected on voice")

        ladder = (ctx.ladder or "know").lower()

        if ladder == "know":                 # read-only — no gate write, narrates
            return GateResult(GateDecision.DO, "do", None, reason="read-only")

        if ladder == "advise":               # deferred to morning briefing
            return GateResult(GateDecision.ADVISE, "none", "briefing_item",
                              reason="advise -> post-call briefing item")

        if ladder == "propose":              # deferred to a draft for review
            return GateResult(GateDecision.PROPOSE, "none", "draft",
                              reason="propose -> post-call draft")

        if ladder == "escalate":
            return GateResult(GateDecision.ESCALATE, "escalate", None,
                              reason="hand to a human")

        if ladder == "do":
            # Hard guard 2: do-class is NEVER enabled for clinical verbs.
            if ctx.verb in self.clinical_verbs:
                return GateResult(GateDecision.REJECT, "reject", None,
                                  reason=f"do-class blocked for clinical verb '{ctx.verb}'")
            return GateResult(GateDecision.DO, "do", None, reason="authorized write")

        # Unknown ladder value -> deny, never silently act.
        return GateResult(GateDecision.REJECT, "reject", None,
                          reason=f"unknown ladder '{ladder}'")

    # --- live-restricted classification for the turn loop ---------------
    def classify(self, pending_tool_calls: list) -> GateDecision:
        """The live voice gate: returns ONLY ``do`` | ``reject`` | ``escalate``.

        Consumed by ``turn_loop.ProtocolAwareHooks``. A tool call dict may carry
        ``name`` / ``ladder`` / ``disposition`` / ``clinical`` keys.
        """
        if not pending_tool_calls:
            return GateDecision.DO           # pure narration, no write

        for tc in pending_tool_calls:
            verb = tc.get("name", "")
            disposition = tc.get("disposition")
            clinical = tc.get("clinical", verb in self.clinical_verbs)

            if (disposition or "").lower() in _AUTO_APPROVE_DISPOSITIONS:
                return GateDecision.REJECT   # no auto-approval on voice

            ladder = (tc.get("ladder") or ("do" if tc.get("is_write", True) else "know")).lower()

            if verb in ("escalate", "warm_transfer") or ladder == "escalate":
                return GateDecision.ESCALATE

            if ladder == "do" and clinical:
                return GateDecision.REJECT   # do-class never for clinical verbs

        return GateDecision.DO

    def as_gate_classify(self) -> Callable[[list], GateDecision]:
        """The callable wired into ``turn_loop.ProtocolAwareHooks(gate_classify=…)``."""
        return self.classify

    # --- convenience for the refill/clinical draft path -----------------
    def guard_no_auto_approve(self, disposition: Optional[str]) -> None:
        """Raise if a clinical write carries an auto-approve disposition (T028)."""
        if (disposition or "").lower() in _AUTO_APPROVE_DISPOSITIONS:
            raise AutoApprovalRejected(
                "auto_approved disposition is not permitted on the voice channel")
