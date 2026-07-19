"""Feature 009 — T010 scope-vs-request acceptance.

- a complete-fixture receipt records all six categories present;
- the partial fixture (attachments omitted) records attachments_imaging as
  absent — with no normalization yet performed.
"""
import uuid

from backend.envelope.scope_check import (
    ScopeChecker, manifest_from_export, manifest_from_zip,
)
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"
SIX = {"patient_client", "scheduling", "invoicing_billing_payments",
       "communications", "attachments_imaging", "configuration"}


def _pid():
    return f"p-{uuid.uuid4().hex[:8]}"


def test_complete_records_all_six_present(repo):
    checker = ScopeChecker(repo)
    pid = _pid()
    exp = generate_practice_export(pid, seed=7, variant="complete")
    sc = checker.check(CLINIC, pid, "pdb1", manifest_from_export(exp))
    assert set(sc.dispositions.keys()) == SIX
    assert all(v == "present" for v in sc.dispositions.values()), sc.dispositions
    # persisted, and no normalization performed (no format profile)
    assert repo.get_scope_check(pid) is not None
    assert repo.has_format_profile(pid) is False


def test_partial_records_attachments_absent(repo):
    checker = ScopeChecker(repo)
    pid = _pid()
    exp = generate_practice_export(pid, seed=7, variant="partial")
    sc = checker.check(CLINIC, pid, "pdb1", manifest_from_export(exp))
    assert sc.dispositions["attachments_imaging"] == "absent"
    assert "attachments_imaging" in checker.absent_categories(sc.dispositions)
    # every other category present
    others = {k: v for k, v in sc.dispositions.items() if k != "attachments_imaging"}
    assert all(v == "present" for v in others.values()), others


def test_manifest_from_zip_matches_in_memory(repo):
    pid = _pid()
    exp = generate_practice_export(pid, seed=7, variant="complete")
    z = manifest_from_zip(exp.raw_bytes())
    mem = manifest_from_export(exp)
    assert z == mem
