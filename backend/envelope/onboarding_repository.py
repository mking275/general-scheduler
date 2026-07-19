"""Feature 009 — T004 OnboardingRepository.

CRUD + append-only ops for the net-new onboarding-control tables + the net-new
canonical financial/AR/ledger/payment + inventory tables, on **local PostgreSQL
via docker-compose** (the shared ``vetagent-voice-pg`` container, host port 5433,
``VOICE_DATABASE_URL`` convention — R8: never another port/container; NOT SQLite,
per data-model.md's "Postgres + RLS, not SQLite" mandate). Reuses the 011
``HouseholdRepository`` / 010 ``VoiceRepository`` pattern exactly: SQLAlchemy Core,
an idempotent-additive ``init_db()``, and a plpgsql append-only trigger spine.

SEC-20 posture — **FORCE ROW LEVEL SECURITY on every 009-owned table** (a
documented FarmAgent tuition: chain-of-custody / reconciliation / identity-audit
rows must never leak cross-tenant even to the table owner). A permissive
app-scope policy stands in for a full tenant policy in the single-clinic build
(the plan's VP-1-slip degradation, same posture as 010/011); app-level
``clinic_id`` / ``practice_id`` scoping does the real filtering in every method.
The real ``clinic_id``-keyed policy slots in at Pilot-Activation with no schema
change.

Append-only audit spine (Constitution I) — UPDATE/DELETE rejected at the DB
level by a plpgsql trigger on the audit tables (``delivery``,
``chain_of_custody``, ``counsel_signoff``, ``state_transition``,
``reconciliation_report``, ``identity_audit_corpus``, ``gap_notice``).

Orphan-receipt guard (the FarmAgent orphan-account fix) — receipt provisioning
**wraps the full transaction** via ``receipt_txn()``: a rolled-back receipt
leaves **zero** partial vault / lineage rows.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, MetaData, String, Table,
    Text, create_engine, insert, select, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection, Engine

# Onboarding-control tables — FORCE-RLS applied to these (SEC-20). The net-new
# canonical financial/inventory tables also get it (009-owned, practice-scoped).
ONBOARDING_CONTROL_TABLES = (
    "delivery",
    "practice_database",
    "chain_of_custody",
    "counsel_signoff",
    "scope_check",
    "format_profile",
    "state_transition",
    "completeness_result",
    "quality_assessment",
    "reconciliation_report",
    "identity_audit_corpus",
    "gap_notice",
    "practice_readiness",
    "batch_rollup",
)

CANONICAL_TABLES = (
    "canonical_record",
    "ledger_entry",
    "invoice_record",
    "payment_record",
    "ar_balance",
    "inventory_item",
    "unmapped_field_sidecar",
)

# Append-only audit tables — UPDATE/DELETE rejected at the DB level.
APPEND_ONLY_TABLES = (
    "delivery",
    "chain_of_custody",
    "counsel_signoff",
    "state_transition",
    "reconciliation_report",
    "identity_audit_corpus",
    "gap_notice",
)

_DEFAULT_URL = "postgresql+psycopg2://voice:voice@localhost:5433/voice"


def default_db_url() -> str:
    return os.environ.get("VOICE_DATABASE_URL", _DEFAULT_URL).strip() or _DEFAULT_URL


def _json_type():
    """JSONB on Postgres; plain JSON elsewhere (SQLite fallback config)."""
    from sqlalchemy import JSON
    return JSON().with_variant(JSONB(), "postgresql")


class OnboardingRepository:
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

        # ---- onboarding-control -------------------------------------- #
        self.tables["delivery"] = Table(
            "delivery", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("source", String, nullable=False),
            Column("delivery_timestamp", String),
            Column("byte_count", Integer, default=0),
            Column("checksum", String, default=""),
            Column("practice_ids", J()),
            Column("created_at", String),
        )

        self.tables["practice_database"] = Table(
            "practice_database", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("delivery_id", String, nullable=False, index=True),
            Column("receipt_state", String, default="received"),
            Column("state", String, default="received"),
            Column("vault_object_ref", String, nullable=True),
            Column("checksum", String, default=""),
            Column("created_at", String),
        )

        self.tables["chain_of_custody"] = Table(
            "chain_of_custody", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("practice_database_id", String, nullable=False, index=True),
            Column("source", String, nullable=False),
            Column("delivery_timestamp", String),
            Column("byte_count", Integer, default=0),
            Column("checksum", String, default=""),
            Column("vault_written_at", String),
            Column("parsed", Boolean, default=False),
            Column("created_at", String),
        )

        self.tables["counsel_signoff"] = Table(
            "counsel_signoff", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("signed_by", String, nullable=False),
            Column("signed_at", String),
            Column("structure_version", String, default="v1"),
            Column("scope", Text, default=""),
            Column("created_at", String),
        )

        self.tables["scope_check"] = Table(
            "scope_check", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("practice_database_id", String, nullable=False, index=True),
            Column("dispositions", J()),
            Column("created_at", String),
        )

        self.tables["format_profile"] = Table(
            "format_profile", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("practice_database_id", String, nullable=False, index=True),
            Column("entities", J()),
            Column("encodings", J()),
            Column("referential_relationships", J()),
            Column("export_variant", String, default=""),
            Column("unmapped_flags", J()),
            Column("created_at", String),
        )

        self.tables["state_transition"] = Table(
            "state_transition", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("from_state", String, nullable=True),
            Column("to_state", String, nullable=False),
            Column("reason", Text, default=""),
            Column("at", String),
        )

        self.tables["completeness_result"] = Table(
            "completeness_result", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("category_coverage", J()),
            Column("referential_integrity_findings", J()),
            Column("ar_balance_total", Float, default=0.0),
            Column("invoice_count", Integer, default=0),
            Column("payment_total", Float, default=0.0),
            Column("missing_or_short", J()),
            Column("created_at", String),
        )

        self.tables["quality_assessment"] = Table(
            "quality_assessment", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("shared_phones", Integer, default=0),
            Column("duplicate_owners", Integer, default=0),
            Column("deceased_pets", Integer, default=0),
            Column("orphaned_refs", Integer, default=0),
            Column("malformed", Integer, default=0),
            Column("usable_record_share", Float, default=1.0),
            Column("below_floor", Boolean, default=False),
            Column("itemized_gap", J()),
            Column("created_at", String),
        )

        self.tables["reconciliation_report"] = Table(
            "reconciliation_report", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("category_counts", J()),
            Column("ar_variance", J()),
            Column("invoice_variance", J()),
            Column("payment_variance", J()),
            Column("outstanding_gap", J()),
            Column("blocking", Boolean, default=False),
            Column("owner_acknowledged", Boolean, default=False),
            Column("audience", String, default="owner"),
            Column("created_at", String),
        )

        self.tables["identity_audit_corpus"] = Table(
            "identity_audit_corpus", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("proposals", J()),
            Column("collisions", J()),
            Column("answer_key_scored_precision", J()),
            Column("created_at", String),
        )

        self.tables["gap_notice"] = Table(
            "gap_notice", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("missing_categories", J()),
            Column("text", Text, default=""),
            Column("created_at", String),
        )

        self.tables["practice_readiness"] = Table(
            "practice_readiness", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("criteria", J()),
            Column("shadow_ready", Boolean, default=False),
            Column("invisible_adoption_asserted", Boolean, default=False),
            Column("created_at", String),
        )

        self.tables["batch_rollup"] = Table(
            "batch_rollup", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("delivery_id", String, nullable=True),
            Column("per_practice", J()),
            Column("created_at", String),
        )

        # ---- generic canonical spine (all categories) ---------------- #
        # Every normalized record (clinical/scheduling/comms/financial/…) lands
        # here with its entity_ref/source_id lineage — the store the idempotency
        # + 100%-lineage gate (T019/T038) diffs, and the hydration store for the
        # canonical clinical/scheduling categories that have no typed net-new
        # table in this build. Financial/inventory categories ALSO land in their
        # typed tables below (the reconciliation/completeness read models).
        self.tables["canonical_record"] = Table(
            "canonical_record", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("category", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False),
            Column("source_id", String, nullable=False),
            Column("payload", J()),
            Column("unmapped_fields", J()),
            Column("created_at", String),
            Index("ix_canonical_record_ref", "practice_id", "entity_ref", unique=True),
            Index("ix_canonical_record_cat", "practice_id", "category"),
        )

        # ---- net-new canonical financial / inventory ----------------- #
        self.tables["ledger_entry"] = Table(
            "ledger_entry", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False),
            Column("source_id", String, nullable=False),
            Column("account_ref", String, default=""),
            Column("amount", Float, default=0.0),
            Column("entry_type", String, default=""),
            Column("posted_at", String, nullable=True),
            Column("created_at", String),
            Index("ix_ledger_entry_src", "practice_id", "source_id"),
        )

        self.tables["invoice_record"] = Table(
            "invoice_record", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False),
            Column("source_id", String, nullable=False),
            Column("client_ref", String, default=""),
            Column("total", Float, default=0.0),
            Column("status", String, default=""),
            Column("issued_at", String, nullable=True),
            Column("created_at", String),
            Index("ix_invoice_record_src", "practice_id", "source_id"),
        )

        self.tables["payment_record"] = Table(
            "payment_record", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False),
            Column("source_id", String, nullable=False),
            Column("client_ref", String, default=""),
            Column("amount", Float, default=0.0),
            Column("method", String, default=""),
            Column("received_at", String, nullable=True),
            Column("created_at", String),
            Index("ix_payment_record_src", "practice_id", "source_id"),
        )

        self.tables["ar_balance"] = Table(
            "ar_balance", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False),
            Column("source_id", String, nullable=False),
            Column("client_ref", String, default=""),
            Column("balance", Float, default=0.0),
            Column("as_of", String, nullable=True),
            Column("created_at", String),
            Index("ix_ar_balance_src", "practice_id", "source_id"),
        )

        self.tables["inventory_item"] = Table(
            "inventory_item", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False),
            Column("source_id", String, nullable=False),
            Column("product_ref", String, default=""),
            Column("qty_on_hand", Float, default=0.0),
            Column("unit", String, default=""),
            Column("last_counted_at", String, nullable=True),
            Column("created_at", String),
            Index("ix_inventory_item_src", "practice_id", "source_id"),
        )

        self.tables["unmapped_field_sidecar"] = Table(
            "unmapped_field_sidecar", md,
            Column("id", String, primary_key=True),
            Column("clinic_id", String, nullable=False, index=True),
            Column("practice_id", String, nullable=False, index=True),
            Column("entity_ref", String, nullable=False),
            Column("source_field", String, default=""),
            Column("raw_value", Text, nullable=True),
            Column("created_at", String),
        )

    # ------------------------------------------------------------------ #
    #  init_db (idempotent-additive)
    # ------------------------------------------------------------------ #
    def init_db(self) -> None:
        """Create all tables + FORCE-RLS + append-only triggers (idempotent)."""
        self.metadata.create_all(self.engine)
        if self.engine.dialect.name == "postgresql":
            self._install_force_rls()
            self._install_append_only_triggers()

    def _install_force_rls(self) -> None:
        """Enable + FORCE row-level security on every 009-owned table (SEC-20),
        with a permissive app-scope policy standing in for the tenant policy in
        the single-clinic build. The FORCE flag is the audited posture; the real
        clinic_id-keyed policy slots in at Pilot-Activation with no schema change."""
        with self.engine.begin() as conn:
            for tbl in ONBOARDING_CONTROL_TABLES + CANONICAL_TABLES:
                conn.execute(text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;"))
                conn.execute(text(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;"))
                conn.execute(text(f"DROP POLICY IF EXISTS envelope_app_scope ON {tbl};"))
                conn.execute(text(
                    f"CREATE POLICY envelope_app_scope ON {tbl} "
                    f"USING (true) WITH CHECK (true);"
                ))

    def _install_append_only_triggers(self) -> None:
        ddl = [
            """
            CREATE OR REPLACE FUNCTION envelope_reject_mutation()
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
                f"FOR EACH ROW EXECUTE FUNCTION envelope_reject_mutation();"
            )
        with self.engine.begin() as conn:
            for stmt in ddl:
                conn.execute(text(stmt))

    def force_rls_enabled(self, table_name: str) -> bool:
        """True iff FORCE ROW LEVEL SECURITY is set on the table (verify hook)."""
        with self.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT relforcerowsecurity FROM pg_class WHERE relname = :t"
            ), {"t": table_name}).first()
        return bool(row and row[0])

    # ------------------------------------------------------------------ #
    #  Generic helpers (HouseholdRepository pattern)
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

    def _payload(self, table_name: str, row: dict) -> dict:
        tbl = self.tables[table_name]
        cols = {c.name for c in tbl.columns}
        return {k: v for k, v in row.items() if k in cols}

    def _insert(self, table_name: str, row: dict, conn: Optional[Connection] = None) -> dict:
        payload = self._payload(table_name, row)
        tbl = self.tables[table_name]
        if conn is not None:
            conn.execute(insert(tbl).values(**payload))
        else:
            with self.engine.begin() as c:
                c.execute(insert(tbl).values(**payload))
        return payload

    def _select_where(self, table_name: str, **eq) -> list[dict]:
        tbl = self.tables[table_name]
        stmt = select(tbl)
        for k, v in eq.items():
            stmt = stmt.where(tbl.c[k] == v)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    def _count(self, table_name: str, **eq) -> int:
        tbl = self.tables[table_name]
        stmt = select(text("count(*)")).select_from(tbl)
        for k, v in eq.items():
            stmt = stmt.where(tbl.c[k] == v)
        with self.engine.connect() as conn:
            return conn.execute(stmt).scalar() or 0

    # ------------------------------------------------------------------ #
    #  Orphan-receipt guard — the full-transaction wrap (FarmAgent fix)
    # ------------------------------------------------------------------ #
    @contextmanager
    def receipt_txn(self) -> Iterator["_ReceiptWriter"]:
        """A single DB transaction for the whole receipt provisioning. If the
        block raises anywhere, the transaction rolls back and **zero** delivery /
        practice_database / chain_of_custody rows persist (no orphan receipt)."""
        with self.engine.begin() as conn:
            yield _ReceiptWriter(self, conn)

    # ------------------------------------------------------------------ #
    #  Typed create / get helpers
    # ------------------------------------------------------------------ #
    def create_delivery(self, m: Any) -> dict:
        return self._insert("delivery", self._dump(m))

    def get_delivery(self, delivery_id: str) -> Optional[dict]:
        rows = self._select_where("delivery", id=delivery_id)
        return rows[0] if rows else None

    def create_practice_database(self, m: Any) -> dict:
        return self._insert("practice_database", self._dump(m))

    def get_practice_database(self, practice_database_id: str) -> Optional[dict]:
        rows = self._select_where("practice_database", id=practice_database_id)
        return rows[0] if rows else None

    def get_practice_database_by_practice(self, practice_id: str) -> Optional[dict]:
        rows = self._select_where("practice_database", practice_id=practice_id)
        return rows[0] if rows else None

    def list_practice_databases(self, clinic_id: str) -> list[dict]:
        return self._select_where("practice_database", clinic_id=clinic_id)

    def set_practice_state(self, practice_id: str, state: str,
                           receipt_state: Optional[str] = None) -> None:
        """Update the mutable practice_database.state (NOT append-only — the
        append-only spine is state_transition). The state machine (T006) is the
        only caller; it always writes a state_transition row alongside."""
        from sqlalchemy import update as _update
        tbl = self.tables["practice_database"]
        vals: dict[str, Any] = {"state": state}
        if receipt_state is not None:
            vals["receipt_state"] = receipt_state
        with self.engine.begin() as conn:
            conn.execute(_update(tbl).where(tbl.c.practice_id == practice_id).values(**vals))

    def set_practice_vault_ref(self, practice_id: str, vault_object_ref: str) -> None:
        from sqlalchemy import update as _update
        tbl = self.tables["practice_database"]
        with self.engine.begin() as conn:
            conn.execute(_update(tbl).where(tbl.c.practice_id == practice_id)
                         .values(vault_object_ref=vault_object_ref))

    def append_chain_of_custody(self, m: Any) -> dict:
        return self._insert("chain_of_custody", self._dump(m))

    def get_chain_of_custody(self, practice_id: str) -> list[dict]:
        return self._select_where("chain_of_custody", practice_id=practice_id)

    def append_counsel_signoff(self, m: Any) -> dict:
        return self._insert("counsel_signoff", self._dump(m))

    def get_counsel_signoffs(self, practice_id: str) -> list[dict]:
        return self._select_where("counsel_signoff", practice_id=practice_id)

    def has_counsel_signoff(self, practice_id: str) -> bool:
        return self._count("counsel_signoff", practice_id=practice_id) > 0

    def create_scope_check(self, m: Any) -> dict:
        return self._insert("scope_check", self._dump(m))

    def get_scope_check(self, practice_id: str) -> Optional[dict]:
        rows = self._select_where("scope_check", practice_id=practice_id)
        return rows[-1] if rows else None

    def create_format_profile(self, m: Any) -> dict:
        return self._insert("format_profile", self._dump(m))

    def get_format_profile(self, practice_id: str) -> Optional[dict]:
        rows = self._select_where("format_profile", practice_id=practice_id)
        return rows[-1] if rows else None

    def has_format_profile(self, practice_id: str) -> bool:
        return self._count("format_profile", practice_id=practice_id) > 0

    def append_state_transition(self, m: Any) -> dict:
        return self._insert("state_transition", self._dump(m))

    def get_state_transitions(self, practice_id: str) -> list[dict]:
        return self._select_where("state_transition", practice_id=practice_id)

    def create_completeness_result(self, m: Any) -> dict:
        return self._insert("completeness_result", self._dump(m))

    def get_completeness_result(self, practice_id: str) -> Optional[dict]:
        rows = self._select_where("completeness_result", practice_id=practice_id)
        return rows[-1] if rows else None

    def create_quality_assessment(self, m: Any) -> dict:
        return self._insert("quality_assessment", self._dump(m))

    def get_quality_assessment(self, practice_id: str) -> Optional[dict]:
        rows = self._select_where("quality_assessment", practice_id=practice_id)
        return rows[-1] if rows else None

    def append_reconciliation_report(self, m: Any) -> dict:
        return self._insert("reconciliation_report", self._dump(m))

    def get_reconciliation_reports(self, practice_id: str) -> list[dict]:
        return self._select_where("reconciliation_report", practice_id=practice_id)

    def append_identity_audit_corpus(self, m: Any) -> dict:
        return self._insert("identity_audit_corpus", self._dump(m))

    def get_identity_audit_corpus(self, practice_id: str) -> Optional[dict]:
        rows = self._select_where("identity_audit_corpus", practice_id=practice_id)
        return rows[-1] if rows else None

    def append_gap_notice(self, m: Any) -> dict:
        return self._insert("gap_notice", self._dump(m))

    def get_gap_notices(self, practice_id: str) -> list[dict]:
        return self._select_where("gap_notice", practice_id=practice_id)

    def create_practice_readiness(self, m: Any) -> dict:
        return self._insert("practice_readiness", self._dump(m))

    def get_practice_readiness(self, practice_id: str) -> Optional[dict]:
        rows = self._select_where("practice_readiness", practice_id=practice_id)
        return rows[-1] if rows else None

    # ---- canonical financial / inventory ----------------------------- #
    def upsert_canonical(self, table_name: str, rows: list[Any],
                         key_cols: tuple = ("practice_id", "source_id")) -> int:
        """Deterministic idempotent upsert on (practice_id, source_id): a re-run
        against the same source yields no duplicate rows and stable identifiers
        (FR-010). Returns the number of rows written or refreshed."""
        from sqlalchemy import and_, delete as _delete
        tbl = self.tables[table_name]
        written = 0
        with self.engine.begin() as conn:
            for m in rows:
                payload = self._payload(table_name, self._dump(m))
                cond = and_(*[tbl.c[k] == payload[k] for k in key_cols])
                conn.execute(_delete(tbl).where(cond))
                conn.execute(insert(tbl).values(**payload))
                written += 1
        return written

    def list_canonical(self, table_name: str, practice_id: str) -> list[dict]:
        return self._select_where(table_name, practice_id=practice_id)

    def count_canonical(self, table_name: str, practice_id: str) -> int:
        return self._count(table_name, practice_id=practice_id)

    def list_canonical_records(self, practice_id: str,
                               category: Optional[str] = None) -> list[dict]:
        """Read the generic canonical spine, optionally filtered to one category."""
        if category is None:
            return self._select_where("canonical_record", practice_id=practice_id)
        return self._select_where("canonical_record", practice_id=practice_id,
                                  category=category)


class _ReceiptWriter:
    """The bound writer yielded by ``receipt_txn`` — every write rides the same
    transaction, so a raise anywhere rolls the whole receipt back."""

    def __init__(self, repo: OnboardingRepository, conn: Connection):
        self._repo = repo
        self._conn = conn

    def insert_delivery(self, m: Any) -> dict:
        return self._repo._insert("delivery", self._repo._dump(m), self._conn)

    def insert_practice_database(self, m: Any) -> dict:
        return self._repo._insert("practice_database", self._repo._dump(m), self._conn)

    def insert_chain_of_custody(self, m: Any) -> dict:
        return self._repo._insert("chain_of_custody", self._repo._dump(m), self._conn)
