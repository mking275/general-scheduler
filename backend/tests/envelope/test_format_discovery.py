"""Feature 009 — T013 format discovery acceptance.

- discovery over a fixture database emits a FormatProfile enumerating entities,
  counts, encodings, and referential relationships and names the variant;
- a corrupt/truncated fixture fails at discovery with a specific error and is
  NOT partially normalized (FR-033).
"""
import uuid

import pytest

from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.format_discovery import DiscoveryError, FormatDiscovery
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"


def _pid():
    return f"p-{uuid.uuid4().hex[:8]}"


def test_discovery_emits_full_profile(repo):
    fd = FormatDiscovery(repo, extraction_port=SimExtractionPort())
    pid = _pid()
    exp = generate_practice_export(pid, seed=7, variant="complete")
    profile = fd.discover(CLINIC, pid, "pdb1", exp)

    # entities + counts
    assert profile.entities["clients"] == len(exp.entities["clients"])
    assert profile.entities["invoices"] == len(exp.entities["invoices"])
    # encodings
    assert profile.encodings["clients"] == "utf-8"
    # referential relationships inferred (patients.client_id -> clients etc.)
    rels = {(r["from"], r["column"], r["to"]) for r in profile.referential_relationships}
    assert ("patients", "client_id", "clients") in rels
    assert ("appointments", "patient_id", "patients") in rels
    assert ("ar_balances", "client_id", "clients") in rels
    # variant named
    assert profile.export_variant == "complete_v1"
    # persisted
    assert repo.has_format_profile(pid) is True


def test_corrupt_export_fails_and_writes_no_profile(repo):
    fd = FormatDiscovery(repo, extraction_port=SimExtractionPort())
    pid = _pid()
    with pytest.raises(DiscoveryError):
        fd.discover(CLINIC, pid, "pdb1", b"this is not a zip")
    # NOT partially normalized: no FormatProfile row exists
    assert repo.has_format_profile(pid) is False
