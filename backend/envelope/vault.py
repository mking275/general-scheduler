"""Feature 009 — T009 clinic-owned encrypted-at-rest vault + receipt.

On receipt, each practice database export is written to the vault and a
chain-of-custody record (source, delivery timestamp, byte-count, **checksum**)
is persisted **before any parsing runs** (FR-001). The vault is a sim
encrypted-at-rest store in this build (Fernet); the live clinic-owned vault +
secure-file-transfer intake is the config swap behind ``sim.resolve_vault``
(T008). Receipt is permitted **before** the counsel gate (a §6.3 backup); it
reuses the T004 wrap-full-transaction provisioning so a rolled-back receipt
leaves **zero** partial vault/lineage rows (the FarmAgent orphan-account fix).

A duplicate/superseding delivery of the same practice is reconciled against the
earlier receipt **via checksum**, not blindly re-loaded: an identical checksum
is a ``duplicate`` (no re-load); a different checksum ``supersedes`` (the earlier
receipt is marked ``superseded`` and a fresh receipt is recorded).
"""
from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from cryptography.fernet import Fernet

from backend.envelope.state_machine import StateMachine
from backend.models import ChainOfCustody, Delivery, PracticeDatabase, PracticeState


# --------------------------------------------------------------------------- #
#  SimVault — encrypted-at-rest store (Fernet)
# --------------------------------------------------------------------------- #
class SimVault:
    """A sim encrypted-at-rest vault. Data is Fernet-encrypted before it is
    stored (on disk under ``root`` when given, else in memory). The stored bytes
    are ciphertext — never the plaintext export."""

    def __init__(self, root: Optional[str] = None, key: Optional[bytes] = None):
        self.root = root
        if root:
            os.makedirs(root, exist_ok=True)
        # A deterministic per-vault key derived from root (sim only); the live
        # vault manages its own keys (KMS) behind the seam.
        if key is None:
            seed = (root or "envelope-sim-vault").encode("utf-8")
            key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
        self._fernet = Fernet(key)
        self._mem: dict[str, bytes] = {}

    def _path(self, ref: str) -> str:
        return os.path.join(self.root, f"{ref}.enc") if self.root else ref

    def write(self, practice_id: str, data: bytes) -> str:
        """Encrypt + store; return the vault object ref."""
        ref = f"vault/{practice_id}/{hashlib.sha256(data).hexdigest()[:16]}"
        cipher = self._fernet.encrypt(data)
        if self.root:
            path = self._path(ref)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(cipher)
        else:
            self._mem[ref] = cipher
        return ref

    def stored_bytes(self, ref: str) -> bytes:
        """The raw at-rest (ciphertext) bytes — for the encrypted-at-rest proof."""
        if self.root:
            with open(self._path(ref), "rb") as f:
                return f.read()
        return self._mem[ref]

    def read(self, ref: str) -> bytes:
        """Decrypt + return the plaintext export (internal use, post-counsel)."""
        return self._fernet.decrypt(self.stored_bytes(ref))

    def exists(self, ref: str) -> bool:
        return os.path.exists(self._path(ref)) if self.root else ref in self._mem


# --------------------------------------------------------------------------- #
#  Receipt orchestration
# --------------------------------------------------------------------------- #
@dataclass
class ReceivedExport:
    """One practice's delivered export bytes (sim: fixture ``raw_bytes()``)."""
    practice_id: str
    data: bytes
    checksum: Optional[str] = None

    def compute_checksum(self) -> str:
        return self.checksum or hashlib.sha256(self.data).hexdigest()


@dataclass
class PracticeReceipt:
    practice_id: str
    disposition: str                  # "received" | "duplicate" | "superseded"
    vault_object_ref: Optional[str]
    checksum: str
    practice_database_id: Optional[str] = None


@dataclass
class DeliveryReceipt:
    delivery_id: str
    practices: list[PracticeReceipt] = field(default_factory=list)


