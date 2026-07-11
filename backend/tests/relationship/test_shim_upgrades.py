"""Phase F — T026/T027/T028/T029 010-shim upgrades + Thoth thread binding, and
the T030 preserve-strings gate.

These prove the 010 shims are now BACKED by the real 011 components while their
public APIs are unchanged. The full 116-test 010 voice suite staying green is
the other half of T030 (run separately); here we assert the real-backing works
and that the 010 enum strings are byte-for-byte unchanged.
"""
import inspect

import pytest

from backend.relationship.consent_registry import ConsentRegistry
from backend.relationship.identity_resolver import IdentityResolver
from backend.relationship.reveal_log import RevealLog
from backend.relationship.scoped_recall import (
    Fact, ScopedRecall, ThothStub, ThreadManager,
)
from backend.relationship.scoping_policy import ScopingPolicy
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-shim-upgrade"
SHARED = "5551110001"          # multi-match (Alvarez + Nguyen)
TOM = "5551110002"             # single exact-phone match -> party c1002


@pytest.fixture()
def seeded(repo):
    build_corpus(clinic_id=CLINIC).seed_into_repo(repo)
    from sqlalchemy import text
    with repo.engine.begin() as conn:
        conn.execute(text("DELETE FROM contact_consent WHERE clinic_id = :c"),
                     {"c": CLINIC})
    return repo


# =========================================================================== #
#  T026 — channel_binding_shim backed by the real resolver (API unchanged)
# =========================================================================== #
def test_t026_shim_signatures_unchanged():
    from backend.voice.shims import channel_binding_shim as cb
    rb = inspect.signature(cb.resolve_binding)
    # the original positional params are intact; new backing params are kw-only
    assert list(rb.parameters)[:2] == ["channel_address", "channel"]
    assert rb.parameters["resolver"].kind == inspect.Parameter.KEYWORD_ONLY
    dis = inspect.signature(cb.disambiguate)
    assert list(dis.parameters) == ["binding", "spoken_name"]


def test_t026_shared_number_real_resolver_is_shared_line(seeded):
    from backend.voice.shims import channel_binding_shim as cb
    resolver = IdentityResolver(seeded)
    b = cb.resolve_binding(SHARED, "voice", resolver=resolver, clinic_id=CLINIC)
    assert b.is_shared_line and len(b.candidate_parties) > 1   # LIMIT 1 kill


def test_t026_single_exact_phone_returns_exactly_one(seeded):
    from backend.voice.shims import channel_binding_shim as cb
    resolver = IdentityResolver(seeded)
    b = cb.resolve_binding(TOM, "voice", resolver=resolver, clinic_id=CLINIC)
    assert len(b.candidate_parties) == 1
    assert not b.is_shared_line


def test_t026_disambiguation_never_enumerates_names(seeded):
    from backend.voice.shims import channel_binding_shim as cb
    resolver = IdentityResolver(seeded)
    b = cb.resolve_binding(SHARED, "voice", resolver=resolver, clinic_id=CLINIC)
    # a wrong name keeps the caller unverified and reads back nothing
    b2 = cb.disambiguate(b, "Napoleon Bonaparte")
    assert b2.verification_level == "none"
    assert b2.confirmed_party is None
    # an exact name soft-confirms exactly one without ever listing candidates
    b3 = cb.disambiguate(
        cb.resolve_binding(SHARED, "voice", resolver=resolver, clinic_id=CLINIC),
        "Jane Alvarez")
    assert b3.verification_level == "soft_confirmed"


def test_t026_no_resolver_uses_fixture_default_unchanged():
    # With no resolver the 010 fixture path is untouched (the 010 tests bind this).
    from backend.voice.shims import channel_binding_shim as cb
    b = cb.resolve_binding("+15551110001")
    assert b.is_shared_line and len(b.candidate_parties) == 3


# =========================================================================== #
#  T027 — consent_shim backed by ConsentRegistry (ConsentDecision shape kept)
# =========================================================================== #
async def test_t027_opt_out_via_inbound_path_visible_through_shim(seeded):
    from backend.voice.shims import consent_shim as cs
    from backend.relationship.consent_registry import ConsentDecision as RegDecision
    reg = ConsentRegistry(seeded, CLINIC)
    party = f"party-{CLINIC}-c1002"
    cs.bind_registry(reg)
    try:
        # opt-out recorded via the registry (the inbound STOP path writes here)
        reg.record_opt_out(party, "sms", source="inbound_stop", keyword="STOP")
        dec = await cs.consent_check(party, "sms")
        assert isinstance(dec, cs.ConsentDecision)             # shim's own shape
        assert dec.allowed is False and dec.reason == "channel_opt_out"
        # ConsentDecision shape is field-identical across shim and registry
        assert {f for f in vars(dec)} == {f for f in vars(RegDecision(allowed=True))}
        # default (never-opted-out) party allows
        assert (await cs.consent_check(f"party-{CLINIC}-c1001", "sms")).allowed is True
    finally:
        cs.bind_registry(None)


async def test_t027_unbound_shim_default_unchanged():
    from backend.voice.shims import consent_shim as cs
    cs.bind_registry(None)
    assert (await cs.consent_check("party-optout-demo", "voice")).allowed is False
    assert (await cs.consent_check("party-regular", "voice")).allowed is True


