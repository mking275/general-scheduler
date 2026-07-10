"""Feature 010 — Vera Voice: T004 VoiceRepository.

CRUD + append-only ops for the 8 voice tables on **local PostgreSQL via
docker-compose** (NOT SQLite — matches data-model.md's "Postgres + RLS, not
SQLite" mandate). RLS-ready: in the single-clinic pilot build, full RLS is
stood in for by **app-level ``clinic_id`` / ``party_id`` scoping** (the plan's
VP-1-slip degradation).

Append-only guarantee (FR-021/024): ``call_turn`` and ``call_transcript`` reject
any UPDATE/DELETE at the DB level via a plpgsql trigger — enforced below the
application, not by convention.

The refill guard (FR-022/023): ``CHECK (status = 'draft_vet_review')`` on
``refill_request_draft`` makes the auto-approve status unrepresentable.

Connection string comes from ``VOICE_DATABASE_URL`` (default the docker-compose
Postgres on host port 5433).
"""
from __future__ import annotations

import os
from typing import Any, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Integer, MetaData, Numeric,
    String, Table, Text, create_engine, insert, select, text, update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

# Append-only tables — UPDATE/DELETE rejected at the DB level.
APPEND_ONLY_TABLES = ("call_turn", "call_transcript")

_DEFAULT_URL = "postgresql+psycopg2://voice:voice@localhost:5433/voice"


def default_db_url() -> str:
    return os.environ.get("VOICE_DATABASE_URL", _DEFAULT_URL).strip() or _DEFAULT_URL


def _json_type():
    """JSONB on Postgres; plain JSON elsewhere (SQLite fallback config)."""
    from sqlalchemy import JSON
    return JSON().with_variant(JSONB(), "postgresql")


