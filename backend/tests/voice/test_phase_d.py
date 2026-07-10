"""Phase D — verbs + prefetch/hold + autonomy gate + refill (T023..T028).

Everything runs in sim (injected booking backend + household provider); zero
live writes / network calls.
"""
import pytest

from backend.models import CallSession, GateDecision


# =========================================================================== #
#  T023 — book / reschedule / availability: read-back, idempotent, no bypass
# =========================================================================== #
def _verbs():
    from backend.voice.verbs import VoiceVerbs, SimBookingBackend
    return VoiceVerbs(SimBookingBackend())


def test_t023_booking_flows_pipeline_and_appears_in_schedule():
    from backend.voice.verbs import SimBookingBackend
    v = _verbs()
    slots = v.availability("goldsmith-0001")
    slot = slots[0]
    rb = v.begin_booking("goldsmith-0001", slot, "Rex", party_id="party-1")
    assert "Rex" in rb.text and slot.provider in rb.text       # read-back BEFORE write
    b = v.commit_booking(rb)
    assert b.pipeline_stages == SimBookingBackend.PIPELINE      # Intake->Match->Solve->Dispatch
    assert b.read_back == rb.text
    # appears in the schedule
    schedule = v.backend.list_bookings("goldsmith-0001")
    assert any(x.booking_id == b.booking_id for x in schedule)


def test_t023_same_token_dedupes_no_double_write():
    v = _verbs()
    slot = v.availability("goldsmith-0001")[0]
    b1 = v.book("goldsmith-0001", slot, "Rex", party_id="party-1", retry_nonce="n1")
    b2 = v.book("goldsmith-0001", slot, "Rex", party_id="party-1", retry_nonce="n1")
    assert b1.booking_id == b2.booking_id                       # same booking returned
    assert len(v.backend.list_bookings("goldsmith-0001")) == 1  # no double-write


def test_t023_unique_active_constraint_rejects_second_same_patient_slot():
    # A fresh call-back session (DIFFERENT retry_nonce -> different token) still
    # cannot double-book the same slot for the same patient.
    from backend.voice.verbs import DoubleBookingError
    v = _verbs()
    slot = v.availability("goldsmith-0001")[0]
    v.book("goldsmith-0001", slot, "Rex", party_id="party-1", retry_nonce="call-A")
    with pytest.raises(DoubleBookingError):
        v.book("goldsmith-0001", slot, "Rex", party_id="party-1", retry_nonce="call-B")


def test_t023_different_patient_same_slot_not_deduped():
    v = _verbs()
    slot = v.availability("goldsmith-0001")[0]
    b1 = v.book("goldsmith-0001", slot, "Rex", party_id="party-1")
    b2 = v.book("goldsmith-0001", slot, "Bella", party_id="party-2")
    assert b1.booking_id != b2.booking_id                       # NOT deduped
    assert len(v.backend.list_bookings("goldsmith-0001")) == 2


def test_t023_reschedule_cancels_then_rebooks():
    v = _verbs()
    slots = v.availability("goldsmith-0001")
    b1 = v.book("goldsmith-0001", slots[0], "Rex", party_id="party-1")
    b2 = v.reschedule("goldsmith-0001", b1.booking_id, slots[1], "Rex", party_id="party-1")
    active = v.backend.list_bookings("goldsmith-0001")
    assert len(active) == 1 and active[0].booking_id == b2.booking_id


# =========================================================================== #
#  T024 — unverified-scope enforcement
# =========================================================================== #
def test_t024_unverified_book_rejected_availability_and_intake_ok():
    from backend.voice.verbs import UnverifiedScopeError
    v = _verbs()
    slot = v.availability("goldsmith-0001", audience_scope="caller_unverified")[0]
    assert slot is not None                                     # availability() OK unverified

    # intake_capture() OK unverified
    draft = v.intake_capture("Jane", "+15550001111", "new puppy",
                             audience_scope="caller_unverified")
    assert draft.caller_name == "Jane"

    # book() against an existing-client record -> rejected
    with pytest.raises(UnverifiedScopeError):
        v.book("goldsmith-0001", slot, "Rex", party_id="party-1",
               audience_scope="caller_unverified")


