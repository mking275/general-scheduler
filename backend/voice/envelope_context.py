"""Feature 009+010 — envelope→voice context bridge (the seam glue).

**The seam problem.** Spec 009 hydrates a practice's canonical entities into the
generic ``canonical_record`` spine (categories ``client``, ``patient``,
``appointment``, ``product_service``, …) plus the typed financial/inventory
tables, each row carrying its ``entity_ref``/``source_id`` lineage. Spec 010's
voice session, however, resolves practice data through *other* sources — slots
from the booking backend, caller/household identity from the 011 relationship
tables (``household`` / ``patient_household_link`` / …, populated by a separate
``migrate_households`` staging read). **Nothing read a shadow-ready practice's
009-hydrated owners / patients / appointments back into a voice session.** This
module is that missing read path.

**Scope (glue only).** A single envelope-backed read path — no new verbs, no
delta sync, no cutover, no change to 009's pipeline or 010's protocol logic.
It reads the 009 spine through the ``OnboardingRepository`` and projects the
subset a voice session context needs (owners, patients, appointments, and the
refill-relevant product/drug surface), each projection preserving the source
``entity_ref`` lineage so a served record still resolves back to its source row.

**The gate (non-negotiable).** Every data-serving method first asserts the
practice is ``shadow_ready`` via ``PracticeReadiness``. A practice that has not
cleared the 009 readiness bar (no readiness row, or ``shadow_ready = False``)
is **denied** — its hydrated data is never served into a voice session. The
on-ramp still ends at ``shadow_ready``: this bridge only *reads* an
already-ready practice; it advances nothing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# The canonical categories this bridge projects for a voice session.
_CAT_CLIENT = "client"
_CAT_PATIENT = "patient"
_CAT_APPOINTMENT = "appointment"
_CAT_PRODUCT = "product_service"


class PracticeNotReadyError(PermissionError):
    """A voice session requested practice data before the practice cleared the
    009 ``shadow_ready`` bar. The bridge refuses to serve un-ready data."""


def _digits(raw: Any) -> str:
    return re.sub(r"\D", "", str(raw or ""))


# --------------------------------------------------------------------------- #
#  Lineage-preserving projections — every view carries its source entity_ref.
# --------------------------------------------------------------------------- #
@dataclass
class OwnerView:
    entity_ref: str                        # client:ezyvet_c* — lineage preserved
    source_id: str
    display_name: str
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class PatientView:
    entity_ref: str                        # patient:ezyvet_p* — lineage preserved
    source_id: str
    name: Optional[str] = None
    species: Optional[str] = None
    breed: Optional[str] = None
    status: Optional[str] = None
    owner_source_id: Optional[str] = None   # -> OwnerView.source_id


@dataclass
class AppointmentView:
    entity_ref: str                        # appointment:* — lineage preserved
    source_id: str
    patient_source_id: Optional[str] = None
    provider_source_id: Optional[str] = None
    start_time: Optional[str] = None
    appointment_type: Optional[str] = None


@dataclass
class RefillContext:
    """The refill-relevant surface for a patient: the patient itself plus the
    drug/product names the practice actually carries (the only names a refill
    draft may be grounded against — never model priors)."""
    patient: PatientView
    known_products: list[str] = field(default_factory=list)


class EnvelopeContextProvider:
    """Envelope-backed voice session context for a single clinic.

    ``repo`` is a 009 ``OnboardingRepository`` (or any object exposing
    ``get_practice_readiness(practice_id)`` and
    ``list_canonical_records(practice_id, category=...)``). The provider is
    read-only and stateless beyond the injected repo.
    """

    def __init__(self, repo, clinic_id: str):
        self.repo = repo
        self.clinic_id = clinic_id

    # ------------------------------------------------------------------ #
    #  The readiness gate — the one choke point every read passes through.
    # ------------------------------------------------------------------ #
    def is_ready(self, practice_id: str) -> bool:
        """True iff the practice has a ``PracticeReadiness`` row with
        ``shadow_ready`` set. No row -> not ready."""
        row = self.repo.get_practice_readiness(practice_id)
        return bool(row and row.get("shadow_ready"))

    def _require_ready(self, practice_id: str) -> None:
        if not self.is_ready(practice_id):
            raise PracticeNotReadyError(
                f"practice {practice_id!r} is not shadow_ready; its onboarding "
                f"data must not be served into a voice session")

    def _records(self, practice_id: str, category: str) -> list[dict]:
        """Gated read of one canonical category for a practice."""
        self._require_ready(practice_id)
        return self.repo.list_canonical_records(practice_id, category=category)

    # ------------------------------------------------------------------ #
    #  Owners (client category)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _owner_view(rec: dict) -> OwnerView:
        p = rec.get("payload") or {}
        name = " ".join(x for x in (p.get("first_name"), p.get("last_name")) if x).strip()
        return OwnerView(
            entity_ref=rec["entity_ref"],
            source_id=str(p.get("source_id") or rec.get("source_id") or ""),
            display_name=name,
            phone=p.get("phone"),
            email=p.get("email"),
        )

    def owners(self, practice_id: str) -> list[OwnerView]:
        return [self._owner_view(r) for r in self._records(practice_id, _CAT_CLIENT)]

    def resolve_owner_by_phone(self, practice_id: str,
                               phone: str) -> Optional[OwnerView]:
        """Resolve an inbound number to the owner on record (digit-normalized).
        The party-resolution entry point for a voice session — ``None`` when no
        client matches (Vera then stays in unverified scope, no name leak)."""
        want = _digits(phone)
        if not want:
            return None
        for owner in self.owners(practice_id):
            if owner.phone and _digits(owner.phone) == want:
                return owner
        return None

    # ------------------------------------------------------------------ #
    #  Patients (patient category), linked to their owner
    # ------------------------------------------------------------------ #
    @staticmethod
    def _patient_view(rec: dict) -> PatientView:
        p = rec.get("payload") or {}
        return PatientView(
            entity_ref=rec["entity_ref"],
            source_id=str(p.get("source_id") or rec.get("source_id") or ""),
            name=p.get("name"),
            species=p.get("species"),
            breed=p.get("breed"),
            status=p.get("status"),
            owner_source_id=(str(p["client_source_id"])
                             if p.get("client_source_id") is not None else None),
        )

    def patients(self, practice_id: str) -> list[PatientView]:
        return [self._patient_view(r) for r in self._records(practice_id, _CAT_PATIENT)]

    def patients_for_owner(self, practice_id: str,
                           owner: OwnerView | str) -> list[PatientView]:
        """The patients linked to an owner (via ``patient.client_source_id`` ->
        ``client.source_id``). Accepts an ``OwnerView`` or a client source id."""
        owner_source_id = owner.source_id if isinstance(owner, OwnerView) else str(owner)
        return [pt for pt in self.patients(practice_id)
                if pt.owner_source_id == owner_source_id]

    # ------------------------------------------------------------------ #
    #  Appointments (appointment category)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _appointment_view(rec: dict) -> AppointmentView:
        p = rec.get("payload") or {}
        return AppointmentView(
            entity_ref=rec["entity_ref"],
            source_id=str(p.get("source_id") or rec.get("source_id") or ""),
            patient_source_id=(str(p["patient_source_id"])
                               if p.get("patient_source_id") is not None else None),
            provider_source_id=(str(p["provider_source_id"])
                                if p.get("provider_source_id") is not None else None),
            start_time=p.get("start_time"),
            appointment_type=p.get("appointment_type"),
        )

    def appointments(self, practice_id: str,
                     patient: Optional[PatientView | str] = None) -> list[AppointmentView]:
        """All appointments for the practice, or (when ``patient`` is given) only
        those for that patient (matched on the patient's source id)."""
        views = [self._appointment_view(r)
                 for r in self._records(practice_id, _CAT_APPOINTMENT)]
        if patient is None:
            return views
        patient_source_id = patient.source_id if isinstance(patient, PatientView) else str(patient)
        return [a for a in views if a.patient_source_id == patient_source_id]

    # ------------------------------------------------------------------ #
    #  Refill-relevant surface
    # ------------------------------------------------------------------ #
    def known_products(self, practice_id: str) -> list[str]:
        """Product/service names the practice carries — the only drug names a
        refill draft may be grounded against."""
        names: list[str] = []
        for r in self._records(practice_id, _CAT_PRODUCT):
            name = (r.get("payload") or {}).get("name")
            if name:
                names.append(str(name))
        return names

    def refill_context(self, practice_id: str,
                       patient: PatientView | str) -> Optional[RefillContext]:
        """The refill-relevant context for a patient: the patient view plus the
        practice's known product/drug names. ``None`` when the patient is not
        found in the shadow-ready spine."""
        patient_source_id = patient.source_id if isinstance(patient, PatientView) else str(patient)
        match = next((pt for pt in self.patients(practice_id)
                      if pt.source_id == patient_source_id), None)
        if match is None:
            return None
        return RefillContext(patient=match,
                             known_products=self.known_products(practice_id))

    # ------------------------------------------------------------------ #
    #  Voice-prefetch seam — a HouseholdProvider backed by the 009 spine.
    # ------------------------------------------------------------------ #
    def household_provider(self, practice_id: str, *,
                           audience: str = "caller",
                           verification_level: str = "none") -> Callable[[str], Optional[Any]]:
        """Return a ``HouseholdProvider`` (``Callable[[party_id], Optional[
        HouseholdSummary]]``) the 010 ``Prefetcher`` plugs in unchanged — but
        sourced from the 009 canonical spine instead of the 011 tables, and
        gated on ``shadow_ready``. The greeting name is populated only for a
        soft-confirmed/strong caller (no name leak); an un-ready practice yields
        a provider that always returns ``None``."""
        # Lazy import keeps backend.voice.envelope_context free of an import-time
        # cycle with prefetch and mirrors 011's one-way-seam convention.
        from backend.voice.prefetch import HouseholdSummary, PatientRef

        def provider(party_id: str) -> Optional[Any]:
            if not self.is_ready(practice_id) or not party_id:
                return None
            owner = next((o for o in self.owners(practice_id)
                          if o.entity_ref == party_id or o.source_id == str(party_id)),
                         None)
            if owner is None:
                return None
            patients = [
                PatientRef(name=pt.name, species=pt.species)
                for pt in self.patients_for_owner(practice_id, owner)
                if (pt.status or "active") == "active"
            ]
            greeting = (owner.display_name
                        if verification_level in ("soft_confirmed", "strong") else None)
            return HouseholdSummary(
                party_id=owner.entity_ref,
                display_name_for_greeting=greeting,
                household_patients=patients,
                last_visit_summary_line=None,
                audience_scope=audience,
                verification_level=verification_level,
            )

        return provider
