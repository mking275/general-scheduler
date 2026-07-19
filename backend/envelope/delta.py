"""Feature 009 — T035 idempotent delta re-ingest (closes a partial-delivery gap).

A later delta delivery of the previously-missing category is ingested
**idempotently** (deterministic ``source_id``/``entity_ref`` keys → no
duplicates), **merges** against the earlier receipt in the canonical store, and
**updates** the reconciliation report — the outstanding gap closes and the
practice advances past ``partial`` (FR-032).

A corrupt/truncated/unreadable delta export fails at **discovery** with a specific
error (``DiscoveryError``) and is **never partially normalized** — the canonical
store is left untouched (FR-033).

This is the onboarding-completion step for a late partial delivery — **not** the
ongoing delta-**sync** engine (010, out of scope): it runs once, on receipt of the
missing category, to finish the initial bulk load.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from backend.envelope.completeness import CompletenessChecker
from backend.envelope.normalizer import Normalizer
from backend.envelope.reconciliation import Reconciler
from backend.envelope.state_machine import StateMachine
from backend.models import PracticeState

# states from which a delta merge may re-open the pipeline.
_MERGEABLE = {PracticeState.PARTIAL.value, PracticeState.DELTA.value}


@dataclass
class DeltaResult:
    practice_id: str
    state: str
    report: Any
    gap_closed: bool
    records_added: int      # net canonical growth (0 on a redundant re-run = idempotent)


def reingest_delta(repo, clinic_id: str, practice_id: str, adapter,
                   delta_export: Any, reported_figures: dict,
                   attributed_causes: Optional[dict] = None) -> DeltaResult:
    """Merge a late delta delivery into an existing partial practice, idempotently.

    ``adapter`` is a resolved ``PimsAdapterPort``; ``delta_export`` is the delta
    bundle (the missing category, arriving later). Raises ``DiscoveryError`` on a
    corrupt export **before** any normalization (canonical store untouched)."""
    before = repo.count_canonical("canonical_record", practice_id)

    # discovery FIRST — a corrupt/truncated export fails here, pre-normalize.
    profile = adapter.profile(delta_export)

    # idempotent merge: the normalizer upserts on the deterministic lineage keys,
    # so a record already present from the earlier receipt is refreshed-in-place
    # (0 duplicates) and the newly-arrived category is added.
    Normalizer(repo).normalize(clinic_id, practice_id, adapter, profile, delta_export)
    after = repo.count_canonical("canonical_record", practice_id)

    sm = StateMachine(repo)
    if sm.current_state(practice_id) in _MERGEABLE:
        sm.advance(practice_id, PracticeState.DELTA, clinic_id=clinic_id,
                   reason="delta re-ingest: late category merged")

    # re-verify + re-reconcile so the report reflects the closed gap.
    CompletenessChecker(repo).check(clinic_id, practice_id)
    report = Reconciler(repo).reconcile(clinic_id, practice_id, reported_figures,
                                        attributed_causes=attributed_causes)

    # ``records_added`` is the net canonical growth. On first arrival it equals
    # the delta's genuinely-new records; on a redundant re-run of the same delta
    # it is 0 (the upsert keys on source_id/entity_ref — no duplicates), which is
    # the idempotency proof the harness drives by running the delta twice.
    return DeltaResult(
        practice_id=practice_id, state=sm.current_state(practice_id),
        report=report,
        gap_closed=not report.outstanding_gap,
        records_added=max(after - before, 0),
    )
