"""Feature 009 — T004 OnboardingRepository acceptance.

- init_db() creates the tables on the docker-compose Postgres with FORCE ROW
  LEVEL SECURITY on each onboarding-control table.
- any UPDATE/DELETE on a logged chain-of-custody / state-transition row is
  rejected (append-only spine).
- a receipt transaction raised mid-write rolls back with ZERO vault or lineage
  rows persisted (orphan-receipt guard).
"""
import uuid

import pytest
from sqlalchemy import text

from backend.envelope.onboarding_repository import (
    CANONICAL_TABLES, ONBOARDING_CONTROL_TABLES,
)
from backend.models import ChainOfCustody, Delivery, PracticeDatabase, StateTransition


def _pid() -> str:
    return f"p-{uuid.uuid4().hex[:8]}"


def test_force_rls_on_every_onboarding_control_table(repo):
    for tbl in ONBOARDING_CONTROL_TABLES:
        assert repo.force_rls_enabled(tbl), f"FORCE RLS not set on {tbl}"
    # canonical 009-owned tables are also protected
    for tbl in CANONICAL_TABLES:
        assert repo.force_rls_enabled(tbl), f"FORCE RLS not set on {tbl}"


def test_chain_of_custody_is_append_only(repo):
    clinic, pid = "goldsmith", _pid()
    pd = PracticeDatabase(clinic_id=clinic, practice_id=pid, delivery_id="d1")
    repo.create_practice_database(pd)
    cc = ChainOfCustody(clinic_id=clinic, practice_id=pid,
                        practice_database_id=pd.id, source="sftp", checksum="abc")
    repo.append_chain_of_custody(cc)
    tbl = repo.tables["chain_of_custody"]
    with pytest.raises(Exception):
        with repo.engine.begin() as conn:
            conn.execute(text(f"UPDATE chain_of_custody SET checksum='x' WHERE id=:i"), {"i": cc.id})
    with pytest.raises(Exception):
        with repo.engine.begin() as conn:
            conn.execute(text(f"DELETE FROM chain_of_custody WHERE id=:i"), {"i": cc.id})


def test_state_transition_is_append_only(repo):
    clinic, pid = "goldsmith", _pid()
    st = StateTransition(clinic_id=clinic, practice_id=pid, to_state="received")
    repo.append_state_transition(st)
    with pytest.raises(Exception):
        with repo.engine.begin() as conn:
            conn.execute(text(f"UPDATE state_transition SET reason='x' WHERE id=:i"), {"i": st.id})
    with pytest.raises(Exception):
        with repo.engine.begin() as conn:
            conn.execute(text(f"DELETE FROM state_transition WHERE id=:i"), {"i": st.id})


def test_orphan_receipt_guard_rolls_back_fully(repo):
    """A receipt transaction raised mid-write leaves ZERO delivery /
    practice_database / chain_of_custody rows (the FarmAgent orphan-account fix)."""
    clinic, pid = "goldsmith", _pid()
    did = f"d-{uuid.uuid4().hex[:8]}"
    delivery = Delivery(id=did, clinic_id=clinic, source="sftp", practice_ids=[pid])
    pd = PracticeDatabase(clinic_id=clinic, practice_id=pid, delivery_id=did)

    class _Boom(RuntimeError):
        pass

    with pytest.raises(_Boom):
        with repo.receipt_txn() as txn:
            txn.insert_delivery(delivery)
            txn.insert_practice_database(pd)
            # raise BEFORE the chain-of-custody write completes
            raise _Boom("mid-receipt failure")

    assert repo.get_delivery(did) is None, "orphan delivery persisted"
    assert repo.get_practice_database_by_practice(pid) is None, "orphan practice_database persisted"
    assert repo.get_chain_of_custody(pid) == [], "orphan chain-of-custody persisted"


def test_receipt_txn_commits_atomically(repo):
    clinic, pid = "goldsmith", _pid()
    did = f"d-{uuid.uuid4().hex[:8]}"
    delivery = Delivery(id=did, clinic_id=clinic, source="sftp", practice_ids=[pid])
    pd = PracticeDatabase(clinic_id=clinic, practice_id=pid, delivery_id=did)
    cc = ChainOfCustody(clinic_id=clinic, practice_id=pid,
                        practice_database_id=pd.id, source="sftp", checksum="abc")
    with repo.receipt_txn() as txn:
        txn.insert_delivery(delivery)
        txn.insert_practice_database(pd)
        txn.insert_chain_of_custody(cc)
    assert repo.get_delivery(did) is not None
    assert repo.get_practice_database_by_practice(pid) is not None
    assert len(repo.get_chain_of_custody(pid)) == 1
