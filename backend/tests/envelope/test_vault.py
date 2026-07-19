"""Feature 009 — T009 vault + chain-of-custody receipt acceptance.

- a received export is stored encrypted-at-rest with a persisted chain-of-custody
  record (source/timestamp/byte-count/checksum) and NO parser has run;
- the practice sits at `received`;
- a duplicate/superseding delivery is reconciled against the earlier receipt via
  checksum, not blindly re-loaded.
"""
import uuid

from backend.envelope.vault import ReceivedExport, ReceiptService, SimVault
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"


def _export(seed=7, variant="complete"):
    pid = f"p-{uuid.uuid4().hex[:8]}"
    return pid, generate_practice_export(pid, seed=seed, variant=variant)


def test_encrypted_at_rest_and_chain_of_custody_before_parse(repo, tmp_path):
    vault = SimVault(root=str(tmp_path))
    svc = ReceiptService(repo, vault=vault)
    pid, exp = _export()
    receipt = svc.receive_delivery(CLINIC, source="sftp",
                                   exports=[ReceivedExport(pid, exp.raw_bytes())])
    pr = receipt.practices[0]
    assert pr.disposition == "received"

    # stored encrypted-at-rest: the at-rest bytes are ciphertext, not plaintext
    at_rest = vault.stored_bytes(pr.vault_object_ref)
    assert at_rest != exp.raw_bytes()
    assert vault.read(pr.vault_object_ref) == exp.raw_bytes()  # decrypts back

    # chain-of-custody persisted with source/timestamp/byte-count/checksum, parsed=False
    cc = repo.get_chain_of_custody(pid)
    assert len(cc) == 1
    row = cc[0]
    assert row["source"] == "sftp"
    assert row["byte_count"] == len(exp.raw_bytes())
    assert row["checksum"] == exp.checksum()
    assert row["delivery_timestamp"]
    assert row["parsed"] is False               # NO parser has run

    # the practice sits at received; no FormatProfile exists yet
    pd = repo.get_practice_database_by_practice(pid)
    assert pd["state"] == "received"
    assert repo.has_format_profile(pid) is False


def test_duplicate_delivery_is_not_reloaded(repo, tmp_path):
    vault = SimVault(root=str(tmp_path))
    svc = ReceiptService(repo, vault=vault)
    pid, exp = _export()
    svc.receive_delivery(CLINIC, "sftp", [ReceivedExport(pid, exp.raw_bytes())])
    # same bytes -> same checksum -> duplicate, not re-loaded
    r2 = svc.receive_delivery(CLINIC, "sftp", [ReceivedExport(pid, exp.raw_bytes())])
    assert r2.practices[0].disposition == "duplicate"
    # still exactly one chain-of-custody row (no blind re-load)
    assert len(repo.get_chain_of_custody(pid)) == 1


def test_superseding_delivery_marks_earlier(repo, tmp_path):
    vault = SimVault(root=str(tmp_path))
    svc = ReceiptService(repo, vault=vault)
    pid, exp = _export(seed=7)
    svc.receive_delivery(CLINIC, "sftp", [ReceivedExport(pid, exp.raw_bytes())])
    # different bytes -> supersedes the earlier receipt
    exp2 = generate_practice_export(pid, seed=99, variant="complete")
    r2 = svc.receive_delivery(CLINIC, "sftp", [ReceivedExport(pid, exp2.raw_bytes())])
    assert r2.practices[0].disposition == "superseded"
    pd = repo.get_practice_database_by_practice(pid)
    assert pd["receipt_state"] == "superseded"


def test_receipt_precedes_counsel_gate(repo, tmp_path):
    """Vault receipt proceeds with no counsel signoff (the §6.3 backup)."""
    svc = ReceiptService(repo, vault=SimVault(root=str(tmp_path)))
    pid, exp = _export()
    assert repo.has_counsel_signoff(pid) is False
    receipt = svc.receive_delivery(CLINIC, "sftp", [ReceivedExport(pid, exp.raw_bytes())])
    assert receipt.practices[0].disposition == "received"
    assert repo.get_practice_database_by_practice(pid)["state"] == "received"
