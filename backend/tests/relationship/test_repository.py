"""T004 HouseholdRepository verification: 13 tables, append-only, UNIQUE."""
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError, InternalError

from backend.models import ContactConsent, ConsentEvent, RevealDecision, RevealDecisionLog

CLINIC = "clinic-test-011"


def _uid(p):
    return f"{p}-{uuid.uuid4().hex[:8]}"


def test_t004_init_db_creates_13_tables(repo):
    assert len(repo.tables) == 13
    with repo.engine.connect() as conn:
        for name in repo.tables:
            # each table is queryable
            conn.execute(text(f"SELECT count(*) FROM {name}"))


def test_t004_reveal_decision_log_append_only(repo):
    row = RevealDecisionLog(
        clinic_id=CLINIC, audience="owner", fact_kind="appointment",
        fact_class="schedule", decision=RevealDecision.REVEALED, reason="explicit_allow",
    )
    written = repo.append_reveal_decision(row)
    with pytest.raises((ProgrammingError, InternalError, Exception)) as exc:
        with repo.engine.begin() as conn:
            conn.execute(text("UPDATE reveal_decision_log SET decision='withheld' "
                              "WHERE id=:i"), {"i": written["id"]})
    assert "append-only" in str(exc.value)

    with pytest.raises(Exception) as exc2:
        with repo.engine.begin() as conn:
            conn.execute(text("DELETE FROM reveal_decision_log WHERE id=:i"),
                         {"i": written["id"]})
    assert "append-only" in str(exc2.value)


def test_t004_consent_event_append_only(repo):
    from backend.models import ConsentAction
    party = _uid("party")
    ev = ConsentEvent(party_id=party, clinic_id=CLINIC, channel="sms",
                      action=ConsentAction.OPT_OUT, keyword="STOP")
    written = repo.append_consent_event(ev)
    with pytest.raises(Exception) as exc:
        with repo.engine.begin() as conn:
            conn.execute(text("UPDATE consent_event SET action='opt_in' WHERE id=:i"),
                         {"i": written["id"]})
    assert "append-only" in str(exc.value)


def test_t004_contact_consent_unique_party_channel(repo):
    party = _uid("party")
    repo.upsert_consent(ContactConsent(clinic_id=CLINIC, party_id=party, channel="sms"))
    # A raw second-row insert for the same (party, channel) violates UNIQUE.
    dup = ContactConsent(clinic_id=CLINIC, party_id=party, channel="sms")
    with pytest.raises(IntegrityError):
        repo._insert("contact_consent", repo._dump(dup))
    # But upsert of the same key is idempotent (updates in place).
    repo.upsert_consent(ContactConsent(clinic_id=CLINIC, party_id=party, channel="sms",
                                       ai_contact_allowed=False))
    cur = repo.get_consent(party, "sms")
    assert cur["ai_contact_allowed"] is False