class VoiceRepository:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or default_db_url()
        self.engine: Engine = create_engine(self.db_url, future=True)
        self.metadata = MetaData()
        self.tables: dict[str, Table] = {}
        self._define_tables()

    # ------------------------------------------------------------------ #
    #  Schema
    # ------------------------------------------------------------------ #
    def _define_tables(self) -> None:
        md = self.metadata
        J = _json_type

        self.tables["call_session"] = Table(
            "call_session", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),   # RLS scope
            Column("inbound_number", Text),
            Column("party_id", String, nullable=True, index=True),
            Column("verification_state", String, default="unverified"),
            Column("channel_binding_id", String, nullable=True),
            Column("started_at", DateTime(timezone=True)),
            Column("answered_at", DateTime(timezone=True)),
            Column("ended_at", DateTime(timezone=True)),
            Column("call_outcome", String, nullable=True),
            Column("containment_flag", Boolean, default=False),
            Column("model_provider", String, nullable=True),
            Column("degraded_mode", Boolean, default=False),
            Column("session_resume_count", Integer, default=0),
            Column("cost_usd", Numeric(8, 4), nullable=True),
            Column("consent_recorded_at", DateTime(timezone=True)),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["call_turn"] = Table(
            "call_turn", md,
            Column("id", String, primary_key=True),
            Column("call_session_id", String, nullable=False, index=True),
            Column("seq", Integer, nullable=False),
            Column("role", String),
            Column("text", Text, default=""),
            Column("is_final", Boolean, default=True),
            Column("started_at", DateTime(timezone=True)),
            Column("latency_ms", Integer, nullable=True),
            Column("barge_in", Boolean, default=False),
            Column("protocol_flag", String, nullable=True),
            Column("gate_decision", String, nullable=True),
            Column("tool_calls_json", J()),
        )

        self.tables["call_transcript"] = Table(
            "call_transcript", md,
            Column("id", String, primary_key=True),
            Column("call_session_id", String, nullable=False, index=True),
            Column("full_text", Text, default=""),
            Column("audio_ref", Text, nullable=True),
            Column("consent_record", J()),
            Column("vendor_no_training_attestation", Text, nullable=True),
            Column("retained_until", DateTime(timezone=True)),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["escalation_event"] = Table(
            "escalation_event", md,
            Column("id", String, primary_key=True),
            Column("call_session_id", String, nullable=False, index=True),
            Column("trigger", String),
            Column("protocol_state", String, nullable=True),
            Column("triggered_at", DateTime(timezone=True)),
            Column("transfer_target_id", String, nullable=True),
            Column("whisper_summary", Text, nullable=True),
            Column("transfer_outcome", String, nullable=True),
            Column("fallback_path", String, nullable=True),
            Column("watchdog_fired", Boolean, default=False),
            Column("resolved_at", DateTime(timezone=True)),
            Column("audit_retained_until", DateTime(timezone=True)),
        )

        self.tables["refill_request_draft"] = Table(
            "refill_request_draft", md,
            Column("id", String, primary_key=True),
            Column("call_session_id", String, nullable=False, index=True),
            Column("party_id", String, nullable=False),
            Column("patient_ref", Text),
            Column("drug_name_asserted", Text),
            Column("status", String, nullable=False, default="draft_vet_review"),
            Column("refills_remaining_at_capture", Integer, nullable=True),
            Column("created_at", DateTime(timezone=True)),
            # FR-022/023: auto-approve is UNREPRESENTABLE on this table.
            CheckConstraint("status = 'draft_vet_review'", name="ck_refill_draft_only"),
        )

        self.tables["clinic_voice_config"] = Table(
            "clinic_voice_config", md,
            Column("clinic_id", String, primary_key=True),
            Column("after_hours_window", J()),
            Column("disclosure_script", J()),
            Column("triage_protocol_id", String, nullable=True),
            Column("er_directory_ref", Text, nullable=True),
            Column("voice_params", J()),
            Column("model_provider_pref", String, default="gemini_live"),
            Column("max_hold_ms", Integer, default=8000),
            Column("filler_script", Text, default=""),
            Column("low_confidence_threshold", Numeric, default=0.6),
            Column("slo_latency_ms", Integer, default=3000),
            Column("vendor_no_training_attestation", Text, nullable=True),
            Column("updated_at", DateTime(timezone=True)),
        )

        self.tables["on_call_target"] = Table(
            "on_call_target", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("label", Text),
            Column("phone", Text),
            Column("type", String, default="on_call_vet"),
            Column("priority", Integer, default=0),
            Column("active_window", J()),
            Column("active", Boolean, default=True),
            Column("created_at", DateTime(timezone=True)),
        )

        self.tables["triage_protocol"] = Table(
            "triage_protocol", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("version", String),
            Column("config_yaml", Text),
            Column("signed_by", String, nullable=True),
            Column("signed_at", DateTime(timezone=True)),
            Column("active", Boolean, default=False),
            Column("created_at", DateTime(timezone=True)),
        )

    def init_db(self) -> None:
        """Create the 8 tables + append-only triggers (idempotent)."""
        self.metadata.create_all(self.engine)
        if self.engine.dialect.name == "postgresql":
            self._install_append_only_triggers()

    def _install_append_only_triggers(self) -> None:
        ddl = [
            """
            CREATE OR REPLACE FUNCTION voice_reject_mutation()
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
                f"FOR EACH ROW EXECUTE FUNCTION voice_reject_mutation();"
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
        # Coerce Enums to their string values.
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

    # ------------------------------------------------------------------ #
    #  call_session (mutable)
    # ------------------------------------------------------------------ #
    def create_call_session(self, session_model: Any) -> dict:
        return self._insert("call_session", self._dump(session_model))

    def get_call_session(self, session_id: str, clinic_id: Optional[str] = None) -> Optional[dict]:
        tbl = self.tables["call_session"]
        stmt = select(tbl).where(tbl.c.id == session_id)
        if clinic_id is not None:                       # app-level RLS stand-in
            stmt = stmt.where(tbl.c.clinic_id == clinic_id)
        with self.engine.connect() as conn:
            r = conn.execute(stmt).mappings().first()
        return dict(r) if r else None

    def update_call_session(self, session_id: str, **fields) -> None:
        tbl = self.tables["call_session"]
        cols = {c.name for c in tbl.columns}
        payload = {k: (v.value if hasattr(v, "value") and not isinstance(v, (str, int, bool)) else v)
                   for k, v in fields.items() if k in cols}
        with self.engine.begin() as conn:
            conn.execute(update(tbl).where(tbl.c.id == session_id).values(**payload))

    # ------------------------------------------------------------------ #
    #  Append-only writes
    # ------------------------------------------------------------------ #
    def append_call_turn(self, turn_model: Any) -> dict:
        return self._insert("call_turn", self._dump(turn_model))

    def get_turns(self, call_session_id: str) -> list[dict]:
        tbl = self.tables["call_turn"]
        stmt = select(tbl).where(tbl.c.call_session_id == call_session_id).order_by(tbl.c.seq)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    def append_transcript(self, transcript_model: Any) -> dict:
        return self._insert("call_transcript", self._dump(transcript_model))

    def get_transcript(self, call_session_id: str) -> Optional[dict]:
        tbl = self.tables["call_transcript"]
        stmt = select(tbl).where(tbl.c.call_session_id == call_session_id)
        with self.engine.connect() as conn:
            r = conn.execute(stmt).mappings().first()
        return dict(r) if r else None

    # ------------------------------------------------------------------ #
    #  escalation_event (mutable — resolved_at set later)
    # ------------------------------------------------------------------ #
    def create_escalation_event(self, ev_model: Any) -> dict:
        return self._insert("escalation_event", self._dump(ev_model))

    def get_escalation_events(self, call_session_id: str) -> list[dict]:
        tbl = self.tables["escalation_event"]
        stmt = select(tbl).where(tbl.c.call_session_id == call_session_id)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    # ------------------------------------------------------------------ #
    #  refill_request_draft (CHECK-guarded)
    # ------------------------------------------------------------------ #
    def create_refill_draft(self, draft_model: Any) -> dict:
        return self._insert("refill_request_draft", self._dump(draft_model))

    def get_refill_drafts(self, call_session_id: str) -> list[dict]:
        tbl = self.tables["refill_request_draft"]
        stmt = select(tbl).where(tbl.c.call_session_id == call_session_id)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    # ------------------------------------------------------------------ #
    #  Config / targets / protocol
    # ------------------------------------------------------------------ #
    def upsert_clinic_voice_config(self, cfg_model: Any) -> dict:
        row = self._dump(cfg_model)
        tbl = self.tables["clinic_voice_config"]
        cols = {c.name for c in tbl.columns}
        payload = {k: v for k, v in row.items() if k in cols}
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(tbl.c.clinic_id).where(tbl.c.clinic_id == payload["clinic_id"])
            ).first()
            if existing:
                conn.execute(update(tbl).where(tbl.c.clinic_id == payload["clinic_id"]).values(**payload))
            else:
                conn.execute(insert(tbl).values(**payload))
        return payload

    def get_clinic_voice_config(self, clinic_id: str) -> Optional[dict]:
        tbl = self.tables["clinic_voice_config"]
        with self.engine.connect() as conn:
            r = conn.execute(select(tbl).where(tbl.c.clinic_id == clinic_id)).mappings().first()
        return dict(r) if r else None

    def create_on_call_target(self, target_model: Any) -> dict:
        return self._insert("on_call_target", self._dump(target_model))

    def get_on_call_targets(self, clinic_id: str, active_only: bool = True) -> list[dict]:
        tbl = self.tables["on_call_target"]
        stmt = select(tbl).where(tbl.c.clinic_id == clinic_id)
        if active_only:
            stmt = stmt.where(tbl.c.active.is_(True))
        stmt = stmt.order_by(tbl.c.priority)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    def create_triage_protocol(self, proto_model: Any) -> dict:
        return self._insert("triage_protocol", self._dump(proto_model))

    def get_active_triage_protocol(self, clinic_id: str) -> Optional[dict]:
        tbl = self.tables["triage_protocol"]
        stmt = select(tbl).where(tbl.c.clinic_id == clinic_id, tbl.c.active.is_(True))
        with self.engine.connect() as conn:
            r = conn.execute(stmt).mappings().first()
        return dict(r) if r else None
