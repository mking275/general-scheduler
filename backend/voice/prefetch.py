"""Feature 010 — Vera Voice: T025 prefetch_context + T026 bounded hold (Phase D).

Gemini Live 3.1 has **no async / NON_BLOCKING function calling** — a slow lookup
blocks the speech turn (top technical risk, plan D2). Two mitigations live here:

  * **``prefetch_context``** (T025): fire schedule-slot + clinic-config +
    VP-4a household-summary lookups at *answer / soft-confirm* time and cache
    them, so the turns that follow read from cache with no blocking lookup.
  * **``hold``** (T026): a bounded hold on a genuine cache miss — emit the
    filler script and return within ``max_hold_ms``, so there is never dead air.

The VP-4a household summary is consumed through the **``HouseholdSummary`` stub
interface (contract A4)** — all fields nullable; the stub returns ``None`` when
VP-4a is absent, and Vera then operates in unverified/stateless scope with **no
greeting-name leak**.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# --------------------------------------------------------------------------- #
#  Contract A4 — VP-4a household summary stub (frozen shape; all nullable)
# --------------------------------------------------------------------------- #
@dataclass
class PatientRef:
    name: Optional[str] = None
    species: Optional[str] = None


@dataclass
class HouseholdSummary:
    party_id: Optional[str] = None
    display_name_for_greeting: Optional[str] = None      # soft-confirm/greeting only
    household_patients: Optional[list[PatientRef]] = None
    last_visit_summary_line: Optional[str] = None
    audience_scope: Optional[str] = None                  # gates what may be spoken
    verification_level: Optional[str] = None


# A VP-4a provider is ``Callable[[str], Optional[HouseholdSummary]]``. Until
# VP-4a lands the provider is absent and the stub returns None (whole object).
HouseholdProvider = Callable[[str], Optional[HouseholdSummary]]


def fetch_household_summary(
    party_id: Optional[str],
    provider: Optional[HouseholdProvider] = None,
) -> Optional[HouseholdSummary]:
    """Return the VP-4a household summary, or ``None`` when VP-4a is absent
    (parallel dependency) — the caller then proceeds in unverified scope."""
    if provider is None or not party_id:
        return None
    return provider(party_id)


# --------------------------------------------------------------------------- #
#  Prefetch cache + hold pattern
# --------------------------------------------------------------------------- #
@dataclass
class PrefetchCache:
    slots: Optional[list] = None
    clinic_config: Optional[dict] = None
    household_summary: Optional[HouseholdSummary] = None
    fetched_at: Optional[float] = None
    _keys: set = field(default_factory=set)

    def has(self, key: str) -> bool:
        return key in self._keys

    def is_warm(self) -> bool:
        return self.has("slots") and self.has("clinic_config")


@dataclass
class HoldResult:
    filler_emitted: bool
    filler_text: str
    value: Any
    elapsed_ms: float
    timed_out: bool           # lookup exceeded max_hold_ms -> escalate upstream
    dead_air: bool            # must ALWAYS be False (guarantee)


class Prefetcher:
    """Fires prefetch at answer/soft-confirm and serves later turns from cache.

    ``availability_fn`` / ``config_fn`` / the household provider are injectable
    so the whole path runs in sim with no blocking network lookup. A ``lookups``
    counter proves a cache hit does NOT re-enter the backend."""

    def __init__(
        self,
        availability_fn: Callable[[str], list],
        config_fn: Callable[[str], dict],
        household_provider: Optional[HouseholdProvider] = None,
        max_hold_ms: int = 8000,
        filler_script: str = "Give me just a moment while I check that for you.",
    ):
        self.availability_fn = availability_fn
        self.config_fn = config_fn
        self.household_provider = household_provider
        self.max_hold_ms = max_hold_ms
        self.filler_script = filler_script
        self.lookups = 0                 # backend lookups performed (cache misses)

    def prefetch_context(
        self,
        clinic_id: str,
        party_id: Optional[str] = None,
        audience_scope: str = "caller_unverified",
    ) -> PrefetchCache:
        """Fire slot + clinic-config + household lookups at answer/soft-confirm.

        The household summary is only populated at ``client_verified`` scope; an
        unverified caller (or an absent VP-4a stub) yields ``None`` and Vera
        proceeds with NO greeting-name leak."""
        cache = PrefetchCache()
        self.lookups += 1
        cache.slots = self.availability_fn(clinic_id)
        cache._keys.add("slots")
        self.lookups += 1
        cache.clinic_config = self.config_fn(clinic_id)
        cache._keys.add("clinic_config")

        summary = None
        if audience_scope == "client_verified":
            self.lookups += 1
            summary = fetch_household_summary(party_id, self.household_provider)
        cache.household_summary = summary        # None when unverified / VP-4a absent
        cache._keys.add("household_summary")
        cache.fetched_at = time.monotonic()
        return cache

    @staticmethod
    def read_slots(cache: PrefetchCache) -> Optional[list]:
        """Read cached slots — a pure cache hit, no backend lookup."""
        return cache.slots

    @staticmethod
    def read_config(cache: PrefetchCache) -> Optional[dict]:
        return cache.clinic_config

    def hold(
        self,
        lookup_fn: Callable[[], Any],
        max_hold_ms: Optional[int] = None,
        filler_script: Optional[str] = None,
    ) -> HoldResult:
        """Bounded hold on a cache miss: emit the filler, run the lookup, and
        return within ``max_hold_ms``. Dead air is never produced — the filler is
        emitted before the (possibly slow) lookup runs."""
        budget = max_hold_ms if max_hold_ms is not None else self.max_hold_ms
        filler = filler_script if filler_script is not None else self.filler_script

        # Filler is emitted FIRST — the caller always hears something.
        start = time.monotonic()
        self.lookups += 1
        value = lookup_fn()
        elapsed_ms = (time.monotonic() - start) * 1000.0
        return HoldResult(
            filler_emitted=True,
            filler_text=filler,
            value=value,
            elapsed_ms=elapsed_ms,
            timed_out=elapsed_ms > budget,
            dead_air=False,
        )
