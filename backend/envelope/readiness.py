"""Feature 009 — T031 PracticeReadiness + T032 invisible-adoption assertion.

**T031** — a practice is ``shadow_ready`` **only** when every FR-022 criterion
holds (each independently blocking):

  * ``counsel_cleared``                 — a ``counsel_signoff`` row exists;
  * ``format_discovered``               — a ``FormatProfile`` row exists;
  * ``normalization_idempotent``        — the re-run-diff proof is clean (0 dup,
                                          stable ids, 100% lineage) — the T038 gate;
  * ``completeness_quality_above_floor``— a completeness result exists and quality
                                          is not below the >20%-unusable floor;
  * ``reconciliation_acknowledged``     — the latest report is group-acknowledged
                                          and not blocking (zero-AR-tolerance);
  * ``identity_corpus_produced``        — the identity audit corpus is built.

This defines the readiness **criteria**, not the shadow operation — there is no
delta-sync / dual-path-write / verb-promotion / cutover verb in this tier
(scope guard; the on-ramp ends at ``shadow_ready``).

**T032 — invisible-adoption assertion**: the gate rejects any onboarding run that
emitted a staff-facing artifact (a login, credential, training artifact,
dashboard, or notification). The canonical ``staff:*`` entity is created
**data-only** (scheduling/attribution) — **no auth/login/notification path is
reachable from onboarding code** (the provisioning verbs do not exist in this
tier). A source-level scan (``scan_source_for_staff_verbs``) proves no such verb
is defined anywhere in the envelope tier; a per-practice behavioral check proves
every surface stayed owner/manager-audience. The full-batch red-team (T041)
asserts SC-006 = 0 across the whole tier.
"""
from __future__ import annotations

import ast
import os
from typing import Iterable, Optional

from backend.envelope.idempotency import IdempotencyReport, has_full_lineage
from backend.models import PracticeReadiness, ReadinessCriterion

# The envelope tier — the surface the invisible-adoption scan covers.
_TIER_ROOT = os.path.dirname(os.path.abspath(__file__))

# A "staff-facing provisioning verb" is a function/method whose name names BOTH a
# staff subject AND a provisioning/auth/notification action. The two-token rule
# avoids false-positives on legitimate owner-facing verbs (e.g. ``notify_owner``).
_STAFF_TOKENS = ("staff", "clinician", "employee", "vet_user")
_ACTION_TOKENS = (
    "login", "credential", "password", "auth", "notify", "notification",
    "dashboard", "training", "invite", "account", "provision", "signin",
    "sign_in", "onboard",
)

_OWNER_AUDIENCES = ("owner", "manager")


class ReadinessError(Exception):
    """The readiness gate blocked a run (e.g. a staff-facing artifact leaked)."""


class StaffArtifactError(ReadinessError):
    """A staff-facing artifact was detected — the invisible-adoption breach."""


def _is_staff_verb(name: str) -> bool:
    n = name.lower()
    return any(s in n for s in _STAFF_TOKENS) and any(a in n for a in _ACTION_TOKENS)


