"""Feature 010 — Vera Voice: T023/T024/T028 verbs (contract B5, Phase D).

Voice is a new **intake channel** into the existing Intake -> Match -> Solve ->
Dispatch pipeline — **no bypass writes**. The verbs here carry a stable
``booking_token`` into the booking pipeline and enforce, below the model:

  * **Read-back before write** (T023): a booking is a two-phase op —
    ``begin_booking`` produces the read-back summary (date / time / provider /
    reason); the write only happens on ``commit_booking``. An abort between the
    two (e.g. a mid-booking emergency, T031) leaves **zero rows**.
  * **Idempotency** (T023 / FR-010): ``booking_token = hash(clinic_id, slot_id,
    patient_ref, retry_nonce)`` dedupes a retry to the original booking; a
    ``UNIQUE(clinic_id, slot_id, patient_ref)`` active-booking constraint rejects
    a second active booking of the same slot for the same patient (even from a
    fresh call-back session). A *different* patient booking the same slot is
    **not** deduped.
  * **Unverified scope** (T024 / FR-006): unverified callers are limited to
    ``availability`` + ``intake_capture``; they can never read or act on an
    existing client's records.
  * **Refill draft** (T028 / FR-022/023): ``refill_draft`` writes a
    ``refill_request_draft`` (``status='draft_vet_review'``) DIRECTLY and has
    **no code path** to ``PrescriptionAgent.request_refill`` (the auto-approve
    branch). The autonomy gate rejects any ``auto_approved`` disposition.

The booking pipeline is injected via a ``BookingBackend`` (like wave-1's
``BaseSimAdapter``) so the whole path runs in sim with the FR-010 guarantees
provable and zero live writes; the live backend wraps
``booking_agent.confirm_booking`` at pilot activation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, time as _time
from typing import Any, Optional, Protocol

from backend.models import RefillRequestDraft
from backend.voice.autonomy_gate import AutonomyGate

# Verbs an unverified caller may use — everything else needs client_verified.
UNVERIFIED_ALLOWED = frozenset({"availability", "intake_capture"})


class UnverifiedScopeError(PermissionError):
    """Raised when an unverified caller invokes a verb outside their scope."""


class DoubleBookingError(RuntimeError):
    """Raised on a second active booking of the same slot for the same patient."""


# --------------------------------------------------------------------------- #
#  booking_token — stable across retries AND across a fresh call-back session
# --------------------------------------------------------------------------- #
def make_booking_token(clinic_id: str, slot_id: str, patient_ref: str,
                       retry_nonce: str = "") -> str:
    """``hash(clinic_id, slot_id, patient_ref, retry_nonce)``. Deliberately NOT
    keyed on ``call_session_id`` — that would misdedupe a second patient booked
    into the same slot in one call, and fail to dedupe a caller retrying from a
    new session (data-model, Booking idempotency)."""
    raw = f"{clinic_id}|{slot_id}|{patient_ref}|{retry_nonce}"
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Slot:
    slot_id: str
    start: str
    provider: str
    reason: str = ""


@dataclass
class Booking:
    booking_id: str
    booking_token: str
    clinic_id: str
    slot_id: str
    patient_ref: str
    party_id: Optional[str]
    status: str = "active"
    pipeline_stages: list = field(default_factory=list)
    read_back: Optional[str] = None


@dataclass
class ReadBack:
    """The read-back summary spoken BEFORE any write (T023)."""
    text: str
    clinic_id: str
    slot_id: str
    patient_ref: str
    party_id: Optional[str]
    booking_token: str


@dataclass
class NewClientDraft:
    party_id: Optional[str]
    caller_name: str
    callback_number: str
    reason: str


# --------------------------------------------------------------------------- #
#  Booking backend (pipeline seam) — sim impl enforces the FR-010 guarantees
# --------------------------------------------------------------------------- #
class BookingBackend(Protocol):
    def create_booking(self, clinic_id: str, slot_id: str, patient_ref: str,
                        party_id: Optional[str], booking_token: str) -> Booking: ...
    def list_bookings(self, clinic_id: str) -> list[Booking]: ...
    def get_slots(self, clinic_id: str) -> list[Slot]: ...
    def cancel_booking(self, booking_id: str) -> None: ...


class SimBookingBackend:
    """In-memory stand-in for the Intake->Match->Solve->Dispatch pipeline. The
    live backend wraps ``booking_agent.confirm_booking`` (pilot activation)."""

    PIPELINE = ["intake", "match", "solve", "dispatch"]

    def __init__(self, slots: Optional[list[Slot]] = None):
        self._slots = slots or [
            Slot("slot-tue-1400", "2026-10-06T14:00", "Dr. Okafor", "follow-up"),
            Slot("slot-wed-0900", "2026-10-07T09:00", "Dr. Goldsmith", "checkup"),
        ]
        self._by_token: dict[str, Booking] = {}
        self._active_key: dict[tuple, str] = {}     # (clinic,slot,patient) -> token
        self._seq = 0

    def get_slots(self, clinic_id: str) -> list[Slot]:
        return list(self._slots)

    def create_booking(self, clinic_id, slot_id, patient_ref, party_id, booking_token) -> Booking:
        # 1. Idempotent dedupe: same token -> return the original booking.
        if booking_token in self._by_token:
            return self._by_token[booking_token]
        # 2. UNIQUE(clinic_id, slot_id, patient_ref) on active bookings.
        key = (clinic_id, slot_id, patient_ref)
        if key in self._active_key:
            raise DoubleBookingError(
                f"active booking already exists for slot {slot_id} / patient {patient_ref}")
        # 3. Flow through the pipeline stages and commit.
        self._seq += 1
        booking = Booking(
            booking_id=f"bk-{self._seq}", booking_token=booking_token,
            clinic_id=clinic_id, slot_id=slot_id, patient_ref=patient_ref,
            party_id=party_id, status="active", pipeline_stages=list(self.PIPELINE),
        )
        self._by_token[booking_token] = booking
        self._active_key[key] = booking_token
        return booking

    def list_bookings(self, clinic_id: str) -> list[Booking]:
        return [b for b in self._by_token.values()
                if b.clinic_id == clinic_id and b.status == "active"]

    def cancel_booking(self, booking_id: str) -> None:
        for key, token in list(self._active_key.items()):
            b = self._by_token[token]
            if b.booking_id == booking_id:
                b.status = "cancelled"
                del self._active_key[key]


# --------------------------------------------------------------------------- #
#  The verb layer
# --------------------------------------------------------------------------- #
class VoiceVerbs:
    def __init__(self, backend: BookingBackend, repo=None,
                 gate: Optional[AutonomyGate] = None):
        self.backend = backend
        self.repo = repo
        self.gate = gate or AutonomyGate()

    # --- scope enforcement (T024) --------------------------------------
    @staticmethod
    def _is_verified(audience_scope: str) -> bool:
        return audience_scope == "client_verified"

    def _require_scope(self, verb: str, audience_scope: str) -> None:
        if verb in UNVERIFIED_ALLOWED:
            return
        if not self._is_verified(audience_scope):
            raise UnverifiedScopeError(
                f"'{verb}' requires a verified caller; unverified callers are "
                f"limited to {sorted(UNVERIFIED_ALLOWED)} (FR-006)")

    # --- availability (unverified OK) ----------------------------------
    def availability(self, clinic_id: str,
                     audience_scope: str = "caller_unverified") -> list[Slot]:
        self._require_scope("availability", audience_scope)
        return self.backend.get_slots(clinic_id)

    # --- intake capture (unverified OK) --------------------------------
    def intake_capture(self, caller_name: str, callback_number: str, reason: str,
                       audience_scope: str = "caller_unverified") -> NewClientDraft:
        self._require_scope("intake_capture", audience_scope)
        return NewClientDraft(party_id=None, caller_name=caller_name,
                              callback_number=callback_number, reason=reason)

    # --- booking: two-phase (read-back -> commit) ----------------------
    def begin_booking(self, clinic_id: str, slot: Slot, patient_ref: str,
                      party_id: Optional[str], audience_scope: str = "client_verified",
                      retry_nonce: str = "") -> ReadBack:
        """Phase 1 — produce the read-back summary. NO write happens here."""
        self._require_scope("book", audience_scope)
        token = make_booking_token(clinic_id, slot.slot_id, patient_ref, retry_nonce)
        text = (f"I'll book {patient_ref} for {slot.reason or 'a visit'} on "
                f"{slot.start} with {slot.provider}. Shall I confirm?")
        return ReadBack(text=text, clinic_id=clinic_id, slot_id=slot.slot_id,
                        patient_ref=patient_ref, party_id=party_id, booking_token=token)

    def commit_booking(self, read_back: ReadBack,
                       audience_scope: str = "client_verified") -> Booking:
        """Phase 2 — the actual write, gate-checked + idempotent. Only reached
        after a read-back was produced and (in the dialog) confirmed."""
        self._require_scope("book", audience_scope)
        # Gate authorizes the write (non-clinical do-class).
        decision = self.gate.classify([{"name": "book", "ladder": "do", "is_write": True}])
        from backend.models import GateDecision
        if decision != GateDecision.DO:
            raise UnverifiedScopeError(f"booking write not authorized: {decision}")
        booking = self.backend.create_booking(
            read_back.clinic_id, read_back.slot_id, read_back.patient_ref,
            read_back.party_id, read_back.booking_token)
        booking.read_back = read_back.text
        return booking

    def book(self, clinic_id: str, slot: Slot, patient_ref: str,
             party_id: Optional[str], audience_scope: str = "client_verified",
             retry_nonce: str = "") -> Booking:
        """Convenience: read-back then commit (idempotent)."""
        rb = self.begin_booking(clinic_id, slot, patient_ref, party_id,
                                audience_scope, retry_nonce)
        return self.commit_booking(rb, audience_scope)

    def reschedule(self, clinic_id: str, old_booking_id: str, new_slot: Slot,
                   patient_ref: str, party_id: Optional[str],
                   audience_scope: str = "client_verified", retry_nonce: str = "") -> Booking:
        """Cancel + confirm through the pipeline (read-back still applies)."""
        self._require_scope("reschedule", audience_scope)
        self.backend.cancel_booking(old_booking_id)
        return self.book(clinic_id, new_slot, patient_ref, party_id,
                         audience_scope, retry_nonce)

    # --- refill draft (T028) — NEVER auto-approve, NEVER request_refill ---
    def refill_draft(self, clinic_id: str, call_session_id: str, party_id: str,
                     patient_ref: str, drug_name_asserted: str,
                     refills_remaining_at_capture: Optional[int] = None,
                     disposition: Optional[str] = None,
                     audience_scope: str = "client_verified") -> RefillRequestDraft:
        """Capture a refill request as a ``draft_vet_review`` row. A refill is a
        verified-caller action; ``refills_remaining`` is recorded for the vet but
        does NOT gate approval. There is no path to ``request_refill``."""
        self._require_scope("refill_draft", audience_scope)
        # Gate guard: reject any auto-approve disposition on voice (raises).
        self.gate.guard_no_auto_approve(disposition)
        # The refill is a clinical 'propose' -> a draft post-call artifact, never
        # a live 'do'. Confirm the gate never authorizes an autonomous approval.
        from backend.voice.autonomy_gate import GateContext
        from backend.models import GateDecision
        gr = self.gate.classify_full(GateContext(
            verb="refill", ladder="propose", disposition=disposition, is_write=True,
            audience_scope=audience_scope))
        assert gr.persisted_decision == GateDecision.PROPOSE
        assert gr.live_action == "none" and gr.post_call_artifact == "draft"

        draft = RefillRequestDraft(
            call_session_id=call_session_id, party_id=party_id,
            patient_ref=patient_ref, drug_name_asserted=drug_name_asserted,
            refills_remaining_at_capture=refills_remaining_at_capture,
            # status is a Literal["draft_vet_review"] — auto_approved is unrepresentable.
        )
        if self.repo is not None:
            self.repo.create_refill_draft(draft)      # DB CHECK backs the guard
        return draft

    # --- info_answer (T041) — grounded ONLY in clinic_voice_config ------
    def info_answer(self, config: dict, topic: str,
                    day: Optional[str] = None) -> "InfoAnswer":
        """Answer an informational question (hours / prep / pricing) drawn
        **only** from ``clinic_voice_config`` — never from model priors. When the
        config has no value, Vera **declines rather than inventing** one and
        offers to escalate to a person (FR-014)."""
        return info_answer(config, topic, day=day)


# --------------------------------------------------------------------------- #
#  T041 — informational-answer grounding (FR-014)
# --------------------------------------------------------------------------- #
@dataclass
class InfoAnswer:
    answered: bool
    text: str
    grounded_in: Optional[str]        # the clinic_voice_config key path, or None
    declined: bool = False
    offer_escalation: bool = False
    invented: bool = False            # INVARIANT: always False (never fabricated)


_DECLINE_TEXT = (
    "I don't have that information on hand, and I don't want to guess. I can have "
    "a member of the team follow up with you on that — would you like me to do that?"
)

# Question-topic keyword groups → the config path they may ground on.
_HOURS_WORDS = ("hour", "open", "close", "closing", "opening", "when are you")
_PRICE_WORDS = ("price", "cost", "how much", "fee", "charge", "pricing")


def _fmt_hours(hours: dict, day: Optional[str]) -> Optional[tuple[str, str]]:
    """Return (text, grounded_in) for the requested day, or None if unknown.
    A day present-but-null in config is a grounded 'closed' answer."""
    if day is None:
        parts = []
        for d, v in hours.items():
            if v:
                parts.append(f"{d.capitalize()} {v['open']}–{v['close']}")
            else:
                parts.append(f"{d.capitalize()} closed")
        return ("Our regular hours are: " + "; ".join(parts) + ".", "hours")
    key = day.lower()
    if key not in hours:
        return None                                  # not in config → decline
    v = hours[key]
    if not v:
        return (f"We're closed on {day.capitalize()}.", f"hours.{key}")
    return (f"On {day.capitalize()} we're open {v['open']} to {v['close']}.",
            f"hours.{key}")


def info_answer(config: dict, topic: str, day: Optional[str] = None) -> InfoAnswer:
    config = config or {}
    t = (topic or "").lower().strip()

    def decline(_probe: str) -> InfoAnswer:
        return InfoAnswer(answered=False, text=_DECLINE_TEXT, grounded_in=None,
                          declined=True, offer_escalation=True, invented=False)

    # 1. Hours — ONLY from config['hours'].
    if any(w in t for w in _HOURS_WORDS):
        hours = config.get("hours") or {}
        if not hours:
            return decline(t)
        got = _fmt_hours(hours, day)
        if got is None:
            return decline(t)
        text, path = got
        return InfoAnswer(True, text, grounded_in=path)

    # 2. Pricing — ONLY if config actually carries it; NEVER invent a price.
    if any(w in t for w in _PRICE_WORDS):
        pricing = config.get("pricing") or (config.get("info") or {}).get("pricing")
        if pricing:
            return InfoAnswer(True, str(pricing), grounded_in="pricing")
        return decline(t)                            # goldsmith omits pricing by design

    # 3. Generic info keys (parking, prep, …) — ONLY from config['info'].
    info = config.get("info") or {}
    for key, val in info.items():
        norm_key = key.lower().replace("_", " ")
        if val and (key.lower() in t or norm_key in t
                    or any(tok in t for tok in norm_key.split())):
            return InfoAnswer(True, str(val), grounded_in=f"info.{key}")

    # 4. Nothing in config grounds this → decline + offer to escalate.
    return decline(t)


# --------------------------------------------------------------------------- #
#  T042 — after-hours boundary gate (FR-004)
# --------------------------------------------------------------------------- #
def _parse_hhmm(s: str) -> _time:
    hh, mm = str(s).split(":")
    return _time(int(hh), int(mm))


def _in_wrapping_window(tod: _time, start: str, end: str) -> bool:
    """Is ``tod`` inside [start, end)? A ``start > end`` window wraps past
    midnight (e.g. 18:00→08:00 covers the whole night)."""
    s, e = _parse_hhmm(start), _parse_hhmm(end)
    if s <= e:
        return s <= tod < e
    return tod >= s or tod < e                       # wraps midnight


# Mon..Sun index → the config sub-window key that applies to weekday evenings.
_WEEKDAYS = range(0, 5)   # Mon–Fri
_SATURDAY = 5
_SUNDAY = 6


def after_hours_admits(window: dict, at: datetime) -> bool:
    """App-side gate (FR-004): does the after-hours voice line handle a call at
    ``at``? The boundary is read entirely from ``clinic_voice_config.
    after_hours_window`` — never hard-coded. Handles overnight windows that span
    midnight and an all-day-Sunday flag.

    Returns True when the call is OUTSIDE regular hours (Vera handles it),
    False when it is within business hours (not routed to Vera)."""
    window = window or {}
    dow, tod = at.weekday(), at.time()

    if dow == _SUNDAY and window.get("sunday_all_day"):
        return True
    if dow == _SATURDAY and "saturday" in window:
        w = window["saturday"]
        if _in_wrapping_window(tod, w["start"], w["end"]):
            return True
    if dow in _WEEKDAYS and "weekday_evening" in window:
        w = window["weekday_evening"]
        if _in_wrapping_window(tod, w["start"], w["end"]):
            return True
    return False


class AfterHoursGate:
    """Runtime admission gate around ``after_hours_admits`` (the gate MUST exist
    and be tested even when the pilot line is after-hours-only at the telephony
    layer — T042)."""

    def __init__(self, after_hours_window: dict):
        self.window = after_hours_window or {}

    def admits(self, at: datetime) -> bool:
        return after_hours_admits(self.window, at)

    def route(self, at: datetime) -> str:
        """``vera`` when the call is after-hours; ``passthrough`` (day office /
        front desk) otherwise. Vera never handles a daytime call in 3a/3b."""
        return "vera" if self.admits(at) else "passthrough"
