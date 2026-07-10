"""T040 — disclosure-100% + degraded/stateless-mode fallback (SC-001, FR-007).

Asserts 100% first-utterance disclosure across the fixtures, and that a
degraded-mode call (VP-4a household memory unavailable) completes in unverified
scope without failing the call. Sim only.
"""
import os

import yaml

from backend.models import CallSession, TurnRole, VerificationState
from backend.voice.adapter_guarantees import DisclosureGuarantee, load_disclosure

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_CONFIG_VOICE = os.path.join(_REPO_ROOT, "config", "voice")

# The SC-001 disclosure must always announce AI + recording + the emergency path.
_REQUIRED_TOKENS = ("ai", "record", "emergency")


def _disclosure_fixtures() -> list[str]:
    """Every disclosure fixture available: the .txt scripts + any embedded in the
    clinic_voice_config yaml."""
    texts = []
    for fn in os.listdir(_CONFIG_VOICE):
        if fn.startswith("disclosure_script.") and fn.endswith(".txt"):
            with open(os.path.join(_CONFIG_VOICE, fn)) as f:
                texts.append(f.read().strip())
    return texts


def test_t040_disclosure_is_seq1_on_100pct_of_calls():
    g = DisclosureGuarantee()
    for _ in range(200):
        sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15550000000")
        turn = g.deliver_disclosure(sess)
        assert turn.seq == 1                                 # first utterance
        assert turn.role == TurnRole.SYSTEM
        low = turn.text.lower()
        assert all(tok in low for tok in _REQUIRED_TOKENS)
        assert sess.consent_recorded_at == turn.started_at    # consent = disclosure time


def test_t040_all_disclosure_fixtures_carry_required_tokens():
    fixtures = _disclosure_fixtures()
    assert fixtures, "no disclosure fixtures found"
    for text in fixtures:
        low = text.lower()
        for tok in _REQUIRED_TOKENS:
            assert tok in low, f"fixture missing {tok!r}: {text[:60]!r}"
    # sanity: it explicitly denies being a clinician (FR-013 grounding)
    assert "not a nurse" in load_disclosure("en").lower()


def test_t040_degraded_mode_completes_in_unverified_scope():
    """VP-4a unavailable → the stub returns None → unverified/stateless operation;
    the call still completes (FR-007). No name leak, no failed call."""
    from backend.voice.prefetch import Prefetcher, fetch_household_summary
    from backend.voice.verbs import SimBookingBackend, UnverifiedScopeError, VoiceVerbs

    # VP-4a absent -> household stub returns None (whole object).
    assert fetch_household_summary("party-1", provider=None) is None

    p = Prefetcher(availability_fn=lambda c: [{"slot": "tue-2pm"}],
                   config_fn=lambda c: {"clinic_id": "goldsmith-0001"},
                   household_provider=None)
    cache = p.prefetch_context("goldsmith-0001", party_id="party-1",
                               audience_scope="caller_unverified")
    assert cache.household_summary is None                   # no greeting-name leak

    # The call proceeds in unverified scope: availability + intake_capture work,
    # but acting on an existing client's records is rejected.
    v = VoiceVerbs(SimBookingBackend())
    assert v.availability("goldsmith-0001", audience_scope="caller_unverified")
    draft = v.intake_capture("Jane", "+15550001111", "new puppy",
                             audience_scope="caller_unverified")
    assert draft.caller_name == "Jane"
    try:
        v.book("goldsmith-0001",
               v.availability("goldsmith-0001", audience_scope="caller_unverified")[0],
               "Rex", party_id="party-1", audience_scope="caller_unverified")
        assert False, "unverified book must be rejected"
    except UnverifiedScopeError:
        pass

    # The degraded call is a completed, non-failed call.
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001",
                       degraded_mode=True,
                       verification_state=VerificationState.UNVERIFIED,
                       ended_at="2026-07-07T02:00:00+00:00")
    assert sess.degraded_mode is True
    assert sess.verification_state == VerificationState.UNVERIFIED
    assert sess.ended_at is not None                         # call completed