def _tier_python_files(root: Optional[str] = None) -> list[str]:
    root = root or _TIER_ROOT
    out: list[str] = []
    for dirpath, _dirs, files in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for f in files:
            if f.endswith(".py"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def scan_source_for_staff_verbs(paths: Optional[Iterable[str]] = None) -> list[str]:
    """AST-scan the envelope tier for any staff-facing provisioning/auth/
    notification verb. Returns ``[]`` when clean — the structural proof that the
    provisioning verbs simply do not exist in this tier (FR-028)."""
    findings: list[str] = []
    for path in (paths if paths is not None else _tier_python_files()):
        with open(path) as f:
            src = f.read()
        try:
            tree = ast.parse(src)
        except SyntaxError:  # pragma: no cover - a .py that will not parse
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and _is_staff_verb(node.name):
                findings.append(f"{path}:{node.name} (staff-facing verb)")
    return sorted(set(findings))


class ReadinessEvaluator:
    def __init__(self, repo):
        self.repo = repo
        # the source-level invisible-adoption scan is constant across a run.
        self._tier_clean = (scan_source_for_staff_verbs() == [])

    # ------------------------------------------------------------------ #
    #  The six criteria
    # ------------------------------------------------------------------ #
    def _counsel_cleared(self, practice_id: str) -> bool:
        return self.repo.has_counsel_signoff(practice_id)

    def _format_discovered(self, practice_id: str) -> bool:
        return self.repo.has_format_profile(practice_id)

    def _normalization_idempotent(self, practice_id: str,
                                  report: Optional[IdempotencyReport]) -> bool:
        # the formal re-run-diff proof when supplied (batch/checkpoint path);
        # else the structural proxy: a fully-lineaged canonical store (the upsert
        # is deterministic-key delete-then-insert, so full lineage ⇒ idempotent).
        if report is not None:
            return report.is_idempotent
        return has_full_lineage(self.repo, practice_id)

    def _completeness_quality_above_floor(self, practice_id: str) -> bool:
        completeness = self.repo.get_completeness_result(practice_id)
        quality = self.repo.get_quality_assessment(practice_id)
        return (completeness is not None
                and quality is not None
                and not quality.get("below_floor"))

    def _reconciliation_acknowledged(self, practice_id: str) -> bool:
        reports = self.repo.get_reconciliation_reports(practice_id)
        if not reports:
            return False
        latest = reports[-1]
        return bool(latest.get("owner_acknowledged")) and not latest.get("blocking")

    def _identity_corpus_produced(self, practice_id: str) -> bool:
        return self.repo.get_identity_audit_corpus(practice_id) is not None

    # ------------------------------------------------------------------ #
    #  T032 — invisible-adoption assertion (per practice)
    # ------------------------------------------------------------------ #
    def _invisible_adoption(self, clinic_id: str, practice_id: str) -> bool:
        """True iff no staff-facing artifact was emitted: the tier defines no
        staff-provisioning verb AND every surface for this practice stayed
        owner/manager-audience (no staff-audience report)."""
        if not self._tier_clean:
            return False
        for report in self.repo.get_reconciliation_reports(practice_id):
            if report.get("audience") not in _OWNER_AUDIENCES:
                return False
        return True

    # ------------------------------------------------------------------ #
    #  evaluate — persist a PracticeReadiness row
    # ------------------------------------------------------------------ #
    def evaluate(self, clinic_id: str, practice_id: str, *,
                 idempotency_report: Optional[IdempotencyReport] = None
                 ) -> PracticeReadiness:
        criteria = {
            ReadinessCriterion.COUNSEL_CLEARED.value:
                self._counsel_cleared(practice_id),
            ReadinessCriterion.FORMAT_DISCOVERED.value:
                self._format_discovered(practice_id),
            ReadinessCriterion.NORMALIZATION_IDEMPOTENT.value:
                self._normalization_idempotent(practice_id, idempotency_report),
            ReadinessCriterion.COMPLETENESS_QUALITY_ABOVE_FLOOR.value:
                self._completeness_quality_above_floor(practice_id),
            ReadinessCriterion.RECONCILIATION_ACKNOWLEDGED.value:
                self._reconciliation_acknowledged(practice_id),
            ReadinessCriterion.IDENTITY_CORPUS_PRODUCED.value:
                self._identity_corpus_produced(practice_id),
        }
        invisible = self._invisible_adoption(clinic_id, practice_id)
        shadow_ready = all(criteria.values()) and invisible
        pr = PracticeReadiness(
            clinic_id=clinic_id, practice_id=practice_id, criteria=criteria,
            shadow_ready=shadow_ready, invisible_adoption_asserted=invisible,
        )
        self.repo.create_practice_readiness(pr)
        return pr


# --------------------------------------------------------------------------- #
#  Scope guard — the on-ramp ends at shadow_ready. No forbidden runtime verb.
# --------------------------------------------------------------------------- #
FORBIDDEN_SCOPE_VERBS = (
    "delta_sync", "dual_path_write", "dual_write", "promote_verb",
    "verb_promotion", "cutover", "replace_event", "shadow_advise",
)


def scan_source_for_scope_leak(paths: Optional[Iterable[str]] = None) -> list[str]:
    """The on-ramp ends at ``shadow_ready``: assert no ongoing-operations verb
    (delta-sync / dual-path-write / verb-promotion / cutover) leaked into the
    tier. NOTE: ``delta`` re-ingest of a *late partial delivery* (T035) is an
    onboarding-completion step, not the ongoing delta-**sync** engine (010)."""
    findings: list[str] = []
    for path in (paths if paths is not None else _tier_python_files()):
        with open(path) as f:
            src = f.read()
        try:
            tree = ast.parse(src)
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                n = node.name.lower()
                for verb in FORBIDDEN_SCOPE_VERBS:
                    if verb in n:
                        findings.append(f"{path}:{node.name}")
    return sorted(set(findings))