class ReceiptService:
    """Receives a delivery under chain of custody: vault write + chain-of-custody
    record before any parse, all provisioned in one transaction."""

    def __init__(self, repo, vault: Optional[SimVault] = None):
        self.repo = repo
        if vault is None:
            from backend.envelope.sim import resolve_vault
            vault = resolve_vault()
        self.vault = vault
        self.sm = StateMachine(repo)

    def receive_delivery(self, clinic_id: str, source: str,
                         exports: list[ReceivedExport],
                         delivery_timestamp: Optional[str] = None) -> DeliveryReceipt:
        ts = delivery_timestamp or datetime.now().isoformat()

        # Reconcile each practice against any earlier receipt via checksum first
        # (no vault write / DB row for an exact duplicate).
        plan: list[tuple[ReceivedExport, str, str]] = []   # (export, checksum, disposition)
        for exp in exports:
            checksum = exp.compute_checksum()
            existing = self.repo.get_practice_database_by_practice(exp.practice_id)
            if existing is None:
                disposition = "received"
            elif existing.get("checksum") == checksum:
                disposition = "duplicate"          # identical — do not re-load
            else:
                disposition = "superseded"         # newer bytes supersede the earlier receipt
            plan.append((exp, checksum, disposition))

        receipts: list[PracticeReceipt] = []
        did = f"delivery-{hashlib.sha256((source + ts).encode()).hexdigest()[:12]}"

        # write vault objects for the practices that need provisioning (before
        # any parse) — physical blob first so the DB row carries a real ref.
        vault_refs: dict[str, str] = {}
        for exp, checksum, disposition in plan:
            if disposition == "duplicate":
                continue
            vault_refs[exp.practice_id] = self.vault.write(exp.practice_id, exp.data)

        provisioned = [(exp, cs, disp) for (exp, cs, disp) in plan if disp != "duplicate"]

        # mark superseded predecessors (mutable receipt_state; not append-only)
        for exp, checksum, disposition in provisioned:
            if disposition == "superseded":
                self.repo.set_practice_state(exp.practice_id,
                                             PracticeState.RECEIVED.value,
                                             receipt_state="superseded")

        # THE ATOMIC RECEIPT — delivery + practice_database + chain-of-custody.
        pd_ids: dict[str, str] = {}
        if provisioned:
            with self.repo.receipt_txn() as txn:
                txn.insert_delivery(Delivery(
                    id=did, clinic_id=clinic_id, source=source,
                    delivery_timestamp=ts, practice_ids=[e.practice_id for e, _, _ in provisioned],
                ))
                for exp, checksum, disposition in provisioned:
                    pd = PracticeDatabase(
                        clinic_id=clinic_id, practice_id=exp.practice_id, delivery_id=did,
                        receipt_state="received", state=PracticeState.RECEIVED,
                        vault_object_ref=vault_refs[exp.practice_id], checksum=checksum,
                    )
                    pd_ids[exp.practice_id] = pd.id
                    txn.insert_practice_database(pd)
                    txn.insert_chain_of_custody(ChainOfCustody(
                        clinic_id=clinic_id, practice_id=exp.practice_id,
                        practice_database_id=pd.id, source=source,
                        delivery_timestamp=ts, byte_count=len(exp.data),
                        checksum=checksum, parsed=False,   # NO parser has run
                    ))

        # record the initial received transition via the state machine (single
        # write path); vault receipt precedes and is unaffected by the counsel gate.
        for exp, checksum, disposition in provisioned:
            self.sm.receive(exp.practice_id, clinic_id,
                            reason=f"vault receipt ({disposition})")

        for exp, checksum, disposition in plan:
            receipts.append(PracticeReceipt(
                practice_id=exp.practice_id, disposition=disposition,
                vault_object_ref=vault_refs.get(exp.practice_id),
                checksum=checksum, practice_database_id=pd_ids.get(exp.practice_id),
            ))
        return DeliveryReceipt(delivery_id=did, practices=receipts)
