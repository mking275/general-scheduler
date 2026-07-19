"""Feature 009+010 — the envelope→voice context bridge.

Proves the seam glue: a ``shadow_ready`` practice's 009-hydrated owners /
patients / appointments / refill-relevant data is resolvable from the
``canonical_record`` spine through a voice session's ``EnvelopeContextProvider``,
that lineage is preserved on every served record, and — the hard gate — that a
practice which is NOT ``shadow_ready`` is denied (both an explicit
``shadow_ready=False`` row and the no-row case).

Runs on the same local docker-compose Postgres the 009/010/011 suites use
(``VOICE_DATABASE_URL``, host port 5433); skips if unavailable.
"""
import os
import uuid

import pytest

from backend.relationship import entity_ref as eref
from backend.models import PracticeReadiness
from backend.voice.envelope_context import (
    EnvelopeContextProvider,
    PracticeNotReadyError,
)


def _default_db_url() -> str:
    return os.environ.get(
        "VOICE_DATABASE_URL",
        "postgresql+psycopg2://voice:voice@localhost:5433/voice",
    )


@pytest.fixture()
def repo():
    from backend.envelope.onboarding_repository import OnboardingRepository

    r = OnboardingRepository(_default_db_url())
    try:
        r.init_db()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"envelope Postgres unavailable: {exc}")
    return r


# --------------------------------------------------------------------------- #
#  Fixture hydration — write canonical_record rows the way the 009 normalizer
#  does (generic spine, keyed on (practice_id, entity_ref)), using the real
#  entity_ref builders so served lineage keys are byte-identical to production.
# --------------------------------------------------------------------------- #
def _canon_row(clinic_id, practice_id, category, entity_ref, source_id, payload):
    return {
        "id": str(uuid.uuid4()),
        "clinic_id": clinic_id,
        "practice_id": practice_id,
        "category": category,
        "entity_ref": entity_ref,
        "source_id": source_id,
        "payload": payload,
        "unmapped_fields": {},
    }


def _hydrate_practice(repo, clinic_id, practice_id):
    """Seed one owner with two patients, an appointment, and a product."""
    client_id, patient_a, patient_b, appt_id, prod_id = "c700", "p810", "p811", "a900", "sku5"
    rows = [
        _canon_row(clinic_id, practice_id, "client",
                   eref.client_ref(client_id), client_id,
                   {"source_id": client_id, "first_name": "Dana", "last_name": "Reyes",
                    "phone": "(555) 201-7788", "email": "dana@example.com"}),
        _canon_row(clinic_id, practice_id, "patient",
                   eref.patient_ref(patient_a), patient_a,
                   {"source_id": patient_a, "client_source_id": client_id,
                    "name": "Biscuit", "species": "canine", "status": "active"}),
        _canon_row(clinic_id, practice_id, "patient",
                   eref.patient_ref(patient_b), patient_b,
                   {"source_id": patient_b, "client_source_id": client_id,
                    "name": "Ghost", "species": "feline", "status": "deceased"}),
        _canon_row(clinic_id, practice_id, "appointment",
                   f"appointment:{eref.PIMS_PREFIX}_{appt_id}", appt_id,
                   {"source_id": appt_id, "patient_source_id": patient_a,
                    "provider_source_id": "prov1", "start_time": "2026-10-06T14:00",
                    "appointment_type": "follow-up"}),
        _canon_row(clinic_id, practice_id, "product_service",
                   f"product_service:{eref.PIMS_PREFIX}_{prod_id}", prod_id,
                   {"source_id": prod_id, "name": "Apoquel 16mg", "unit_price": "2.50"}),
    ]
    repo.upsert_canonical("canonical_record", rows,
                          key_cols=("practice_id", "entity_ref"))
    return {"client_id": client_id, "patient_a": patient_a, "patient_b": patient_b,
            "appt_id": appt_id}


def _mark_ready(repo, clinic_id, practice_id, ready: bool):
    repo.create_practice_readiness(PracticeReadiness(
        clinic_id=clinic_id, practice_id=practice_id,
        criteria={}, shadow_ready=ready,
        invisible_adoption_asserted=ready,
    ))


@pytest.fixture()
def clinic_id():
    return f"clinic-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------- #
#  READY practice — data is resolvable, lineage preserved
# --------------------------------------------------------------------------- #
def test_ready_practice_owner_resolvable_by_phone(repo, clinic_id):
    practice_id = f"prac-{uuid.uuid4().hex[:8]}"
    _hydrate_practice(repo, clinic_id, practice_id)
    _mark_ready(repo, clinic_id, practice_id, True)

    ctx = EnvelopeContextProvider(repo, clinic_id)
    assert ctx.is_ready(practice_id) is True

    owner = ctx.resolve_owner_by_phone(practice_id, "555-201-7788")
    assert owner is not None
    assert owner.display_name == "Dana Reyes"
    # lineage preserved: the served owner carries its byte-identical entity_ref.
    assert owner.entity_ref == eref.client_ref("c700")


