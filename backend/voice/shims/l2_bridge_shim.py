"""[SHIM — extract post-pilot] Feature 010 — T007 L2 bridge + pre-speak
interposition shim (contract A3), registry-marked ``prototype``.

``bridge_inbound()`` routes voice into the shared ``converse_turn()``. The
non-negotiable condition (C3 condition 1): ``converse_turn`` exposes a
``TurnHooks.pre_speak`` hook that runs on the model's proposed output **before
it is rendered** and carries **override authority** — it may REPLACE, BLOCK,
ESCALATE, HOLD, or HANGUP. This is where our deterministic protocol machine +
C4 gate interpose (wired in ``turn_loop`` T015).

If core ships L2 without this hook, voice would have to bypass the shared brain
— unacceptable. This shim implements the contract so L3 never blocks on core;
extracted to core C3 post-pilot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal, Optional

# Registry marker — this is the prototype stand-in, not core L2.
REGISTRY_MARK = "prototype"

TurnAction = Literal["speak", "replace", "escalate", "hold", "hangup"]


@dataclass
class ModelOutput:
    """The realtime model's proposed output for a turn."""
    text: str
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class TurnContext:
    session_id: str
    seq: int
    transcript_delta: str = ""
    audience_scope: str = "caller_unverified"
    meta: dict = field(default_factory=dict)


@dataclass
class TurnDecision:
    action: TurnAction = "speak"
    text: Optional[str] = None
    override_reason: Optional[str] = None    # audited when the hook overrides


class TurnHooks:
    """What voice needs L2 to accept. Subclass and override; defaults pass the
    model output through unchanged."""

    async def pre_speak(self, draft: ModelOutput, ctx: TurnContext) -> TurnDecision:
        return TurnDecision(action="speak", text=draft.text)

    async def on_partial(self, partial: str) -> None:  # streaming
        return None

    async def on_barge_in(self, at_ms: int) -> None:    # caller interrupt
        return None


@dataclass
class SpokenTurn:
    """Result of a turn: what actually gets rendered + the audited decision."""
    action: TurnAction
    spoken_text: Optional[str]
    decision: TurnDecision
    model_draft: str


async def converse_turn(
    session: dict,
    draft: ModelOutput,
    ctx: TurnContext,
    hooks: Optional[TurnHooks] = None,
) -> SpokenTurn:
    """Run the model draft through ``pre_speak`` BEFORE it is rendered.

    The hook's decision has override authority:
      - ``speak``   -> render the draft (or the hook's text if supplied)
      - ``replace`` -> render the hook's text INSTEAD of the model draft
      - ``escalate``/``hold``/``hangup`` -> no draft spoken; carried to caller
    """
    hooks = hooks or TurnHooks()
    decision = await hooks.pre_speak(draft, ctx)

    if decision.action == "speak":
        spoken = decision.text if decision.text is not None else draft.text
    elif decision.action == "replace":
        # Model draft is DISCARDED — the hook's text is spoken instead.
        spoken = decision.text
    else:  # escalate | hold | hangup — model output does not reach the caller
        spoken = decision.text
    return SpokenTurn(action=decision.action, spoken_text=spoken,
                      decision=decision, model_draft=draft.text)


async def bridge_inbound(
    channel: str,
    raw: Any,
    hooks: Optional[TurnHooks] = None,
    resolve_binding_fn: Optional[Callable[..., Any]] = None,
) -> dict:
    """Resolve the channel binding (A1) and open a session. Returns a minimal
    session dict the turn loop drives; the real L2 returns a richer object."""
    if resolve_binding_fn is None:
        from backend.voice.shims.channel_binding_shim import resolve_binding as resolve_binding_fn
    address = raw.get("from") if isinstance(raw, dict) else str(raw)
    binding = resolve_binding_fn(address, channel)
    return {
        "binding": binding,
        "channel": channel,
        "hooks": hooks or TurnHooks(),
        "registry_mark": REGISTRY_MARK,
    }