# =========================================================================== #
#  T025 — prefetch_context (+ VP-4a stub None -> unverified, no name leak)
# =========================================================================== #
def test_t025_prefetch_warms_cache_no_blocking_lookup_next_turn():
    from backend.voice.prefetch import Prefetcher
    slots = [{"slot": "tue-2pm"}]
    cfg = {"clinic_id": "goldsmith-0001"}
    p = Prefetcher(availability_fn=lambda c: slots, config_fn=lambda c: cfg)
    cache = p.prefetch_context("goldsmith-0001", audience_scope="caller_unverified")
    assert cache.is_warm()
    lookups_after_prefetch = p.lookups
    # next turn reads from cache — NO backend lookup
    assert p.read_slots(cache) == slots
    assert p.read_config(cache) == cfg
    assert p.lookups == lookups_after_prefetch                  # unchanged


def test_t025_vp4a_stub_none_proceeds_unverified_no_greeting_leak():
    from backend.voice.prefetch import Prefetcher, fetch_household_summary
    # VP-4a absent -> stub returns None (whole object).
    assert fetch_household_summary("party-1", provider=None) is None
    p = Prefetcher(availability_fn=lambda c: [], config_fn=lambda c: {},
                   household_provider=None)
    cache = p.prefetch_context("goldsmith-0001", party_id="party-1",
                               audience_scope="caller_unverified")
    assert cache.household_summary is None                      # no greeting name available


def test_t025_verified_scope_populates_household_summary():
    from backend.voice.prefetch import Prefetcher, HouseholdSummary, PatientRef
    def provider(pid):
        return HouseholdSummary(party_id=pid, display_name_for_greeting="Mrs. Alvarez",
                                household_patients=[PatientRef("Rex", "dog")],
                                audience_scope="client_verified", verification_level="soft_confirmed")
    p = Prefetcher(availability_fn=lambda c: [], config_fn=lambda c: {},
                   household_provider=provider)
    cache = p.prefetch_context("goldsmith-0001", party_id="party-1",
                               audience_scope="client_verified")
    assert cache.household_summary.display_name_for_greeting == "Mrs. Alvarez"


# =========================================================================== #
#  T026 — bounded hold on cache miss (no dead air)
# =========================================================================== #
def test_t026_hold_emits_filler_and_returns_within_budget():
    from backend.voice.prefetch import Prefetcher
    p = Prefetcher(availability_fn=lambda c: [], config_fn=lambda c: {},
                   max_hold_ms=8000, filler_script="One moment please.")
    res = p.hold(lambda: {"slots": ["tue-2pm"]})
    assert res.filler_emitted is True and res.filler_text == "One moment please."
    assert res.dead_air is False
    assert res.value == {"slots": ["tue-2pm"]}
    assert res.elapsed_ms <= 8000 and res.timed_out is False


# =========================================================================== #
#  T027 — autonomy gate: live do|reject|escalate; advise/propose -> artifacts
# =========================================================================== #
def test_t027_live_gate_only_do_reject_escalate():
    from backend.voice.autonomy_gate import AutonomyGate
    g = AutonomyGate()
    assert g.classify([]) == GateDecision.DO                    # narration
    assert g.classify([{"name": "book", "ladder": "do"}]) == GateDecision.DO
    assert g.classify([{"name": "escalate"}]) == GateDecision.ESCALATE
    # clinical do-class blocked
    assert g.classify([{"name": "prescribe", "ladder": "do"}]) == GateDecision.REJECT
    for v in (g.classify([]), g.classify([{"name": "book", "ladder": "do"}]),
              g.classify([{"name": "escalate"}])):
        assert v in (GateDecision.DO, GateDecision.REJECT, GateDecision.ESCALATE)


def test_t027_advise_and_propose_defer_to_post_call_artifacts():
    from backend.voice.autonomy_gate import AutonomyGate, GateContext
    g = AutonomyGate()
    advise = g.classify_full(GateContext(verb="note", ladder="advise"))
    assert advise.persisted_decision == GateDecision.ADVISE
    assert advise.live_action == "none" and advise.post_call_artifact == "briefing_item"

    propose = g.classify_full(GateContext(verb="refill", ladder="propose"))
    assert propose.persisted_decision == GateDecision.PROPOSE
    assert propose.live_action == "none" and propose.post_call_artifact == "draft"


