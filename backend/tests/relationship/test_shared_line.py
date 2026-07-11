"""T032 [US4] — shared-line collision RED-TEAM (SC-003).

Two households share one number (Alvarez ‖ Nguyen on 5551110001). The harness
drives resolve -> disambiguate -> reveal and proves, zero-tolerance:

  * the FULL candidate set is returned — 0 silent single-picks (the LIMIT-1 kill);
  * Vera disambiguates neutrally — NO candidate name is ever spoken on a
    multi-candidate result;
  * zero household-specific detail is revealed until exactly one candidate is
    confirmed (recognition summary is scoped to the confirmed household only).
"""
import pytest

from backend.models import ResolutionOutcome
from backend.relationship.identity_resolver import IdentityResolver
from backend.relationship.reveal_log import RevealLog
from backend.relationship.scoped_recall import Fact, ScopedRecall, ThothStub
from backend.relationship.scoping_policy import ScopingPolicy
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-redteam-shared"
SHARED = "5551110001"                  # Alvarez (Jane) ‖ Nguyen (Lan)
HH_A = f"hh-{CLINIC}-alvarez"
HH_B = f"hh-{CLINIC}-nguyen"


@pytest.fixture()
def env(repo):
    build_corpus(clinic_id=CLINIC).seed_into_repo(repo)
    resolver = IdentityResolver(repo)
    facts = [
        Fact("visit_summary", "Alvarez — Rex wellness", subject_household=HH_A,
             subject_clinic=CLINIC),
        Fact("diagnosis", "Alvarez — otitis", subject_household=HH_A, subject_clinic=CLINIC),
        Fact("visit_summary", "Nguyen — Kiki checkup", subject_household=HH_B,
             subject_clinic=CLINIC),
        Fact("appointment", "Tue 3pm", subject_household=HH_A, subject_clinic=CLINIC),
    ]
    policy = ScopingPolicy.load()
    log = RevealLog(repo, CLINIC, interaction_ref="call:shared")
    sr = ScopedRecall(ThothStub(facts), policy, log)
    return resolver, sr, repo


# --------------------------------------------------------------------------- #
#  SC-003 — full candidate set, 0 silent single-picks
# --------------------------------------------------------------------------- #
def test_t032_full_candidate_set_never_single_pick(env):
    resolver, _sr, _repo = env
    result = resolver.resolve(CLINIC, SHARED, "phone")
    assert result.outcome == ResolutionOutcome.AMBIGUOUS_MULTI
    assert result.match_count == 2 and result.is_shared_line       # never reduced to 1
    assert result.confirmed_party_id is None


def test_t032_no_candidate_name_ever_spoken_on_multi(env):
    resolver, _sr, _repo = env
    result = resolver.resolve(CLINIC, SHARED, "phone")
    auto = resolver.auto_id_response(result)
    assert auto["mode"] == "neutral_prompt"                        # neutral, no greeting
    assert "display_name" not in auto
    # no candidate name appears anywhere in the caller-facing payload
    blob = str(auto).lower()
    for name in ("jane", "alvarez", "lan", "nguyen"):
        assert name not in blob


def test_t032_persisted_candidate_set_is_full(env):
    resolver, _sr, repo = env
    resolver.resolve(CLINIC, SHARED, "phone")
    ev = [e for e in repo.get_resolution_events(CLINIC)
          if e["inbound_identifier_normalized"] == SHARED][-1]
    assert len(ev["candidate_set_json"]) == 2                      # both parties persisted


# --------------------------------------------------------------------------- #
#  No household detail until exactly one candidate is confirmed
# --------------------------------------------------------------------------- #
async def test_t032_no_detail_until_one_confirmed(env):
    resolver, sr, _repo = env
    result = resolver.resolve(CLINIC, SHARED, "phone")

    # BEFORE disambiguation: unverified scope — only general schedule, no
    # household-specific detail for either household.
    pre = await sr.recall("anything", audience="caller_unverified", entity_scope=[CLINIC])
    kinds = {f.fact_kind for f in pre}
    assert kinds <= {"appointment"}                               # schedule only
    assert "visit_summary" not in kinds and "diagnosis" not in kinds

    # Disambiguate on an OPEN name -> resolves to exactly ONE candidate (Jane).
    confirmed = resolver.disambiguate(result, "Jane Alvarez", CLINIC)
    assert confirmed.outcome == ResolutionOutcome.RESOLVED_SINGLE
    jane = f"party-{CLINIC}-c1001"
    assert confirmed.confirmed_party_id == jane

    # AFTER confirming Jane: client_verified recall scoped to HER household only.
    post = await sr.recall("summary", audience="client_verified", entity_scope=[HH_A, CLINIC])
    hhs = {f.subject_household for f in post}
    assert HH_B not in hhs                                         # Nguyen never leaks
    assert any(f.subject_household == HH_A for f in post)          # own detail OK


async def test_t032_wrong_disambiguation_reveals_nothing(env):
    resolver, sr, _repo = env
    result = resolver.resolve(CLINIC, SHARED, "phone")
    # a name matching NEITHER candidate stays ambiguous — no confirmation
    still = resolver.disambiguate(result, "Napoleon Bonaparte", CLINIC)
    assert still.confirmed_party_id is None
    assert still.outcome == ResolutionOutcome.AMBIGUOUS_MULTI
    # unverified caller still gets no household detail
    out = await sr.recall("x", audience="caller_unverified", entity_scope=[CLINIC])
    assert all(f.fact_kind == "appointment" for f in out)
