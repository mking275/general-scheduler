"""Feature 009 — T036 chain-of-custody-before-parse harness (SC-001).

Assert every received database has a vault object + checksum + scope-vs-request
record written **before** any parser runs; no parse is reachable pre-receipt.
100% of received databases carry a full chain-of-custody record; 0 parses occur
pre-receipt.
"""
import uuid

from backend.envelope.scope_check import ScopeChecker, manifest_from_export
from backend.envelope.vault import ReceiptService, ReceivedExport, SimVault
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_batch

CLINIC = "goldsmith"


def _receive_batch(repo, n=5):
    clinic = f"{CLINIC}-{uuid.uuid4().hex[:6]}"
    exports = generate_batch(seed=901, n=n, clinic_id=clinic)
    vault = SimVault()
    receipt = ReceiptService(repo, vault).receive_delivery(
        clinic, "secure-file-transfer",
        [ReceivedExport(e.practice_id, e.raw_bytes()) for e in exports])
    # the scope-vs-request record (a manifest read, still pre-parse) per database.
    for e in exports:
        pdb = repo.get_practice_database_by_practice(e.practice_id)
        ScopeChecker(repo).check(clinic, e.practice_id, pdb["id"],
                                 manifest_from_export(e))
    return clinic, exports, vault, receipt


def test_full_chain_of_custody_before_any_parse(repo):
    clinic, exports, vault, receipt = _receive_batch(repo)

    for e in exports:
        pid = e.practice_id
        # 1) a persisted chain-of-custody record: source/timestamp/checksum, and
        #    parsed MUST be false at write time.
        coc = repo.get_chain_of_custody(pid)
        assert len(coc) == 1, f"{pid}: expected exactly one chain-of-custody row"
        row = coc[0]
        assert row["source"] and row["delivery_timestamp"]
        assert row["checksum"] == e.checksum()
        assert row["byte_count"] == e.byte_count()
        assert row["parsed"] is False, f"{pid}: parsed flag set before any parse"

        # 2) the export sits encrypted-at-rest in the vault (ciphertext, not the
        #    plaintext export) — captured before touched.
        pdb = repo.get_practice_database_by_practice(pid)
        ref = pdb["vault_object_ref"]
        assert ref and vault.exists(ref)
        assert vault.stored_bytes(ref) != e.raw_bytes()      # encrypted at rest

        # 3) the scope-vs-request record is present (manifest read, pre-parse).
        assert repo.get_scope_check(pid) is not None

        # 4) NO parse/normalize has run — the canonical store is empty (0 parses
        #    pre-receipt).
        assert repo.count_canonical("canonical_record", pid) == 0
        assert pdb["state"] == "received"


def test_hundred_percent_received_carry_full_record(repo):
    clinic, exports, _vault, _receipt = _receive_batch(repo, n=6)
    with_full_record = 0
    for e in exports:
        coc = repo.get_chain_of_custody(e.practice_id)
        sc = repo.get_scope_check(e.practice_id)
        if coc and coc[0]["checksum"] and sc is not None and not coc[0]["parsed"]:
            with_full_record += 1
    assert with_full_record == len(exports)             # 100% (SC-001)