def test_t027_rejects_auto_approved_and_blocks_do_for_clinical():
    from backend.voice.autonomy_gate import AutonomyGate, GateContext
    g = AutonomyGate()
    # auto_approved disposition -> reject (both surfaces)
    assert g.classify([{"name": "refill", "disposition": "auto_approved"}]) == GateDecision.REJECT
    aa = g.classify_full(GateContext(verb="refill", ladder="do", disposition="auto_approved"))
    assert aa.persisted_decision == GateDecision.REJECT and aa.live_action == "reject"
    # do-class blocked for a clinical verb
    clin = g.classify_full(GateContext(verb="prescribe", ladder="do"))
    assert clin.persisted_decision == GateDecision.REJECT


def test_t027_gate_wires_into_turn_loop():
    from backend.voice.autonomy_gate import AutonomyGate
    from backend.voice.turn_loop import ProtocolAwareHooks
    g = AutonomyGate()
    hooks = ProtocolAwareHooks(gate_classify=g.as_gate_classify())
    assert hooks.gate_classify([{"name": "prescribe", "ladder": "do"}]) == GateDecision.REJECT


# =========================================================================== #
#  T028 — refill draft: 0 auto-approvals, never touches request_refill
# =========================================================================== #
def test_t028_refill_with_refills_remaining_still_draft_only(repo):
    from backend.voice.verbs import VoiceVerbs, SimBookingBackend
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)
    v = VoiceVerbs(SimBookingBackend(), repo=repo)
    # refills_remaining > 0 would auto-approve in prescriptions.py — NOT here.
    draft = v.refill_draft("goldsmith-0001", sess.id, party_id="party-1",
                           patient_ref="Rex", drug_name_asserted="Apoquel",
                           refills_remaining_at_capture=3)
    assert draft.status == "draft_vet_review"
    rows = repo.get_refill_drafts(sess.id)
    assert len(rows) == 1 and rows[0]["status"] == "draft_vet_review"


def test_t028_no_code_path_to_request_refill():
    """Import/call-graph assertion: the voice verb module never references the
    auto-approve branch in prescriptions.py::request_refill."""
    import ast
    import inspect
    import backend.voice.verbs as verbs_mod
    tree = ast.parse(inspect.getsource(verbs_mod))
    # No import of PrescriptionAgent, and no attribute call to request_refill.
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names]
            assert "PrescriptionAgent" not in names, "voice verbs must not import PrescriptionAgent"
        if isinstance(node, ast.Attribute):
            assert node.attr != "request_refill", "voice verbs must not call request_refill"


def test_t028_request_refill_never_called_at_runtime(repo, monkeypatch):
    from backend.agents.prescriptions import PrescriptionAgent
    from backend.voice.verbs import VoiceVerbs, SimBookingBackend

    def boom(*a, **k):
        raise AssertionError("voice path must NEVER call request_refill (auto-approve branch)")
    monkeypatch.setattr(PrescriptionAgent, "request_refill", boom)

    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)
    v = VoiceVerbs(SimBookingBackend(), repo=repo)
    for i in range(5):                                          # 0 auto-approvals across the suite
        draft = v.refill_draft("goldsmith-0001", sess.id, party_id="party-1",
                               patient_ref=f"pet-{i}", drug_name_asserted="Rimadyl",
                               refills_remaining_at_capture=i)   # even with refills remaining
        assert draft.status == "draft_vet_review"


def test_t028_auto_approved_disposition_rejected():
    from backend.voice.verbs import VoiceVerbs, SimBookingBackend
    from backend.voice.autonomy_gate import AutoApprovalRejected
    v = VoiceVerbs(SimBookingBackend())
    with pytest.raises(AutoApprovalRejected):
        v.refill_draft("goldsmith-0001", "sess-1", party_id="party-1",
                       patient_ref="Rex", drug_name_asserted="Apoquel",
                       disposition="auto_approved")
