"""Feature 011 — T004 HouseholdRepository.

CRUD + append-only ops for the 13 net-new relationship tables on **local
PostgreSQL via docker-compose** (NOT SQLite — data-model.md's "Postgres + RLS,
not SQLite" mandate). Reuses the 010 ``VoiceRepository`` pattern exactly:
SQLAlchemy Core, ``VOICE_DATABASE_URL`` connection convention (the shared
``vetagent-voice-pg`` container, host port 5433 — R8: never another port), and
an idempotent-additive ``init_db()``.

RLS stand-in: single-clinic app-level ``clinic_id`` / ``party_id`` scoping (the
plan's VP-1-slip degradation, same posture as 010).

Append-only audit spine (Constitution I) — UPDATE/DELETE rejected at the DB
level by a plpgsql trigger on the 5 audit tables:
``identity_resolution_event``, ``verification_challenge``,
``reveal_decision_log``, ``consent_event``, ``inbound_message``.

``contact_consent`` carries ``UNIQUE(party_id, channel)`` (one current row per
channel); ``contact_identifier`` carries the lookup index
``(clinic_id, id_type, value_normalized)`` — a lookup returns ALL matching rows
(the candidate set), never ``LIMIT 1``.
"""
from __future__ import annotations

import os
from typing import Any, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer, MetaData, String, Table, Text,
    UniqueConstraint, create_engine, insert, select, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

# Append-only tables — UPDATE/DELETE rejected at the DB level.
APPEND_ONLY_TABLES = (
    "identity_resolution_event",
    "verification_challenge",
    "reveal_decision_log",
    "consent_event",
    "inbound_message",
)

_DEFAULT_URL = "postgresql+psycopg2://voice:voice@localhost:5433/voice"


def default_db_url() -> str:
    return os.environ.get("VOICE_DATABASE_URL", _DEFAULT_URL).strip() or _DEFAULT_URL


def _json_type():
    """JSONB on Postgres; plain JSON elsewhere (SQLite fallback config)."""
    from sqlalchemy import JSON
    return JSON().with_variant(JSONB(), "postgresql")


