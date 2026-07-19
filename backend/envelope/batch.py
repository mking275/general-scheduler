"""Feature 009 — T033 batch orchestration + group rollup + prior inheritance.

Drives a multi-practice batch through the full on-ramp — receipt → discovery →
normalize → verify → reconcile → group-ack → identity → ``shadow_ready`` — with
three load-bearing properties:

  * **Practices are independent units.** Each practice runs in isolation; a
    ``held`` / ``blocked`` / ``partial`` practice **never stalls the batch** — the
    unblocked practices still reach ``shadow_ready`` (FR-024/025).
  * **The group rollup is a computed view** over the true per-practice rows —
    every practice's stage/status, a blocked one visible but not stalling (FR-024).
  * **Prior inheritance** (FR-026, SC-010): the adapter's per-variant field map is
    a **group-level prior**, established once and reused by every subsequent
    practice of the same PIMS/variant — each database is still profiled
    independently for schema drift, but the mapping is not re-derived. The
    per-practice **marginal mapping steps** trend down to 0 (config-reuse only).

**Bootstrap seam (binding)**: the orchestrator calls ``pims.load_adapters()`` as
its bootstrap — the PIMS-agnostic core never imports a concrete adapter; it
resolves everything through ``pims.port`` (FR-027).

**Invisible adoption (T032)**: the finalize gate runs the readiness evaluator,
whose invisible-adoption assertion rejects any run that emitted a staff-facing
artifact — a clinician in the export becomes a **data-only** ``staff:*`` canonical
row (scheduling/attribution), never a login/notification/dashboard (the batch-wide
red-team scan gates SC-006 = 0 at T041).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.envelope.completeness import CompletenessChecker
from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.gap_notice import GapNoticeService
from backend.envelope.identity_bootstrap import IdentityBootstrap
from backend.envelope.idempotency import rerun_diff
from backend.envelope.normalizer import Normalizer
from backend.envelope.owner_surface import OwnerSurface
from backend.envelope.quality import QualityAssessor, enforce_floor
from backend.envelope.readiness import ReadinessEvaluator
from backend.envelope.reconciliation import Reconciler
from backend.envelope.scope_check import ScopeChecker, manifest_from_export
from backend.envelope.state_machine import StateMachine
from backend.envelope.vault import ReceiptService, ReceivedExport
from backend.models import (
    BatchRollup, CounselSignoff, FormatProfile, PracticeState,
)

_PIMS = "ezyvet"
_VARIANT = "complete_v1"


@dataclass
class PracticeOutcome:
    practice_id: str
    state: str
    shadow_ready: bool = False
    marginal_mapping_steps: int = 0
    disposition: str = "received"        # receipt disposition (received/duplicate/…)
    blocked_reason: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BatchResult:
    clinic_id: str
    delivery_id: str
    order: list[str]
    outcomes: dict[str, PracticeOutcome] = field(default_factory=dict)
    rollup: dict[str, dict] = field(default_factory=dict)

    # -- SC-010 measurement: marginal mapping steps in practice order -------- #
    @property
    def marginal_mapping_steps(self) -> list[int]:
        return [self.outcomes[pid].marginal_mapping_steps for pid in self.order]

    @property
    def shadow_ready_practices(self) -> list[str]:
        return sorted(pid for pid, o in self.outcomes.items() if o.shadow_ready)


class BatchOrchestrator:
    def __init__(self, repo, review_queue, *, vault: Optional[Any] = None,
                 sms_gateway: Optional[Any] = None):
        self.repo = repo
        self.review = review_queue
        self.vault = vault
        self.sms = sms_gateway
        self.sm = StateMachine(repo)
        # the established group-level priors: (pims, variant) already mapped.
        self._priors: set[tuple[str, str]] = set()
        # per-practice ingest context needed by the finalize pass.
        self._ctx: dict[str, tuple[Any, Any, Any]] = {}

    # ------------------------------------------------------------------ #
    #  run — the whole batch
    # ------------------------------------------------------------------ #
    def run(self, clinic_id: str, exports: list[Any], *,
            source: str = "secure-file-transfer", counsel_signed: bool = True
            ) -> BatchResult:
        # BOOTSTRAP: the core never imports a concrete adapter (FR-027).
        from backend.envelope.pims import load_adapters
        from backend.envelope.pims.port import resolve_adapter
        load_adapters()
        self._resolve_adapter = resolve_adapter

        order = [e.practice_id for e in exports]
        result = BatchResult(clinic_id=clinic_id, delivery_id="", order=order)

        # 1) receipt under chain of custody (one delivery, all practices).
        receipt = ReceiptService(self.repo, self.vault).receive_delivery(
            clinic_id, source,
            [ReceivedExport(e.practice_id, e.raw_bytes()) for e in exports])
        result.delivery_id = receipt.delivery_id
        disp = {p.practice_id: p.disposition for p in receipt.practices}

        # 2) Pass A — per practice, INDEPENDENT: ingest → verify → reconcile.
        for exp in exports:
            outcome = self._pass_a(clinic_id, exp, counsel_signed)
            outcome.disposition = disp.get(exp.practice_id, "received")
            result.outcomes[exp.practice_id] = outcome

        # 3) group acknowledgment (owner surface) — acks non-blocking reconciled
        #    practices, skips blocking ones (never stalls the batch).
        OwnerSurface(self.repo, self.sms).acknowledge_group(
            clinic_id, order, acknowledged_by="owner")

        # 4) Pass B — per practice, INDEPENDENT: reconciled → identity → shadow.
        for exp in exports:
            self._pass_b(clinic_id, exp, result.outcomes[exp.practice_id])

        # 5) group rollup — a computed view over the true per-practice rows.
        result.rollup = self._build_rollup(clinic_id, result)
        return result

    # ------------------------------------------------------------------ #
    #  Pass A — ingest → verify → reconcile (each practice isolated)
    # ------------------------------------------------------------------ #
    def _pass_a(self, clinic_id: str, exp: Any, counsel_signed: bool
                ) -> PracticeOutcome:
        pid = exp.practice_id
        outcome = PracticeOutcome(practice_id=pid, state="received")
        try:
            pdb = self.repo.get_practice_database_by_practice(pid)
            pdb_id = pdb["id"] if pdb else "pdb"

            # scope-vs-request (manifest read; pre-normalize).
            ScopeChecker(self.repo).check(clinic_id, pid, pdb_id,
                                          manifest_from_export(exp))

            # counsel gate — the hard pre-normalization gate (FR-004). In sim the
            # signoff row stands in; without it, the state machine blocks advance.
            if counsel_signed:
                self.repo.append_counsel_signoff(CounselSignoff(
                    clinic_id=clinic_id, practice_id=pid, signed_by="counsel",
                    scope="clinic-owned-data structure"))

            # adapter via the port + prior-inheritance accounting.
            adapter = self._resolve_adapter(
                _PIMS, _VARIANT, clinic_id=clinic_id, practice_id=pid,
                practice_database_id=pdb_id, extraction_port=SimExtractionPort())
            profile = adapter.profile(exp)
            outcome.marginal_mapping_steps = self._track_prior(
                adapter.pims, profile.export_variant or adapter.variant)

            self.repo.create_format_profile(FormatProfile(
                clinic_id=clinic_id, practice_id=pid, practice_database_id=pdb_id,
                entities=profile.entities, encodings=profile.encodings,
                referential_relationships=profile.referential_relationships,
                export_variant=profile.export_variant,
                unmapped_flags=profile.unmapped_flags))

            Normalizer(self.repo).normalize(clinic_id, pid, adapter, profile, exp)
            self.sm.advance(pid, PracticeState.PROFILED, clinic_id=clinic_id)
            self.sm.advance(pid, PracticeState.NORMALIZED, clinic_id=clinic_id)

            # completeness + quality; a >20%-unusable practice is HELD (never
            # advances) but the batch keeps going.
            CompletenessChecker(self.repo).check(clinic_id, pid)
            qa = QualityAssessor(self.repo).assess(clinic_id, pid)
            if enforce_floor(self.sm, pid, qa, clinic_id):
                outcome.state = self.sm.current_state(pid)
                outcome.blocked_reason = "quality floor breached (>20% unusable)"
                return outcome

            self.sm.advance(pid, PracticeState.VERIFIED, clinic_id=clinic_id)

            # reconcile against the source's own reported figures.
            report = Reconciler(self.repo).reconcile(
                clinic_id, pid, getattr(exp, "reported_figures", {}) or {})

            # partial delivery → owner-facing gap notice + PARTIAL hold (proceeds
            # on delivered data, not marked complete).
            gap = GapNoticeService(self.repo).detect_and_notice(
                clinic_id, pid, state_machine=self.sm)

            if report.blocking:
                outcome.state = self.sm.current_state(pid)   # stays `verified`
                outcome.blocked_reason = "unexplained AR variance (zero-tolerance)"
                return outcome
            if gap is not None:
                outcome.state = self.sm.current_state(pid)   # `partial`
                outcome.blocked_reason = (
                    f"partial delivery: {', '.join(gap.missing_categories)}")
                return outcome

            # a clean, complete, reconciled practice — hand context to Pass B.
            self._ctx[pid] = (adapter, profile, exp)
            outcome.state = self.sm.current_state(pid)        # `verified`
            return outcome
        except Exception as exc:  # a single practice's failure never stalls others
            outcome.state = self.sm.current_state(pid) or "received"
            outcome.error = f"{type(exc).__name__}: {exc}"
            return outcome

    # ------------------------------------------------------------------ #
    #  Pass B — reconciled → identity → shadow_ready (each practice isolated)
    # ------------------------------------------------------------------ #
    def _pass_b(self, clinic_id: str, exp: Any, outcome: PracticeOutcome) -> None:
        pid = exp.practice_id
        if outcome.state != PracticeState.VERIFIED.value or pid not in self._ctx:
            return
        surface = OwnerSurface(self.repo, self.sms)
        if not surface.is_activatable(pid):      # not group-acknowledged
            return
        try:
            adapter, profile, exp_ctx = self._ctx[pid]
            self.sm.advance(pid, PracticeState.RECONCILED, clinic_id=clinic_id)

            boot = IdentityBootstrap(self.repo, self.review)
            bres = boot.bootstrap(clinic_id, pid)
            boot.build_corpus(clinic_id, pid, bres,
                              answer_key=getattr(exp_ctx, "answer_key", None))
            self.sm.advance(pid, PracticeState.IDENTITY_BOOTSTRAPPED,
                            clinic_id=clinic_id)

            # the formal re-run-diff idempotency proof (T038), feeding readiness.
            idem = rerun_diff(self.repo, clinic_id, pid, adapter, profile, exp_ctx)
            readiness = ReadinessEvaluator(self.repo).evaluate(
                clinic_id, pid, idempotency_report=idem)

            if readiness.shadow_ready:
                self.sm.advance(pid, PracticeState.SHADOW_READY, clinic_id=clinic_id)
                outcome.shadow_ready = True
            outcome.state = self.sm.current_state(pid)
        except Exception as exc:
            outcome.state = self.sm.current_state(pid)
            outcome.error = f"{type(exc).__name__}: {exc}"

    # ------------------------------------------------------------------ #
    #  Prior inheritance — the group-level mapping prior, established once
    # ------------------------------------------------------------------ #
    def _track_prior(self, pims: str, variant: str) -> int:
        """Return this practice's marginal mapping steps: 1 the first time a
        (pims, variant) prior is established for the group, 0 thereafter (the
        mapping is reused; each database is still profiled independently)."""
        key = (pims.lower(), (variant or "").lower())
        if key in self._priors:
            return 0
        self._priors.add(key)
        return 1

    # ------------------------------------------------------------------ #
    #  Group rollup — a computed view over the true per-practice rows
    # ------------------------------------------------------------------ #
    def _build_rollup(self, clinic_id: str, result: BatchResult) -> dict[str, dict]:
        per_practice: dict[str, dict] = {}
        for pid in result.order:
            o = result.outcomes[pid]
            # read the TRUE persisted state (not just the in-memory outcome).
            pdb = self.repo.get_practice_database_by_practice(pid)
            per_practice[pid] = {
                "state": (pdb or {}).get("state", o.state),
                "shadow_ready": o.shadow_ready,
                "marginal_mapping_steps": o.marginal_mapping_steps,
                "blocked_reason": o.blocked_reason,
                "error": o.error,
            }
        self.repo.create_batch_rollup(BatchRollup(
            clinic_id=clinic_id, delivery_id=result.delivery_id,
            per_practice=per_practice))
        return per_practice
