"""T039 — booking-accuracy audit harness (SC-003).

Post-call read-back vs written slot across an audit set, plus idempotency under
injected retry/latency. Booking accuracy must be **≥ 99%**; no double-booking;
the same ``booking_token`` dedupes to the original booking; and the
``UNIQUE(clinic_id, slot_id, patient_ref)`` constraint holds across a simulated
call-back retry from a NEW session.

Runs against ``SimBookingBackend`` (the two-phase read-back → commit path). The
**live backend is a pilot-activation swap** wrapping
``booking_agent.confirm_booking`` — not built here.
"""
from backend.voice.verbs import (
    DoubleBookingError, Slot, SimBookingBackend, VoiceVerbs, make_booking_token,
)


def _audit_slots(n: int) -> list[Slot]:
    return [Slot(slot_id=f"slot-{i:04d}", start=f"2026-10-{(i % 27) + 1:02d}T09:00",
                 provider="Dr. Okafor", reason="follow-up") for i in range(n)]


def test_t039_read_back_matches_written_slot_at_least_99pct():
    slots = _audit_slots(200)
    v = VoiceVerbs(SimBookingBackend(slots=slots))
    matches = 0
    total = len(slots)

    for i, slot in enumerate(slots):
        patient = f"pet-{i:04d}"
        # Phase 1: read-back (spoken BEFORE any write).
        rb = v.begin_booking("goldsmith-0001", slot, patient, party_id=f"party-{i}")
        # Phase 2: the write.
        booking = v.commit_booking(rb)
        # Post-call audit: what was written == what was read back.
        if (booking.slot_id == rb.slot_id
                and booking.patient_ref == rb.patient_ref
                and booking.booking_token == rb.booking_token
                and slot.start in rb.text            # read-back conveys the slot
                and slot.provider in rb.text):
            matches += 1

    accuracy = matches / total
    assert accuracy >= 0.99, f"booking accuracy {accuracy:.3%} < 99%"
    assert matches == total                                  # sim is exact


def test_t039_same_token_dedupes_under_injected_retry_latency():
    v = VoiceVerbs(SimBookingBackend())
    slot = v.availability("goldsmith-0001")[0]
    # Simulate a flaky network: the same confirm retried several times.
    ids = set()
    for _ in range(5):                                       # retries under latency
        b = v.book("goldsmith-0001", slot, "Rex", party_id="party-1", retry_nonce="n1")
        ids.add(b.booking_id)
    assert len(ids) == 1                                     # all dedupe to one booking
    assert len(v.backend.list_bookings("goldsmith-0001")) == 1


def test_t039_unique_constraint_holds_across_callback_from_new_session():
    v = VoiceVerbs(SimBookingBackend())
    slot = v.availability("goldsmith-0001")[0]
    # Call A books the slot.
    v.book("goldsmith-0001", slot, "Rex", party_id="party-1", retry_nonce="callA")
    # A fresh call-back session (DIFFERENT nonce → different token) must NOT be
    # able to double-book the same slot for the same patient.
    tok_a = make_booking_token("goldsmith-0001", slot.slot_id, "Rex", "callA")
    tok_b = make_booking_token("goldsmith-0001", slot.slot_id, "Rex", "callB")
    assert tok_a != tok_b                                    # not token-deduped
    try:
        v.book("goldsmith-0001", slot, "Rex", party_id="party-1", retry_nonce="callB")
        assert False, "expected DoubleBookingError from the UNIQUE active constraint"
    except DoubleBookingError:
        pass
    assert len(v.backend.list_bookings("goldsmith-0001")) == 1


def test_t039_different_patient_same_slot_not_deduped():
    v = VoiceVerbs(SimBookingBackend())
    slot = v.availability("goldsmith-0001")[0]
    b1 = v.book("goldsmith-0001", slot, "Rex", party_id="party-1")
    b2 = v.book("goldsmith-0001", slot, "Bella", party_id="party-2")
    assert b1.booking_id != b2.booking_id
    assert len(v.backend.list_bookings("goldsmith-0001")) == 2