def test_ready_practice_patients_and_appointments_linked(repo, clinic_id):
    practice_id = f"prac-{uuid.uuid4().hex[:8]}"
    ids = _hydrate_practice(repo, clinic_id, practice_id)
    _mark_ready(repo, clinic_id, practice_id, True)
    ctx = EnvelopeContextProvider(repo, clinic_id)

    owner = ctx.resolve_owner_by_phone(practice_id, "5552017788")
    patients = ctx.patients_for_owner(practice_id, owner)
    assert {p.name for p in patients} == {"Biscuit", "Ghost"}
    # every served patient preserves its patient:ezyvet_p* lineage key.
    assert {p.entity_ref for p in patients} == {
        eref.patient_ref(ids["patient_a"]), eref.patient_ref(ids["patient_b"])}

    biscuit = next(p for p in patients if p.name == "Biscuit")
    appts = ctx.appointments(practice_id, biscuit)
    assert len(appts) == 1
    assert appts[0].start_time == "2026-10-06T14:00"
    assert appts[0].patient_source_id == ids["patient_a"]


def test_ready_practice_refill_context_grounded_in_spine(repo, clinic_id):
    practice_id = f"prac-{uuid.uuid4().hex[:8]}"
    ids = _hydrate_practice(repo, clinic_id, practice_id)
    _mark_ready(repo, clinic_id, practice_id, True)
    ctx = EnvelopeContextProvider(repo, clinic_id)

    rc = ctx.refill_context(practice_id, ids["patient_a"])
    assert rc is not None
    assert rc.patient.entity_ref == eref.patient_ref(ids["patient_a"])
    assert "Apoquel 16mg" in rc.known_products


def test_ready_practice_household_provider_plugs_into_prefetch(repo, clinic_id):
    """The bridge lands into the real 010 prefetch seam: its HouseholdProvider
    is consumable by ``fetch_household_summary`` and honors the greeting-name
    privacy rule."""
    from backend.voice.prefetch import fetch_household_summary

    practice_id = f"prac-{uuid.uuid4().hex[:8]}"
    _hydrate_practice(repo, clinic_id, practice_id)
    _mark_ready(repo, clinic_id, practice_id, True)
    ctx = EnvelopeContextProvider(repo, clinic_id)
    party = eref.client_ref("c700")

    # unverified -> no greeting-name leak, but the household patients resolve.
    unverified = fetch_household_summary(
        party, ctx.household_provider(practice_id, verification_level="none"))
    assert unverified is not None
    assert unverified.display_name_for_greeting is None
    assert {p.name for p in unverified.household_patients} == {"Biscuit"}  # active only

    # soft-confirmed -> greeting name is populated.
    verified = fetch_household_summary(
        party, ctx.household_provider(practice_id, verification_level="soft_confirmed"))
    assert verified.display_name_for_greeting == "Dana Reyes"


# --------------------------------------------------------------------------- #
#  NON-READY practice — every read path is denied (the hard gate)
# --------------------------------------------------------------------------- #
def test_non_ready_practice_denied_explicit_false(repo, clinic_id):
    practice_id = f"prac-{uuid.uuid4().hex[:8]}"
    _hydrate_practice(repo, clinic_id, practice_id)
    _mark_ready(repo, clinic_id, practice_id, False)      # explicitly not ready

    ctx = EnvelopeContextProvider(repo, clinic_id)
    assert ctx.is_ready(practice_id) is False
    for call in (
        lambda: ctx.owners(practice_id),
        lambda: ctx.resolve_owner_by_phone(practice_id, "5552017788"),
        lambda: ctx.patients(practice_id),
        lambda: ctx.appointments(practice_id),
        lambda: ctx.known_products(practice_id),
    ):
        with pytest.raises(PracticeNotReadyError):
            call()


def test_non_ready_practice_denied_no_readiness_row(repo, clinic_id):
    practice_id = f"prac-{uuid.uuid4().hex[:8]}"
    _hydrate_practice(repo, clinic_id, practice_id)
    # NO readiness row created at all -> must be treated as not ready.

    ctx = EnvelopeContextProvider(repo, clinic_id)
    assert ctx.is_ready(practice_id) is False
    with pytest.raises(PracticeNotReadyError):
        ctx.owners(practice_id)


def test_non_ready_household_provider_serves_nothing(repo, clinic_id):
    practice_id = f"prac-{uuid.uuid4().hex[:8]}"
    _hydrate_practice(repo, clinic_id, practice_id)
    _mark_ready(repo, clinic_id, practice_id, False)
    ctx = EnvelopeContextProvider(repo, clinic_id)

    from backend.voice.prefetch import fetch_household_summary
    provider = ctx.household_provider(practice_id, verification_level="soft_confirmed")
    assert fetch_household_summary(eref.client_ref("c700"), provider) is None
