"""Shared (non-collected) ingest helpers for the Phase-H harnesses.

Underscore-prefixed so pytest does not collect it as a test module. Drives one
practice through the on-ramp to a chosen stage against the T005 synthetic fixture,
returning the handles (adapter/profile/export) the gates assert on.
"""
from __future__ import annotations

import uuid

from backend.envelope.completeness import CompletenessChecker
from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.normalizer import Normalizer
from backend.envelope.pims import load_adapters
from backend.envelope.pims.port import resolve_adapter
from backend.envelope.quality import QualityAssessor
from backend.envelope.state_machine import StateMachine
from backend.models import (
    CounselSignoff, FormatProfile, PracticeDatabase, PracticeState,
)
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import (
    generate_practice_export,
)

CLINIC = "goldsmith"

# The reused 011 HouseholdRepository.init_db() re-issues its append-only DDL
# (CREATE OR REPLACE FUNCTION + DROP/CREATE TRIGGER) on every call, which churns
# the shared Postgres system catalogs and races autovacuum ("tuple concurrently
# updated") when many tests each re-init. The tables persist for the whole
# session, so we init ONCE per process and reuse — cutting the harness's
# contribution to the shared catalog churn without forking the 011 module.
_HH_INITED: set[str] = set()


def review_queue(db_url: str):
    """A ``(ReviewQueue, HouseholdRepository)`` pair; the household schema is
    initialized at most once per process per db_url (see note above)."""
    from backend.relationship.household_repository import HouseholdRepository
    from backend.relationship.review_queue import ReviewQueue

    hr = HouseholdRepository(db_url)
    if db_url not in _HH_INITED:
        hr.init_db()
        _HH_INITED.add(db_url)
    return ReviewQueue(hr), hr


def new_pid(prefix: str = "p") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def adapter_for(pid: str, clinic: str = CLINIC):
    load_adapters()
    return resolve_adapter("ezyvet", "complete_v1", clinic_id=clinic, practice_id=pid,
                           practice_database_id="pdb1",
                           extraction_port=SimExtractionPort())


def normalize_once(repo, pid, *, clinic=CLINIC, seed=41, variant="complete",
                   planted="clean"):
    """Receive → profile → normalize (no state advance). Returns
    (exp, adapter, profile)."""
    repo.create_practice_database(PracticeDatabase(
        clinic_id=clinic, practice_id=pid, delivery_id="d1"))
    sm = StateMachine(repo)
    sm.receive(pid, clinic)
    exp = generate_practice_export(pid, seed=seed, variant=variant, planted=planted)
    adapter = adapter_for(pid, clinic)
    profile = adapter.profile(exp)
    repo.create_format_profile(FormatProfile(
        clinic_id=clinic, practice_id=pid, practice_database_id="pdb1",
        entities=profile.entities, encodings=profile.encodings,
        referential_relationships=profile.referential_relationships,
        export_variant=profile.export_variant))
    Normalizer(repo).normalize(clinic, pid, adapter, profile, exp)
    return exp, adapter, profile, sm


def verify_stage(repo, pid, *, clinic=CLINIC, seed=41, variant="complete",
                 planted="clean"):
    """Full ingest to `verified` (counsel + profile + normalize + completeness +
    quality). Returns (exp, adapter, profile, sm)."""
    exp, adapter, profile, sm = normalize_once(
        repo, pid, clinic=clinic, seed=seed, variant=variant, planted=planted)
    repo.append_counsel_signoff(CounselSignoff(
        clinic_id=clinic, practice_id=pid, signed_by="counsel"))
    sm.advance(pid, PracticeState.PROFILED)
    sm.advance(pid, PracticeState.NORMALIZED)
    CompletenessChecker(repo).check(clinic, pid)
    QualityAssessor(repo).assess(clinic, pid)
    sm.advance(pid, PracticeState.VERIFIED)
    return exp, adapter, profile, sm
