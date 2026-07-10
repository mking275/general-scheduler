"""Feature 010 — Vera Voice: T032 telemetry (contract B6).

``CallTelemetry`` is emitted from **call #1**. Cost is priced from the
per-provider rate fixture ``backend/voice/config/pricing.yml`` (T003 / FR-030) —
never a hard-coded guess. Turn latency p50/p95 come from the append-only
``call_turn`` log (T018). The **single source of the containment metric** is
``call_session.containment_flag`` (booked ⊆ contained; F2) — ``call_outcome`` is
a descriptive label only, never the metric.

SC-004 containment rate = ``count(containment_flag = true) / non-emergency calls``
(``containment_rate``); an escalated call is the emergency path and is excluded
from the denominator.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Optional

import yaml

_PRICING_PATH = os.path.join(os.path.dirname(__file__), "config", "pricing.yml")

_MICRO = 6  # cost rounding — sub-cent COGS matters at per-call granularity


# --------------------------------------------------------------------------- #
#  Pricing (from the pricing.yml fixture — the cost-per-call source)
# --------------------------------------------------------------------------- #
def load_pricing(path: Optional[str] = None) -> dict:
    with open(path or _PRICING_PATH) as f:
        return (yaml.safe_load(f) or {}).get("providers", {})


def _provider_key(provider: Any) -> str:
    return provider.value if hasattr(provider, "value") else str(provider)


def compute_cost_usd(provider: Any, audio_in_min: float, audio_out_min: float,
                     text_tokens: int = 0, pricing: Optional[dict] = None) -> float:
    """Per-call COGS = audio-in + audio-out + text, priced from ``pricing.yml``."""
    pricing = pricing if pricing is not None else load_pricing()
    rates = pricing.get(_provider_key(provider))
    if rates is None:
        raise KeyError(f"no pricing for provider {_provider_key(provider)!r} in pricing.yml")
    cost = (
        audio_in_min * float(rates["audio_in_usd_per_min"])
        + audio_out_min * float(rates["audio_out_usd_per_min"])
        + (text_tokens / 1000.0) * float(rates["text_usd_per_1k_tokens"])
    )
    return round(cost, _MICRO)


# --------------------------------------------------------------------------- #
#  Latency percentiles (from the call_turn log)
# --------------------------------------------------------------------------- #
def _percentile(sorted_vals: list[int], pct: float) -> int:
    if not sorted_vals:
        return 0
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return int(round(sorted_vals[int(k)]))
    frac = k - lo
    return int(round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac))


def latency_percentiles(turns: list) -> tuple[int, int]:
    """(p50, p95) over the non-null ``latency_ms`` of the call's turns."""
    vals = sorted(int(_get(t, "latency_ms")) for t in turns
                  if _get(t, "latency_ms") is not None)
    return _percentile(vals, 50), _percentile(vals, 95)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# --------------------------------------------------------------------------- #
#  Telemetry record (contract B6)
# --------------------------------------------------------------------------- #
@dataclass
class EscalationDetail:
    trigger: Optional[str]
    target: Optional[str]
    outcome: Optional[str]
    watchdog_fired: bool = False

    @classmethod
    def from_event(cls, ev: Any) -> "EscalationDetail":
        return cls(
            trigger=_enum_str(_get(ev, "trigger")),
            target=_get(ev, "transfer_target_id"),
            outcome=_enum_str(_get(ev, "transfer_outcome")),
            watchdog_fired=bool(_get(ev, "watchdog_fired", False)),
        )


@dataclass
class CallTelemetry:
    cost_usd: float
    turn_latency_p50_ms: int
    turn_latency_p95_ms: int
    call_outcome: Optional[str]          # descriptive label — NOT the metric
    containment_flag: bool               # single source of the containment metric
    escalation: Optional[EscalationDetail]
    barge_in_false_rate: float
    model_provider: Optional[str]
    session_resume_count: int


def _enum_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def build_call_telemetry(
    session: Any,
    turns: list,
    *,
    audio_in_min: float,
    audio_out_min: float,
    text_tokens: int = 0,
    escalation: Any = None,
    barge_in_false_rate: float = 0.0,
    pricing: Optional[dict] = None,
    repo=None,
) -> CallTelemetry:
    """Assemble the per-call telemetry. If ``repo`` is given, ``cost_usd`` is
    persisted back to the ``call_session`` row (from call #1)."""
    provider = _get(session, "model_provider")
    cost = compute_cost_usd(provider or "gemini_live", audio_in_min, audio_out_min,
                            text_tokens, pricing=pricing)
    p50, p95 = latency_percentiles(turns)
    tel = CallTelemetry(
        cost_usd=cost,
        turn_latency_p50_ms=p50,
        turn_latency_p95_ms=p95,
        call_outcome=_enum_str(_get(session, "call_outcome")),
        containment_flag=bool(_get(session, "containment_flag", False)),
        escalation=EscalationDetail.from_event(escalation) if escalation is not None else None,
        barge_in_false_rate=barge_in_false_rate,
        model_provider=_enum_str(provider),
        session_resume_count=int(_get(session, "session_resume_count", 0) or 0),
    )
    if repo is not None:
        repo.update_call_session(_get(session, "id"), cost_usd=cost)
    return tel


# --------------------------------------------------------------------------- #
#  SC-004 containment rate (booked ⊆ contained; F2)
# --------------------------------------------------------------------------- #
def _is_emergency(session: Any) -> bool:
    """The emergency/escalation path — excluded from the SC-004 denominator."""
    return _enum_str(_get(session, "call_outcome")) == "escalated"


def containment_rate(sessions: list) -> float:
    """``count(containment_flag = true) / non-emergency calls`` (SC-004).

    Non-emergency = calls whose outcome is not ``escalated``. A booked call and a
    plain contained call both count as contained (booked ⊆ contained)."""
    non_emergency = [s for s in sessions if not _is_emergency(s)]
    if not non_emergency:
        return 0.0
    contained = [s for s in non_emergency if _get(s, "containment_flag", False)]
    return len(contained) / len(non_emergency)
