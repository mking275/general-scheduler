"""Phase C — triage protocol engine (T020..T022).

The engine is deterministic and config-driven; the bundled sample protocol is
UNSIGNED test content (VP-9 signs the real content). Err-to-escalate always.
"""
import pytest

from backend.models import TriageProtocol


# --- T020: engine + versioned YAML loader ----------------------------------
def test_t020_sample_loads_and_emergency_keywords_resolve():
    from backend.voice.triage_protocol import TriageProtocolEngine

    eng = TriageProtocolEngine.load_sample("goldsmith")
    assert eng.config.version == "0.0.0-sample"
    assert eng.config.escalation_on_flag == 1.0

    # "collapsed" and "not breathing" -> emergency urgency class.
    for phrase in ("my dog collapsed", "the cat is not breathing"):
        flag = eng.step(phrase)
        assert flag is not None
        assert flag["urgency"] == "emergency"
        assert flag["routing_target"] == "on_call_vet"


def test_t020_benign_and_routine_classification():
    from backend.voice.triage_protocol import TriageProtocolEngine

    eng = TriageProtocolEngine.load_sample("goldsmith")
    # A benign turn flags nothing.
    assert eng.step("I'd like to say hello and confirm my address") is None
    # A routine keyword routes to booking, not escalation.
    flag = eng.step("I need to book a checkup")
    assert flag is not None and flag["urgency"] == "routine"
    assert flag["routing_target"] == "booking"


def test_t020_err_to_escalate_most_urgent_wins():
    from backend.voice.triage_protocol import TriageProtocolEngine

    # A phrase carrying both a routine keyword ("appointment") and an emergency
    # keyword ("collapsed") must resolve to the MOST urgent class.
    eng = TriageProtocolEngine.load_sample("goldsmith")
    flag = eng.step("I called for an appointment but now he collapsed")
    assert flag is not None and flag["urgency"] == "emergency"


def test_t020_versioned_loader_from_yaml_str():
    from backend.voice.triage_protocol import TriageProtocolEngine

    eng = TriageProtocolEngine.from_yaml_str(
        """
        version: "9.9.9-test"
        slo: {escalation_on_flag: 1.0}
        urgency_classes:
          emergency:
            routing_target: "on_call_vet"
            keywords: ["choking"]
        """
    )
    assert eng.config.version == "9.9.9-test"
    assert eng.step("she is choking")["urgency"] == "emergency"


# --- T021: protocol override authority over the model ----------------------
async def test_t021_protocol_overrides_model_booking_to_escalate():
    from backend.voice.triage_protocol import TriageProtocolEngine
    from backend.voice.turn_loop import ProtocolAwareHooks, run_turn
    from backend.voice.shims.l2_bridge_shim import ModelOutput, TurnContext

    eng = TriageProtocolEngine.load_sample("goldsmith")

    # The gate must NEVER be consulted once the protocol flags — proving no
    # write path is even reached (no booking committed).
    gate_calls = []

    def spy_gate(tool_calls):
        gate_calls.append(tool_calls)
        from backend.models import GateDecision
        return GateDecision.DO

    hooks = ProtocolAwareHooks(protocol_step=eng.as_protocol_step(),
                               gate_classify=spy_gate)

    # Model tries to BOOK during a protocol-flagged (emergency) turn.
    draft = ModelOutput(text="Sure, I can book that appointment for Tuesday.",
                        tool_calls=[{"name": "book", "args": {"slot": "tue-2pm"}}])
    ctx = TurnContext(session_id="s", seq=3,
                      transcript_delta="wait, my dog just collapsed")
    res = await run_turn({}, draft, ctx, hooks)

    assert res.action == "escalate"
    assert res.spoken_text != draft.text          # model output overridden
    assert res.decision.override_reason.startswith("protocol:")
    assert gate_calls == []                        # no write authorized/committed
    assert hooks.stats.overrides == 1
    assert hooks.stats.escalations == 1


async def test_t021_unflagged_turn_lets_model_narrate():
    from backend.voice.triage_protocol import TriageProtocolEngine
    from backend.voice.turn_loop import ProtocolAwareHooks, run_turn
    from backend.voice.shims.l2_bridge_shim import ModelOutput, TurnContext

    eng = TriageProtocolEngine.load_sample("goldsmith")
    hooks = ProtocolAwareHooks(protocol_step=eng.as_protocol_step())
    res = await run_turn({}, ModelOutput(text="Tuesday at 2pm, does that work?"),
                         TurnContext(session_id="s", seq=2,
                                     transcript_delta="Tuesday afternoon please"),
                         hooks)
    assert res.action == "speak"
    assert res.spoken_text == "Tuesday at 2pm, does that work?"


# --- T022: signature gate + regression harness -----------------------------
def test_t022_unsigned_protocol_blocks_live_allows_sim():
    from backend.voice.triage_protocol import (
        TriageProtocolEngine, UnsignedProtocolError,
    )

    eng = TriageProtocolEngine.load_sample("goldsmith")
    assert eng.is_signed is False                  # sample is UNSIGNED by design
    eng.assert_live_allowed(is_live=False)         # sim: permitted
    with pytest.raises(UnsignedProtocolError):
        eng.assert_live_allowed(is_live=True)      # live: blocked


def test_t022_signed_protocol_allows_live():
    from backend.voice.triage_protocol import TriageProtocolEngine

    eng = TriageProtocolEngine.from_yaml_str(
        """
        version: "1.0.0"
        signed_by: "Dr. Goldsmith DVM"
        signed_at: "2026-10-01T00:00:00Z"
        slo: {escalation_on_flag: 1.0}
        urgency_classes:
          emergency: {routing_target: "on_call_vet", keywords: ["collapsed"]}
        """
    )
    assert eng.is_signed is True
    eng.assert_live_allowed(is_live=True)          # no raise


def test_t022_keyword_regression_zero_misroutes():
    """Every labelled probe must resolve to its expected urgency — 0 misroutes."""
    from backend.voice.triage_protocol import TriageProtocolEngine

    eng = TriageProtocolEngine.load_sample("goldsmith")
    regression = [
        ("my dog collapsed on the floor", "emergency"),
        ("he is not breathing", "emergency"),
        ("she had a seizure", "emergency"),
        ("the puppy was hit by a car", "emergency"),
        ("he swallowed something toxic", "emergency"),
        ("my cat is vomiting blood", "urgent"),
        ("the dog won't eat", "urgent"),
        ("I'd like to book a checkup", "routine"),
        ("time for his vaccine", "routine"),
        ("I need a refill", "routine"),
    ]
    misroutes = []
    for phrase, expected in regression:
        flag = eng.step(phrase)
        got = flag["urgency"] if flag else None
        if got != expected:
            misroutes.append((phrase, expected, got))
    assert not misroutes, f"protocol misroutes: {misroutes}"


def test_t022_signature_gate_against_db_row(repo):
    """A ``triage_protocol`` row with no signature is inactive-for-live."""
    from backend.voice.triage_protocol import TriageProtocolEngine

    unsigned = TriageProtocol(clinic_id="goldsmith-0001", version="0.0.0-sample",
                              config_yaml="", active=True)
    repo.create_triage_protocol(unsigned)
    got = repo.get_active_triage_protocol("goldsmith-0001")
    assert got is not None
    # signed_by / signed_at unset -> unsigned -> live blocked.
    is_signed = bool(got.get("signed_by")) and bool(got.get("signed_at"))
    assert is_signed is False
    eng = TriageProtocolEngine.load_sample("goldsmith")
    with pytest.raises(Exception):
        eng.assert_live_allowed(is_live=True)
