"""Feature 010 — Vera Voice: T015 turn loop (contract B3).

Every turn, before Vera's reply is spoken:
  1. ``triage_protocol.step(transcript_delta)``  — deterministic; OVERRIDES model
  2. ``autonomy_gate.classify(pending_tool_calls)`` — live gate: do|reject|escalate
  3. ``pre_speak`` hook (T007 shim) — the single choke point where 1+2 interpose
  4. speak

The protocol engine (T020) and autonomy gate (T027) are wave-2; the loop takes
them as injectable callables with safe pass-through defaults so the wiring —
and the guarantee that **every turn passes through ``pre_speak`` before render**
— is testable now. Barge-in signalling is wired through ``on_barge_in``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from backend.models import GateDecision
from backend.voice.shims.l2_bridge_shim import (
    ModelOutput, SpokenTurn, TurnContext, TurnDecision, TurnHooks, converse_turn,
)

# Callable stub signatures (replaced by real engines in wave 2).
ProtocolStep = Callable[[str], Optional[dict]]      # transcript_delta -> {"urgency","state"} | None
GateClassify = Callable[[list], GateDecision]       # pending_tool_calls -> decision


def _default_protocol_step(_delta: str) -> Optional[dict]:
    return None                                     # no flag until T020 engine


def _default_gate_classify(_tools: list) -> GateDecision:
    return GateDecision.DO                          # authorize until T027 gate


@dataclass
class TurnLoopStats:
    turns: int = 0
    pre_speak_invocations: int = 0
    overrides: int = 0
    escalations: int = 0
    barge_ins: list[int] = field(default_factory=list)


class ProtocolAwareHooks(TurnHooks):
    """The T007 ``TurnHooks`` with protocol-override + autonomy-gate interposed
    in ``pre_speak`` — where the deterministic safety layer beats the model."""

    def __init__(self, protocol_step: Optional[ProtocolStep] = None,
                 gate_classify: Optional[GateClassify] = None,
                 stats: Optional[TurnLoopStats] = None):
        self.protocol_step = protocol_step or _default_protocol_step
        self.gate_classify = gate_classify or _default_gate_classify
        self.stats = stats or TurnLoopStats()

    async def pre_speak(self, draft: ModelOutput, ctx: TurnContext) -> TurnDecision:
        self.stats.pre_speak_invocations += 1

        # 1. Deterministic protocol OVERRIDES the model on any flagged urgency.
        flag = self.protocol_step(ctx.transcript_delta)
        if flag and flag.get("urgency") in ("emergency", "urgent"):
            self.stats.overrides += 1
            self.stats.escalations += 1
            return TurnDecision(action="escalate",
                                override_reason=f"protocol:{flag.get('urgency')}")

        # 2. Autonomy gate authorizes writes / escalations (live: do|reject|escalate).
        decision = self.gate_classify(draft.tool_calls)
        if decision == GateDecision.REJECT:
            self.stats.overrides += 1
            return TurnDecision(action="replace",
                                text="I can't do that on this call, but I'll note it for the team.",
                                override_reason="gate_reject")
        if decision == GateDecision.ESCALATE:
            self.stats.overrides += 1
            self.stats.escalations += 1
            return TurnDecision(action="escalate", override_reason="gate_escalate")

        # 3. Otherwise the model narrates.
        return TurnDecision(action="speak", text=draft.text)

    async def on_barge_in(self, at_ms: int) -> None:
        self.stats.barge_ins.append(at_ms)


async def run_turn(session: dict, draft: ModelOutput, ctx: TurnContext,
                   hooks: ProtocolAwareHooks) -> SpokenTurn:
    """Run a single turn through the T007 pre-speak interposition."""
    result = await converse_turn(session, draft, ctx, hooks=hooks)
    hooks.stats.turns += 1
    return result
