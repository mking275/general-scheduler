"""Feature 010 — Vera Voice: T020/T021/T022 triage protocol ENGINE (Phase C).

A **deterministic, config-driven** keyword/urgency state machine. The engine and
YAML format are VetAgent-owned; the *content* (which keywords map to which
urgency class, and the vet signature) arrives from VP-9. Nothing here is an
assessment — the engine only routes: keyword -> urgency class -> routing target.

Safety posture (binding):
  * **Err-to-escalate.** When a keyword matches more than one class, the most
    urgent class wins. There is no "downgrade" path.
  * **Never assessment language.** The engine emits an urgency class + routing
    target, never a clinical judgement about the animal.
  * **Signature gate (T022).** An active protocol with no ``signed_by`` /
    ``signed_at`` is UNSIGNED test content — usable in sim only; it blocks live
    emergency handling. The bundled ``triage_protocol.goldsmith.sample.yaml`` is
    unsigned by design.

Wiring (T021): ``engine.as_protocol_step()`` returns the callable the
``turn_loop.ProtocolAwareHooks`` interposes in ``pre_speak`` with override
authority over the model's proposed output.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import yaml

# Default urgency severity order (most urgent first). Config may override via a
# top-level ``urgency_order`` list; unknown classes sort *after* the known ones
# so a novel/typo'd class never silently outranks "emergency".
DEFAULT_URGENCY_ORDER = ["emergency", "urgent", "routine"]

# The urgency classes the turn loop treats as escalation-worthy (see
# ``turn_loop.ProtocolAwareHooks.pre_speak``). Kept here so the two stay aligned.
ESCALATING_URGENCIES = ("emergency", "urgent")

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CONFIG_DIR = os.path.join(_REPO_ROOT, "config", "voice")


class UnsignedProtocolError(RuntimeError):
    """Raised when an unsigned protocol is asked to handle a LIVE emergency."""


@dataclass
class UrgencyClassDef:
    name: str
    routing_target: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class ProtocolConfig:
    version: str
    urgency_classes: dict[str, UrgencyClassDef]
    escalation_on_flag: float = 1.0
    signed_by: Optional[str] = None
    signed_at: Optional[str] = None
    urgency_order: list[str] = field(default_factory=lambda: list(DEFAULT_URGENCY_ORDER))

    @property
    def is_signed(self) -> bool:
        return bool(self.signed_by) and bool(self.signed_at)


def _parse_config(data: dict) -> ProtocolConfig:
    raw_classes = data.get("urgency_classes") or {}
    classes: dict[str, UrgencyClassDef] = {}
    for name, spec in raw_classes.items():
        spec = spec or {}
        classes[name] = UrgencyClassDef(
            name=name,
            routing_target=spec.get("routing_target", "on_call_vet"),
            keywords=[str(k).lower().strip() for k in (spec.get("keywords") or [])],
        )
    order = data.get("urgency_order") or DEFAULT_URGENCY_ORDER
    return ProtocolConfig(
        version=str(data.get("version", "0.0.0")),
        urgency_classes=classes,
        escalation_on_flag=float((data.get("slo") or {}).get("escalation_on_flag", 1.0)),
        signed_by=data.get("signed_by"),
        signed_at=data.get("signed_at"),
        urgency_order=list(order),
    )


class TriageProtocolEngine:
    """Deterministic keyword -> urgency-class router. No classifier, no priors."""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        # Precompute a severity rank for every class (lower rank = more urgent).
        self._rank: dict[str, int] = {}
        for i, name in enumerate(config.urgency_order):
            self._rank[name] = i
        # Unknown classes sort after all ordered ones (never outrank emergency).
        base = len(config.urgency_order)
        for name in config.urgency_classes:
            self._rank.setdefault(name, base)

    # --- loaders --------------------------------------------------------
    @classmethod
    def from_yaml_str(cls, yaml_str: str) -> "TriageProtocolEngine":
        return cls(_parse_config(yaml.safe_load(yaml_str) or {}))

    @classmethod
    def from_yaml(cls, path: str) -> "TriageProtocolEngine":
        with open(path) as f:
            return cls.from_yaml_str(f.read())

    @classmethod
    def load_sample(cls, clinic: str = "goldsmith") -> "TriageProtocolEngine":
        return cls.from_yaml(
            os.path.join(_CONFIG_DIR, f"triage_protocol.{clinic}.sample.yaml"))

    # --- signature gate (T022) -----------------------------------------
    @property
    def is_signed(self) -> bool:
        return self.config.is_signed

    def assert_live_allowed(self, is_live: bool) -> None:
        """An UNSIGNED protocol must never handle a live emergency (T022).
        Sim is always permitted so the engine can be exercised pre-signature."""
        if is_live and not self.is_signed:
            raise UnsignedProtocolError(
                f"triage protocol v{self.config.version} is unsigned "
                "(no signed_by/signed_at) — blocked from live emergency handling; "
                "sim only until VP-9 signs the content."
            )

    # --- the state machine step ----------------------------------------
    def step(self, transcript_delta: str) -> Optional[dict]:
        """Classify a transcript delta. Returns the flag dict for the most urgent
        matching class, or ``None`` if nothing matched.

        Return shape (consumed by ``turn_loop`` + the escalation watchdog):
            {"urgency": <class>, "routing_target": <target>,
             "matched_keyword": <kw>, "protocol_version": <ver>}
        """
        text = (transcript_delta or "").lower()
        if not text:
            return None

        best: Optional[tuple[int, str, UrgencyClassDef]] = None
        for cls_def in self.config.urgency_classes.values():
            for kw in cls_def.keywords:
                if kw and kw in text:
                    rank = self._rank.get(cls_def.name, len(self.config.urgency_order))
                    # Err-to-escalate: keep the LOWEST rank (most urgent) match.
                    if best is None or rank < best[0]:
                        best = (rank, kw, cls_def)
                    break  # one keyword per class is enough to flag it
        if best is None:
            return None
        _, kw, cls_def = best
        return {
            "urgency": cls_def.name,
            "routing_target": cls_def.routing_target,
            "matched_keyword": kw,
            "protocol_version": self.config.version,
        }

    # --- turn-loop adapter (T021) --------------------------------------
    def as_protocol_step(self) -> Callable[[str], Optional[dict]]:
        """Return the ``protocol_step`` callable for ``ProtocolAwareHooks``.
        The engine's decision OVERRIDES the model inside ``pre_speak``."""
        return self.step