# =========================================================================== #
#  T028 — HouseholdSummary real audience-scoped projection via ScopedRecall
# =========================================================================== #
def _scoped(repo, facts):
    policy = ScopingPolicy.load()
    log = RevealLog(repo, CLINIC, interaction_ref="call:a4")
    return ScopedRecall(ThothStub(facts), policy, log)


def test_t028_verified_caller_gets_own_scoped_greeting_summary(seeded):
    from backend.voice.prefetch import HouseholdSummary, real_household_provider
    party = f"party-{CLINIC}-c1001"                            # Jane Alvarez
    hid = seeded.get_contact(party)["household_id"]
    facts = [
        Fact("last_visit", "annual wellness — Rex", subject_household=hid,
             subject_clinic=CLINIC),
        # a foreign household's summary must never surface
        Fact("last_visit", "OTHER household", subject_household="hh-foreign",
             subject_clinic=CLINIC),
    ]
    provider = real_household_provider(
        seeded, _scoped(seeded, facts), CLINIC,
        audience="client_verified", verification_level="soft_confirmed")
    summary = provider(party)
    assert isinstance(summary, HouseholdSummary)
    assert summary.display_name_for_greeting == "Jane Alvarez"  # greeting populated
    assert summary.last_visit_summary_line == "annual wellness — Rex"
    assert "OTHER household" not in (summary.last_visit_summary_line or "")
    names = {p.name for p in summary.household_patients}
    assert "Rex" in names and "Buddy" not in names             # deceased excluded


def test_t028_unverified_caller_no_greeting_name_leak(seeded):
    from backend.voice.prefetch import real_household_provider
    party = f"party-{CLINIC}-c1001"
    hid = seeded.get_contact(party)["household_id"]
    facts = [Fact("last_visit", "x", subject_household=hid, subject_clinic=CLINIC)]
    provider = real_household_provider(
        seeded, _scoped(seeded, facts), CLINIC,
        audience="caller_unverified", verification_level="none")
    summary = provider(party)
    assert summary.display_name_for_greeting is None           # no name leak
    # caller_unverified is not allowed client_summary -> the line is withheld
    assert summary.last_visit_summary_line is None


def test_t028_a4_field_shape_unchanged():
    # The frozen A4 field set the 010 prefetch tests consume is intact.
    from backend.voice.prefetch import HouseholdSummary
    fields = set(inspect.signature(HouseholdSummary).parameters)
    assert fields == {"party_id", "display_name_for_greeting", "household_patients",
                      "last_visit_summary_line", "audience_scope", "verification_level"}


# =========================================================================== #
#  T029 — thread_id binding: single-channel voice continuity ONLY
# =========================================================================== #
async def test_t029_voice_thread_recalls_prior_same_channel_context(repo):
    tm = ThreadManager()
    tid = tm.bind_thread(channel="voice", party_id="party-1")
    prior = Fact("appointment", "Tue 3pm", subject_household="hhA",
                 subject_clinic=CLINIC, thread_id=tid)
    scoped = _scoped(repo, [prior])
    out = await scoped.recall("prior?", audience="client_verified",
                              entity_scope=["hhA", CLINIC], thread_id=tid)
    assert [f.content for f in out] == ["Tue 3pm"]             # same-channel continuity


async def test_t029_no_cross_channel_switching(repo):
    tm = ThreadManager()
    voice_tid = tm.bind_thread(channel="voice", party_id="party-1")
    sms_tid = tm.bind_thread(channel="sms", party_id="party-1")
    assert voice_tid != sms_tid                                # channel-qualified
    # a fact bound to the voice thread is NOT recalled under the sms thread
    fact = Fact("appointment", "voice-only", subject_household="hhA",
                subject_clinic=CLINIC, thread_id=voice_tid)
    scoped = _scoped(repo, [fact])
    out = await scoped.recall("x", audience="client_verified",
                              entity_scope=["hhA", CLINIC], thread_id=sms_tid)
    assert out == []                                           # no cross-channel bleed
    # ThreadManager exposes no cross-channel carry method (4b scope guard)
    publics = {m for m in dir(ThreadManager) if not m.startswith("_")}
    assert publics == {"bind_thread"}


# =========================================================================== #
#  T030 — preserve-strings gate (the 4-tier translation lives only at the edge)
# =========================================================================== #
def test_t030_010_verification_state_strings_unchanged():
    from backend.models import VerificationState
    assert VerificationState.UNVERIFIED.value == "unverified"
    assert VerificationState.SOFT_CONFIRMED.value == "soft_confirmed"


def test_t030_010_shim_verification_level_strings_unchanged():
    from backend.voice.shims import channel_binding_shim as cb
    b = cb.resolve_binding("+19998887777")                     # unknown -> none
    assert b.verification_level == "none"
    b2 = cb.disambiguate(cb.resolve_binding("+15551110001"), "Jane")
    assert b2.verification_level == "soft_confirmed"           # never rewritten


def test_t030_core_tier_translation_only_at_boundary_edge():
    # The 4-tier core vocabulary is produced by the R5 adapter, never written
    # back into either 010 enum (H2).
    from backend.relationship.verification import reconcile_binding_tier
    assert reconcile_binding_tier("none") == "unverified"
    assert reconcile_binding_tier("unverified") == "unverified"
    assert reconcile_binding_tier("soft_confirmed") == "phone_match"
    assert reconcile_binding_tier("strong") == "identity_confirmed"
