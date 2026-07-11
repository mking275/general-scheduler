"""Feature 011 — T020/T021 ScopedRecall rail (contract B).

[SHIM — extract to core rail post-confirmation]  Board ask #2: "if core builds
only one thing this month, build this." Until core lands the mandatory-audience
recall API, this wrapper makes an **unscoped client-facing recall unrepresentable
by API shape** — ``audience`` is a REQUIRED keyword-only argument, there is no
unscoped overload, and the raw Thoth handle is PRIVATE (name-mangled) so no
client-facing surface can reach it.

``_apply_policy`` runs the T018 default-deny filter and writes the T019
reveal-decision audit on every fact — revealed or withheld.

**Access-count caveat (shim-era, M3):** filtering happens AFTER Thoth's
``recall()``, which has already incremented ``access_count`` on every candidate
fact — including facts this wrapper then withholds. So ``access_count`` here
OVER-counts and MUST NOT drive salience / sleep-agent consolidation. It leaks
nothing to the caller (withheld facts never reach the response). The core-rail
extraction (contract A) resolves this by pushing ``audience``/``entity_scope``
INTO recall so a withheld fact is never touched (withheld ≠ accessed).

Registry status: ``prototype`` — deleted when core lands the mandatory-audience
API; the policy data (contract C) is unchanged and moves with the vertical.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from backend.relationship.reveal_log import RevealLog
from backend.relationship.scoping_policy import ScopingPolicy

Audience = Literal["owner", "manager", "staff", "client_verified", "caller_unverified"]


@dataclass
class Fact:
    """A recalled fact. ``fact_kind`` is the raw Thoth kind; the evaluator
    bridges it to a fact class. ``subject_household`` / ``subject_clinic`` drive
    the row-level scope predicates (``own_household_only`` / ``own_clinic_only``)."""
    fact_kind: str
    content: Any = None
    entity_ref: Optional[str] = None
    subject_household: Optional[str] = None
    subject_clinic: Optional[str] = None
    access_count: int = 0


class ThothStub:
    """Sim-only stand-in for core's shipped Thoth. Exposes the UNSCOPED
    ``recall`` / ``recall_by_kind`` surface exactly as core does — no audience
    parameter — so no live substrate call is made. Every ``recall`` increments
    ``access_count`` (the shim-era over-count, M3)."""

    def __init__(self, facts: Optional[list[Fact]] = None):
        self._facts: list[Fact] = list(facts or [])

    def _touch(self, facts: list[Fact]) -> list[Fact]:
        for f in facts:
            f.access_count += 1        # over-counts; see M3 caveat
        return facts

    async def recall(self, query: str) -> list[Fact]:
        return self._touch(list(self._facts))

    async def recall_by_kind(self, kind: str) -> list[Fact]:
        return self._touch([f for f in self._facts if f.fact_kind == kind])


class ScopedRecall:
    """The rail. Client-facing code holds only a ``ScopedRecall`` — never the
    raw Thoth handle. ``audience`` is REQUIRED (kw-only), so an unscoped recall
    is a construction/type error, not a runtime check."""

    def __init__(self, thoth: Any, policy: ScopingPolicy, reveal_log: RevealLog):
        # Name-mangled PRIVATE handle: unreachable from any client-facing surface.
        self.__thoth = thoth
        self.__policy = policy
        self.__reveal_log = reveal_log

    async def recall(self, query: str, *, audience: Audience,
                     entity_scope: list[str]) -> list[Fact]:
        raw = await self.__thoth.recall(query)               # core engine (unscoped)
        return self._apply_policy(raw, audience, entity_scope)

    async def recall_by_kind(self, kind: str, *, audience: Audience,
                             entity_scope: list[str]) -> list[Fact]:
        raw = await self.__thoth.recall_by_kind(kind)
        return self._apply_policy(raw, audience, entity_scope)

    # ------------------------------------------------------------------ #
    #  T018 default-deny filter + T019 audit on EVERY fact
    # ------------------------------------------------------------------ #
    def _apply_policy(self, raw: list[Fact], audience: Audience,
                      entity_scope: list[str]) -> list[Fact]:
        out: list[Fact] = []
        for f in raw:
            dec = self.__policy.evaluate(
                f.fact_kind, audience,
                subject_household=f.subject_household,
                subject_clinic=f.subject_clinic,
                entity_scope=entity_scope,
            )
            self.__reveal_log.record(
                audience=audience, fact_kind=f.fact_kind, decision=dec,
                entity_ref=f.entity_ref,
            )
            if dec.allowed:                # withheld facts NEVER reach the caller
                out.append(f)
        return out