class HouseholdRepository:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or default_db_url()
        self.engine: Engine = create_engine(self.db_url, future=True)
        self.metadata = MetaData()
        self.tables: dict[str, Table] = {}
        self._define_tables()

    # ------------------------------------------------------------------ #
    #  Schema — 13 tables
    # ------------------------------------------------------------------ #
    def _define_tables(self) -> None:
        md = self.metadata
        J = _json_type

        self.tables["household"] = Table(
            "household", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False, unique=True),
            Column("display_name", Text, default=""),
            Column("review_status", String, default="confirmed"),
            Column("created_at", DateTime(timezone=True)),
            Column("updated_at", DateTime(timezone=True)),
        )

        self.tables["household_contact"] = Table(
            "household_contact", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("household_id", String, nullable=False, index=True),
            Column("pims_client_id", String, nullable=True),
            Column("entity_ref", String, nullable=False),
            Column("display_name", Text, default=""),
            Column("household_role", String, default="co_owner"),
            Column("active", Boolean, default=True),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["contact_identifier"] = Table(
            "contact_identifier", md,
            Column("id", String, primary_key=True),
            Column("party_id", String, nullable=False, index=True),
            Column("clinic_id", String, nullable=False),
            Column("id_type", String, nullable=False),
            Column("value_normalized", String, nullable=False),
            Column("value_raw", Text, default=""),
            Column("is_primary", Boolean, default=False),
            Column("source", String, default="pims"),
            Column("created_at", DateTime(timezone=True)),
            # The lookup index — returns the FULL candidate set, never LIMIT 1.
            Index("ix_contact_identifier_lookup",
                  "clinic_id", "id_type", "value_normalized"),
        )

        self.tables["patient_household_link"] = Table(
            "patient_household_link", md,
            Column("id", String, primary_key=True),
            Column("patient_id", String, nullable=False, index=True),
            Column("household_id", String, nullable=False, index=True),
            Column("clinic_id", String, nullable=False),
            Column("pims_patient_id", String, nullable=True),
            Column("entity_ref", String, nullable=False),
            Column("status", String, default="active"),
            Column("display_name", Text, default=""),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["identity_resolution_event"] = Table(
            "identity_resolution_event", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("channel", String, default="voice"),
            Column("inbound_identifier_normalized", String),
            Column("identifier_type", String),
            Column("candidate_set_json", J()),
            Column("match_count", Integer, default=0),
            Column("outcome", String),
            Column("confirmed_party_id", String, nullable=True),
            Column("resolved_at", DateTime(timezone=True)),
        )

        self.tables["household_review_queue"] = Table(
            "household_review_queue", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("proposal_type", String, nullable=False),
            Column("subject_refs_json", J()),
            Column("evidence_json", J()),
            Column("status", String, default="pending"),
            Column("reviewed_by", String, nullable=True),
            Column("reviewed_at", DateTime(timezone=True)),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["verification_challenge"] = Table(
            "verification_challenge", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("call_session_id", String, nullable=True),
            Column("party_id", String, nullable=True),
            Column("action_requested", String),
            Column("sensitivity_tier", String),
            Column("factors_required", Integer, default=1),
            Column("factors_presented_json", J()),
            Column("outcome", String),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["memory_scoping_policy"] = Table(
            "memory_scoping_policy", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("version", String),
            Column("policy_yaml", Text),
            Column("signed_by", String, nullable=True),
            Column("active", Boolean, default=False),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["reveal_decision_log"] = Table(
            "reveal_decision_log", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("interaction_ref", String, default=""),
            Column("audience", String),
            Column("fact_kind", String),
            Column("fact_class", String, nullable=True),
            Column("entity_ref", String, nullable=True),
            Column("decision", String),
            Column("rule_matched", String, nullable=True),
            Column("reason", String),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["contact_consent"] = Table(
            "contact_consent", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("party_id", String, nullable=False),
            Column("channel", String, nullable=False),
            Column("ai_contact_allowed", Boolean, default=True),
            Column("source", String, default="staff"),
            Column("changed_at", DateTime(timezone=True)),
            Column("changed_by", String, default="system"),
            UniqueConstraint("party_id", "channel", name="uq_contact_consent_party_channel"),
        )

        self.tables["consent_event"] = Table(
            "consent_event", md,
            Column("id", String, primary_key=True),
            Column("party_id", String, nullable=False, index=True),
            Column("clinic_id", String, nullable=False),
            Column("channel", String, nullable=False),
            Column("action", String),
            Column("keyword", String, nullable=True),
            Column("inbound_message_id", String, nullable=True),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["inbound_message"] = Table(
            "inbound_message", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("channel", String, default="sms"),
            Column("from_identifier_normalized", String),
            Column("body", Text, default=""),
            Column("matched_keyword", String, nullable=True),
            Column("action_taken", String, default="none"),
            Column("received_at", DateTime(timezone=True)),
        )

        self.tables["clinic_staff_role"] = Table(
            "clinic_staff_role", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("staff_user_id", String, nullable=False),
            Column("role", String),
            Column("active", Boolean, default=True),
            Column("created_at", DateTime(timezone=True)),
        )

    # ------------------------------------------------------------------ #
    #  init_db (idempotent-additive)
    # ------------------------------------------------------------------ #
    def init_db(self) -> None:
        """Create the 13 tables + append-only triggers (idempotent)."""
        self.metadata.create_all(self.engine)
        if self.engine.dialect.name == "postgresql":
            self._install_append_only_triggers()

    def _install_append_only_triggers(self) -> None:
        ddl = [
            """
            CREATE OR REPLACE FUNCTION relationship_reject_mutation()
            RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'append-only violation: % on % is rejected',
                    TG_OP, TG_TABLE_NAME;
            END;
            $$ LANGUAGE plpgsql;
            """
        ]
        for tbl in APPEND_ONLY_TABLES:
            ddl.append(f"DROP TRIGGER IF EXISTS trg_{tbl}_append_only ON {tbl};")
            ddl.append(
                f"CREATE TRIGGER trg_{tbl}_append_only "
                f"BEFORE UPDATE OR DELETE ON {tbl} "
                f"FOR EACH ROW EXECUTE FUNCTION relationship_reject_mutation();"
            )
        with self.engine.begin() as conn:
            for stmt in ddl:
                conn.execute(text(stmt))

    # ------------------------------------------------------------------ #
    #  Generic helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _dump(model_or_dict: Any) -> dict:
        if hasattr(model_or_dict, "model_dump"):
            d = model_or_dict.model_dump()
        else:
            d = dict(model_or_dict)
        for k, v in list(d.items()):
            if hasattr(v, "value") and not isinstance(v, (str, int, bool)):
                d[k] = v.value
        return d

    def _insert(self, table_name: str, row: dict) -> dict:
        tbl = self.tables[table_name]
        cols = {c.name for c in tbl.columns}
        payload = {k: v for k, v in row.items() if k in cols}
        with self.engine.begin() as conn:
            conn.execute(insert(tbl).values(**payload))
        return payload

    def _select_where(self, table_name: str, **eq) -> list[dict]:
        tbl = self.tables[table_name]
        stmt = select(tbl)
        for k, v in eq.items():
            stmt = stmt.where(tbl.c[k] == v)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    # ------------------------------------------------------------------ #
    #  household / contact / identifier / patient link (mutable core)
    # ------------------------------------------------------------------ #
    def create_household(self, m: Any) -> dict:
        return self._insert("household", self._dump(m))

    def get_household(self, household_id: str, clinic_id: Optional[str] = None) -> Optional[dict]:
        rows = self._select_where("household", id=household_id) if clinic_id is None \
            else self._select_where("household", id=household_id, clinic_id=clinic_id)
        return rows[0] if rows else None

    def create_contact(self, m: Any) -> dict:
        return self._insert("household_contact", self._dump(m))

    def get_contacts_for_household(self, household_id: str) -> list[dict]:
        return self._select_where("household_contact", household_id=household_id)

    def get_contact(self, party_id: str) -> Optional[dict]:
        rows = self._select_where("household_contact", id=party_id)
        return rows[0] if rows else None

    def create_identifier(self, m: Any) -> dict:
        return self._insert("contact_identifier", self._dump(m))

    def find_identifiers(self, clinic_id: str, id_type: str, value_normalized: str) -> list[dict]:
        """Return ALL contact_identifier rows matching the normalized value —
        the FULL candidate set. There is deliberately no ``LIMIT 1`` path."""
        return self._select_where(
            "contact_identifier",
            clinic_id=clinic_id, id_type=id_type, value_normalized=value_normalized,
        )

    def get_identifiers_for_party(self, party_id: str) -> list[dict]:
        return self._select_where("contact_identifier", party_id=party_id)

    def create_patient_link(self, m: Any) -> dict:
        return self._insert("patient_household_link", self._dump(m))

    def get_patients_for_household(self, household_id: str) -> list[dict]:
        return self._select_where("patient_household_link", household_id=household_id)

    def count_patient_links(self) -> int:
        tbl = self.tables["patient_household_link"]
        with self.engine.connect() as conn:
            return conn.execute(select(text("count(*)")).select_from(tbl)).scalar() or 0

    def count_distinct_linked_patients(self) -> int:
        tbl = self.tables["patient_household_link"]
        with self.engine.connect() as conn:
            return conn.execute(
                select(text("count(distinct patient_id)")).select_from(tbl)
            ).scalar() or 0

    # ------------------------------------------------------------------ #
    #  Append-only audit writes
    # ------------------------------------------------------------------ #
    def append_resolution_event(self, m: Any) -> dict:
        return self._insert("identity_resolution_event", self._dump(m))

    def get_resolution_events(self, clinic_id: str) -> list[dict]:
        return self._select_where("identity_resolution_event", clinic_id=clinic_id)

    def append_verification_challenge(self, m: Any) -> dict:
        return self._insert("verification_challenge", self._dump(m))

    def get_verification_challenges(self, clinic_id: str) -> list[dict]:
        return self._select_where("verification_challenge", clinic_id=clinic_id)

    def append_reveal_decision(self, m: Any) -> dict:
        return self._insert("reveal_decision_log", self._dump(m))

    def get_reveal_decisions(self, clinic_id: str) -> list[dict]:
        return self._select_where("reveal_decision_log", clinic_id=clinic_id)

    def append_consent_event(self, m: Any) -> dict:
        return self._insert("consent_event", self._dump(m))

    def get_consent_events(self, party_id: str) -> list[dict]:
        return self._select_where("consent_event", party_id=party_id)

    def append_inbound_message(self, m: Any) -> dict:
        return self._insert("inbound_message", self._dump(m))

    def get_inbound_messages(self, clinic_id: str) -> list[dict]:
        return self._select_where("inbound_message", clinic_id=clinic_id)

    # ------------------------------------------------------------------ #
    #  household_review_queue (mutable — status set by staff later)
    # ------------------------------------------------------------------ #
    def create_review_item(self, m: Any) -> dict:
        return self._insert("household_review_queue", self._dump(m))

    def get_review_items(self, clinic_id: str, status: Optional[str] = None) -> list[dict]:
        if status is None:
            return self._select_where("household_review_queue", clinic_id=clinic_id)
        return self._select_where("household_review_queue", clinic_id=clinic_id, status=status)

    # ------------------------------------------------------------------ #
    #  contact_consent (upsert of current state; history in consent_event)
    # ------------------------------------------------------------------ #
    def upsert_consent(self, m: Any) -> dict:
        from sqlalchemy import update as _update
        row = self._dump(m)
        tbl = self.tables["contact_consent"]
        cols = {c.name for c in tbl.columns}
        payload = {k: v for k, v in row.items() if k in cols}
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(tbl.c.id).where(
                    tbl.c.party_id == payload["party_id"],
                    tbl.c.channel == payload["channel"],
                )
            ).first()
            if existing:
                upd = {k: v for k, v in payload.items() if k not in ("id",)}
                conn.execute(_update(tbl).where(tbl.c.id == existing[0]).values(**upd))
            else:
                conn.execute(insert(tbl).values(**payload))
        return payload

    def get_consent(self, party_id: str, channel: str) -> Optional[dict]:
        rows = self._select_where("contact_consent", party_id=party_id, channel=channel)
        return rows[0] if rows else None

    # ------------------------------------------------------------------ #
    #  memory_scoping_policy / clinic_staff_role
    # ------------------------------------------------------------------ #
    def create_scoping_policy(self, m: Any) -> dict:
        return self._insert("memory_scoping_policy", self._dump(m))

    def get_active_scoping_policy(self, clinic_id: str) -> Optional[dict]:
        rows = self._select_where("memory_scoping_policy", clinic_id=clinic_id, active=True)
        return rows[0] if rows else None

    def create_staff_role(self, m: Any) -> dict:
        return self._insert("clinic_staff_role", self._dump(m))

    def get_staff_role(self, staff_user_id: str) -> Optional[dict]:
        rows = self._select_where("clinic_staff_role", staff_user_id=staff_user_id)
        return rows[0] if rows else None
