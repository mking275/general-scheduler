"""Feature 009 — T007 PimsAdapterPort + adapter registry.

The stable port a per-PIMS ingest adapter implements:

  * ``profile(raw_export) -> FormatProfile``  — discovery: enumerate entities,
    counts, encodings, referential relationships, and the export variant.
  * ``normalize(profile, raw_export) -> NormalizeResult`` — canonical records +
    lineage (every ``CanonicalRecord`` carries ``entity_ref`` / ``source_id``).

A registry keyed by ``(pims, variant)`` lets a second adapter plug in without
touching the core. The orchestration / verification / reconciliation core imports
**this port only** — never a concrete adapter (PIMS-agnostic; FR-027). ezyVet is
the first and only adapter this cycle (``ezyvet_adapter.py``); the second is
deferred until the target group's PIMS mix is known.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

from backend.models import CanonicalRecord, FormatProfile


@dataclass
class NormalizeResult:
    """The ``normalize()`` return shape: canonical records + lineage sidecars.
    Every record already carries ``entity_ref``/``source_id`` lineage; the
    unmapped lists carry what a known adapter could NOT map (flagged, never
    dropped — FR-007/FR-008 US3-scenario-3)."""
    records: list[CanonicalRecord] = field(default_factory=list)
    unmapped_entities: list[str] = field(default_factory=list)
    unmapped_fields: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class PimsAdapterPort(Protocol):
    """The stable ingest port. A concrete adapter (ezyVet, and any future PIMS)
    implements exactly this; the core depends only on this Protocol."""

    #: identifying key parts for the registry
    pims: str
    variant: str

    def profile(self, raw_export: Any) -> FormatProfile: ...

    def normalize(self, profile: FormatProfile, raw_export: Any) -> NormalizeResult: ...


# --------------------------------------------------------------------------- #
#  Registry — keyed by (pims, variant)
# --------------------------------------------------------------------------- #
_REGISTRY: dict[tuple[str, str], Callable[..., PimsAdapterPort]] = {}


def register_adapter(pims: str, variant: str,
                     factory: Callable[..., PimsAdapterPort]) -> None:
    """Register an adapter factory under ``(pims, variant)``. Idempotent —
    re-registering the same key replaces the factory (module reload safe)."""
    _REGISTRY[(pims.lower(), variant.lower())] = factory


def resolve_adapter(pims: str, variant: str, **kwargs) -> PimsAdapterPort:
    """Construct the adapter registered for ``(pims, variant)``.

    Falls back to the ``(pims, "*")`` wildcard if no exact-variant adapter is
    registered — a known PIMS whose delivered variant is unrecognized resolves
    to the base adapter, which flags the unrecognized variant for adapter work
    rather than force-fitting (edge case, US7)."""
    key = (pims.lower(), variant.lower())
    factory = _REGISTRY.get(key) or _REGISTRY.get((pims.lower(), "*"))
    if factory is None:
        raise KeyError(f"no adapter registered for pims={pims!r} variant={variant!r}")
    return factory(**kwargs)


def registered_keys() -> list[tuple[str, str]]:
    return sorted(_REGISTRY.keys())


def is_registered(pims: str, variant: str) -> bool:
    key = (pims.lower(), variant.lower())
    return key in _REGISTRY or (pims.lower(), "*") in _REGISTRY
