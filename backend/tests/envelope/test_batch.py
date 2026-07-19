"""Feature 009 — T044 batch-independence + prior-reuse harness (SC-010).

A blocked practice does not stall the batch; marginal mapping steps trend down as
practice N inherits group priors. A ``held``/``blocked``/``partial`` practice does
not prevent unblocked practices reaching ``shadow_ready`` (FR-025); per-practice
marginal setup/mapping steps trend down across the batch toward config-reuse only
(SC-010 build-time proxy).
"""
import uuid

import pytest

from backend.envelope.batch import BatchOrchestrator
from backend.envelope.onboarding_repository import OnboardingRepository
from backend.tests.envelope import _pipeline as P
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_batch


def _run_batch(db_url, n=8, seed=555):
    repo = OnboardingRepository(db_url)
    repo.init_db()
    rq, _hr = P.review_queue(db_url)
    clinic = f"batch-{uuid.uuid4().hex[:6]}"
    exports = generate_batch(seed=seed, n=n, clinic_id=clinic)
    result = BatchOrchestrator(repo, rq).run(clinic, exports)
    return repo, clinic, exports, result


def test_blocked_practice_does_not_stall_batch(db_url):
    repo, clinic, exports, result = _run_batch(db_url, n=8)

    # the planted mix: an AR-variance (blocking), a >20%-dirty (held), a partial —
    # none of which reach shadow_ready — and clean practices that DO.
    states = {pid: o.state for pid, o in result.outcomes.items()}
    assert "held" in states.values()            # the >20%-dirty practice
    assert "partial" in states.values()         # the partial-delivery practice

    shadow = result.shadow_ready_practices
    assert shadow, "no practice reached shadow_ready — the batch stalled"
    # unblocked practices reached shadow_ready DESPITE the blocked/held/partial ones.
    assert len(shadow) >= 3

    # the rollup reflects true per-practice stage/status (a computed view).
    for pid, view in result.rollup.items():
        assert view["state"] == repo.get_practice_database_by_practice(pid)["state"]


def test_marginal_mapping_steps_trend_down(db_url):
    repo, clinic, exports, result = _run_batch(db_url, n=8, seed=556)
    steps = result.marginal_mapping_steps

    # practice 0 establishes the group prior (1 mapping step); every subsequent
    # practice of the same variant reuses it (0 steps) — config-reuse only.
    assert steps[0] == 1
    assert all(s == 0 for s in steps[1:]), steps
    # monotonic non-increasing + terminal value 0 (SC-010 build-time proxy).
    assert all(steps[i] >= steps[i + 1] for i in range(len(steps) - 1))
    assert steps[-1] == 0
    # a strict downtrend from the first practice to the last.
    assert steps[0] > steps[-1]


def test_ar_block_not_demoted_to_partial(db_url):
    """A practice with BOTH an unexplained AR variance AND a missing category
    must block on the zero-AR-tolerance guard — never be demoted to a mere
    `partial` delivery (which would make an AR-blocked practice delta-mergeable)."""
    from backend.tests.envelope.fixtures.ezyvet_synthetic_export import (
        generate_practice_export,
    )
    repo = OnboardingRepository(db_url)
    repo.init_db()
    rq, _hr = P.review_queue(db_url)
    clinic = f"batch-arblk-{uuid.uuid4().hex[:6]}"
    pid = f"{clinic}-p0"
    # partial (attachments omitted) AND a planted AR variance — the co-occurrence.
    exp = generate_practice_export(pid, seed=771, variant="partial",
                                   planted="ar_variance")
    result = BatchOrchestrator(repo, rq).run(clinic, [exp])

    o = result.outcomes[pid]
    assert "AR variance" in (o.blocked_reason or "")
    assert o.state == "verified"                 # blocked, NOT partial
    assert repo.get_practice_database_by_practice(pid)["state"] == "verified"
    assert not o.shadow_ready


def test_prior_reuse_persisted_rollup(db_url):
    repo, clinic, exports, result = _run_batch(db_url, n=6, seed=557)
    # the rollup is persisted (append) and carries the per-practice prior cost.
    rollup = repo.latest_batch_rollup(clinic)
    assert rollup is not None
    per = rollup["per_practice"]
    total_mapping_steps = sum(v["marginal_mapping_steps"] for v in per.values())
    # the whole group paid the mapping cost exactly ONCE (one established prior).
    assert total_mapping_steps == 1
