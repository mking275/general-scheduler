"""Phase D — T020 ScopedRecall (unscoped recall unrepresentable) + T021 scope."""
import inspect

import pytest

from backend.relationship.reveal_log import RevealLog
from backend.relationship.scoped_recall import Fact, ScopedRecall, ThothStub
from backend.relationship.scoping_policy import ScopingPolicy

CLINIC = "clinic-scoped-recall"


def _facts():
    return [
        # own-household schedule + clinical + client_summary
        Fact("appointment", "Tue 3pm", entity_ref="patient:ezyvet_p1",
             subject_household="hhA", subject_clinic=CLINIC),
        Fact("visit_summary", "annual wellness", entity_ref="client:ezyvet_c1",
             subject_household="hhA", subject_clinic=CLINIC),
        # financial (not in client_verified allow_classes)
        Fact("balance", "$240 due", entity_ref="client:ezyvet_c1",
             subject_household="hhA", subject_clinic=CLINIC),
        # ANOTHER household's clinical detail (own_household_only must withhold)
        Fact("diagnosis", "otitis", entity_ref="patient:ezyvet_p9",
             subject_household="hhB", subject_clinic=CLINIC),
    ]


@pytest.fixture()
def scoped(repo):
    policy = ScopingPolicy.load()
    log = RevealLog(repo, CLINIC, interaction_ref="call:sr")
    return ScopedRecall(ThothStub(_facts()), policy, log)


# --------------------------------------------------------------------------- #
#  T020 — unscoped client-facing recall is UNREPRESENTABLE (API shape)
# --------------------------------------------------------------------------- #
def test_t020_audience_is_required_keyword_only():
    for name in ("recall", "recall_by_kind"):
        sig = inspect.signature(getattr(ScopedRecall, name))
        aud = sig.parameters["audience"]
        assert aud.kind == inspect.Parameter.KEYWORD_ONLY
        assert aud.default is inspect.Parameter.empty        # no default -> required
        assert sig.parameters["entity_scope"].default is inspect.Parameter.empty


async def test_t020_calling_recall_without_audience_is_type_error(scoped):
    with pytest.raises(TypeError):
        await scoped.recall("anything")                      # no audience -> TypeError


def test_t020_no_unscoped_overload_exists():
    # The only recall surfaces are the two scoped ones; no bypass method exists.
    publics = [m for m in dir(ScopedRecall) if not m.startswith("_")]
    assert set(publics) == {"recall", "recall_by_kind"}


def test_t020_raw_thoth_handle_is_unreachable(scoped):
    # Red-team probe: the raw Thoth handle is name-mangled private — no public /
    # single-underscore attribute exposes it.
    assert getattr(scoped, "_thoth", None) is None
    assert not hasattr(scoped, "thoth")
    thoth_objs = [v for k, v in vars(scoped).items()
                  if isinstance(v, ThothStub) and not k.startswith("_ScopedRecall__")]
    assert thoth_objs == []                                  # only the mangled handle holds it


async def test_t020_every_recall_emits_a_reveal_audit(scoped, repo):
    before = len(repo.get_reveal_decisions(CLINIC))
    await scoped.recall("anything", audience="client_verified", entity_scope=["hhA", CLINIC])
    after = len(repo.get_reveal_decisions(CLINIC))
    assert after - before == len(_facts())                   # one audit row per fact


# --------------------------------------------------------------------------- #
#  T021 — entity_scope enforcement (own household, no financial, unverified)
# --------------------------------------------------------------------------- #
async def test_t021_client_verified_own_household_gets_own_detail(scoped):
    out = await scoped.recall("x", audience="client_verified", entity_scope=["hhA", CLINIC])
    kinds = {f.fact_kind for f in out}
    assert "appointment" in kinds and "visit_summary" in kinds


async def test_t021_another_household_detail_always_withheld(scoped, repo):
    out = await scoped.recall("x", audience="client_verified", entity_scope=["hhA", CLINIC])
    # hhB diagnosis never returned
    assert all(f.subject_household != "hhB" for f in out)
    wrong = [r for r in repo.get_reveal_decisions(CLINIC)
             if r["reason"] == "wrong_household" and r["fact_kind"] == "diagnosis"]
    assert wrong, "a foreign-household fact must log wrong_household"


async def test_t021_financial_withheld_for_client_verified(scoped):
    out = await scoped.recall("x", audience="client_verified", entity_scope=["hhA", CLINIC])
    assert all(f.fact_kind != "balance" for f in out)        # financial not allowed


async def test_t021_caller_unverified_limited_to_schedule(scoped):
    out = await scoped.recall("x", audience="caller_unverified", entity_scope=["hhA", CLINIC])
    kinds = {f.fact_kind for f in out}
    assert kinds <= {"appointment"}                          # schedule availability only
    assert "visit_summary" not in kinds and "diagnosis" not in kinds
