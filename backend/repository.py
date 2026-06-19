import sqlite3
import json
import os
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from .models import (
    Resource, ResourceType, TimeBlock, TimeRange, Job,
    Patient, PatientWithOwner, Owner, OwnerSummary,
    PreExamBrief, RiskScore, SoapNote, FollowUpDraft,
    Clinic, VetClinicAssignment,
    IntegrationDefinition, IntegrationStatus, MigrationRun, MigrationFlag,
    Account, ModuleLicense, AccountInvoice, AccountUser,
)
from .interfaces import BaseRepository

# Store the DB file next to this module (works locally and on Render's persistent disk)
_DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "scheduler.db"))


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                hard_skills TEXT NOT NULL,
                attributes TEXT,
                availability_windows TEXT,
                status TEXT DEFAULT 'available',
                current_timeblock_id TEXT
            );
            CREATE TABLE IF NOT EXISTS timeblocks (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                resource_ids TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                patient_id TEXT,
                intake_status TEXT DEFAULT 'not_started',
                followup_status TEXT DEFAULT 'not_started',
                risk_level TEXT,
                status TEXT DEFAULT 'scheduled'
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                breed TEXT NOT NULL,
                dob TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                flags TEXT NOT NULL DEFAULT '[]',
                flag_notes TEXT DEFAULT '',
                owner_id TEXT NOT NULL,
                visit_count INTEGER DEFAULT 0,
                last_visit_date TEXT,
                last_visit_procedure TEXT
            );
            CREATE TABLE IF NOT EXISTS owners (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                patient_ids TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS pre_exam_briefs (
                id TEXT PRIMARY KEY,
                timeblock_id TEXT NOT NULL,
                chief_complaint TEXT DEFAULT '',
                symptoms TEXT NOT NULL DEFAULT '[]',
                owner_verbatim TEXT DEFAULT '',
                suggested_focus TEXT NOT NULL DEFAULT '[]',
                status TEXT DEFAULT 'not_started',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS risk_scores (
                id TEXT PRIMARY KEY,
                timeblock_id TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                score INTEGER NOT NULL,
                factors TEXT NOT NULL DEFAULT '[]',
                calculated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS soap_notes (
                id TEXT PRIMARY KEY,
                timeblock_id TEXT NOT NULL,
                subjective TEXT DEFAULT '',
                objective TEXT NOT NULL DEFAULT '{}',
                assessment TEXT DEFAULT '',
                plan TEXT DEFAULT '',
                signed INTEGER DEFAULT 0,
                signed_at TEXT,
                signed_by TEXT
            );
            CREATE TABLE IF NOT EXISTS followup_drafts (
                id TEXT PRIMARY KEY,
                timeblock_id TEXT NOT NULL,
                subject TEXT DEFAULT '',
                body TEXT DEFAULT '',
                tone TEXT DEFAULT 'wellness',
                status TEXT DEFAULT 'draft',
                generated_at TEXT,
                approved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS clinics (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                address TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                timezone TEXT DEFAULT 'America/Los_Angeles',
                color_hex TEXT DEFAULT '#6C63FF',
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS vet_clinic_assignments (
                id TEXT PRIMARY KEY,
                vet_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                schedule_days TEXT NOT NULL DEFAULT '[]',
                is_primary INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS labs (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                timeblock_id TEXT,
                panel_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                ordered_by TEXT DEFAULT '',
                ordered_at TEXT NOT NULL,
                resulted_at TEXT,
                results TEXT DEFAULT '{}'
            );
        CREATE TABLE IF NOT EXISTS owner_images (
            id TEXT PRIMARY KEY,
            timeblock_id TEXT NOT NULL,
            patient_id TEXT,
            filename TEXT DEFAULT 'photo.jpg',
            content_type TEXT DEFAULT 'image/jpeg',
            data TEXT NOT NULL,
            caption TEXT DEFAULT '',
            submitted_at TEXT NOT NULL,
            source TEXT DEFAULT 'owner'
        );
        CREATE TABLE IF NOT EXISTS breed_protocols (
            id          TEXT PRIMARY KEY,
            breed_pattern       TEXT NOT NULL,
            flag_type           TEXT NOT NULL,
            title               TEXT NOT NULL,
            detail              TEXT NOT NULL,
            age_threshold_years REAL DEFAULT 0,
            severity            TEXT DEFAULT 'info'
        );
        CREATE TABLE IF NOT EXISTS waitlist (
            id                TEXT PRIMARY KEY,
            patient_id        TEXT NOT NULL,
            clinic_id         TEXT NOT NULL,
            procedure_type    TEXT NOT NULL,
            preferred_vet_id  TEXT,
            urgency           TEXT DEFAULT 'flexible',
            offer_status      TEXT DEFAULT 'waiting',
            join_date         TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS care_protocols (
            id              TEXT PRIMARY KEY,
            species         TEXT NOT NULL,
            protocol_name   TEXT NOT NULL,
            interval_months INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS care_events (
            id               TEXT PRIMARY KEY,
            patient_id       TEXT NOT NULL,
            protocol_id      TEXT NOT NULL,
            timeblock_id     TEXT,
            administered_date TEXT NOT NULL,
            next_due_date     TEXT NOT NULL,
            batch_number      TEXT DEFAULT '',
            administered_by   TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS prescriptions (
            id               TEXT PRIMARY KEY,
            patient_id       TEXT NOT NULL,
            timeblock_id     TEXT,
            drug_name        TEXT NOT NULL,
            dose             TEXT NOT NULL,
            frequency        TEXT NOT NULL,
            duration_days    INTEGER NOT NULL,
            refills_remaining INTEGER DEFAULT 0,
            supply_ends_at   TEXT NOT NULL,
            issued_by        TEXT NOT NULL,
            issued_date      TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS refill_requests (
            id               TEXT PRIMARY KEY,
            prescription_id  TEXT NOT NULL,
            initiated_by     TEXT NOT NULL,
            status           TEXT DEFAULT 'pending',
            requested_at     TEXT NOT NULL,
            reviewed_by      TEXT,
            reviewed_at      TEXT
        );
        CREATE TABLE IF NOT EXISTS integration_definitions (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            module        TEXT NOT NULL DEFAULT 'core',
            tier          TEXT NOT NULL DEFAULT 'standard',
            required_keys TEXT NOT NULL DEFAULT '[]',
            test_endpoint TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS integration_credentials (
            id               TEXT PRIMARY KEY,
            clinic_id        TEXT NOT NULL,
            integration_id   TEXT NOT NULL,
            key_name         TEXT NOT NULL,
            encrypted_value  TEXT NOT NULL,
            last_verified_at TEXT
        );
        CREATE TABLE IF NOT EXISTS integration_statuses (
            id               TEXT PRIMARY KEY,
            clinic_id        TEXT NOT NULL,
            integration_id   TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'unconfigured',
            latency_ms       INTEGER DEFAULT 0,
            error_message    TEXT DEFAULT '',
            last_checked_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS migration_runs (
            id                   TEXT PRIMARY KEY,
            clinic_id            TEXT NOT NULL,
            source_system        TEXT NOT NULL,
            status               TEXT NOT NULL DEFAULT 'pending',
            phase                TEXT DEFAULT '',
            imported_owners      INTEGER DEFAULT 0,
            imported_patients    INTEGER DEFAULT 0,
            imported_visits      INTEGER DEFAULT 0,
            imported_vaccines    INTEGER DEFAULT 0,
            imported_rx          INTEGER DEFAULT 0,
            flagged_count        INTEGER DEFAULT 0,
            started_at           TEXT,
            completed_at         TEXT,
            error_message        TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS migration_flags (
            id               TEXT PRIMARY KEY,
            migration_run_id TEXT NOT NULL,
            record_type      TEXT NOT NULL,
            source_row       TEXT NOT NULL DEFAULT '{}',
            reason           TEXT NOT NULL
        );
        """)
        # T003 — Extend labs table with integration fields
        for col_def in [
            "provider TEXT DEFAULT 'manual'",
            "lab_order_id TEXT",
            "clinic_id TEXT",
            "flagged_values TEXT DEFAULT '[]'",
            "is_critical INTEGER DEFAULT 0",
            "acknowledged_by TEXT",
            "acknowledged_at TEXT",
        ]:
            try:
                conn.execute(f"ALTER TABLE labs ADD COLUMN {col_def}")
            except Exception:
                pass
        # T004 — Extend owner_images table with imaging fields
        for col_def in [
            "modality TEXT",
            "report_text TEXT",
            "dicom_study_uid TEXT",
            "imaging_system TEXT",
            "study_date TEXT",
        ]:
            try:
                conn.execute(f"ALTER TABLE owner_images ADD COLUMN {col_def}")
            except Exception:
                pass
        # T055 — Extend timeblocks with lab_order_id
        try:
            conn.execute("ALTER TABLE timeblocks ADD COLUMN lab_order_id TEXT")
        except Exception:
            pass
        # Migrate existing resources table to add status columns if missing
        try:
            conn.execute("ALTER TABLE resources ADD COLUMN status TEXT DEFAULT 'available'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE resources ADD COLUMN current_timeblock_id TEXT")
        except Exception:
            pass
        # Migrate: add clinic_id to resources
        try:
            conn.execute("ALTER TABLE resources ADD COLUMN clinic_id TEXT")
        except Exception:
            pass
        # Migrate existing timeblocks to add new columns
        for col, default in [
            ("patient_id", "NULL"),
            ("intake_status", "'not_started'"),
            ("followup_status", "'not_started'"),
            ("risk_level", "NULL"),
            ("status", "'scheduled'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE timeblocks ADD COLUMN {col} TEXT DEFAULT {default}")
            except Exception:
                pass
        # Migrate: add clinic_id to timeblocks
        try:
            conn.execute("ALTER TABLE timeblocks ADD COLUMN clinic_id TEXT")
        except Exception:
            pass
        # Migrate: add home_clinic_id to patients
        try:
            conn.execute("ALTER TABLE patients ADD COLUMN home_clinic_id TEXT")
        except Exception:
            pass
        # T002 — Phase 3: confirmation columns on timeblocks
        try:
            conn.execute("ALTER TABLE timeblocks ADD COLUMN confirmation_status TEXT DEFAULT 'not_sent'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE timeblocks ADD COLUMN confirmed_at TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE timeblocks ADD COLUMN reminder_sent_at TEXT")
        except Exception:
            pass

        # spec-007 T001 — Account management tables
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id                     TEXT PRIMARY KEY,
                name                   TEXT NOT NULL,
                contact_name           TEXT NOT NULL,
                contact_email          TEXT NOT NULL,
                contact_phone          TEXT DEFAULT '',
                address                TEXT DEFAULT '',
                plan_tier              TEXT NOT NULL DEFAULT 'starter',
                status                 TEXT NOT NULL DEFAULT 'trial',
                trial_ends_at          TEXT,
                created_at             TEXT NOT NULL,
                stripe_customer_id     TEXT DEFAULT '',
                stripe_subscription_id TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS module_licenses (
                id                          TEXT PRIMARY KEY,
                account_id                  TEXT NOT NULL,
                module_id                   TEXT NOT NULL,
                status                      TEXT NOT NULL DEFAULT 'active',
                billing_interval            TEXT NOT NULL DEFAULT 'monthly',
                price_cents                 INTEGER NOT NULL DEFAULT 0,
                purchased_at                TEXT NOT NULL,
                expires_at                  TEXT,
                stripe_subscription_item_id TEXT DEFAULT '',
                UNIQUE(account_id, module_id)
            );
            CREATE TABLE IF NOT EXISTS account_invoices (
                id                TEXT PRIMARY KEY,
                account_id        TEXT NOT NULL,
                invoice_number    TEXT NOT NULL,
                period_start      TEXT NOT NULL,
                period_end        TEXT NOT NULL,
                line_items        TEXT NOT NULL DEFAULT '[]',
                subtotal_cents    INTEGER NOT NULL DEFAULT 0,
                total_cents       INTEGER NOT NULL DEFAULT 0,
                status            TEXT NOT NULL DEFAULT 'pending',
                stripe_invoice_id TEXT DEFAULT '',
                paid_at           TEXT,
                created_at        TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS account_users (
                id         TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                name       TEXT NOT NULL,
                email      TEXT NOT NULL,
                role       TEXT NOT NULL DEFAULT 'admin',
                created_at TEXT NOT NULL,
                UNIQUE(account_id, email)
            );
        """)
        # spec-007 T002 — Add account_id to clinics
        try:
            conn.execute("ALTER TABLE clinics ADD COLUMN account_id TEXT")
        except Exception:
            pass


def _resource_from_row(row) -> Resource:
    from datetime import datetime
    now = datetime.now()
    start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    end = now.replace(hour=17, minute=0, second=0, microsecond=0)
    window = TimeRange(start_time=start, end_time=end)
    try:
        rid = UUID(row["id"])
    except (ValueError, AttributeError):
        import hashlib
        rid = UUID(bytes=hashlib.md5(str(row["id"]).encode()).digest())
    return Resource(
        id=rid,
        name=row["name"],
        type=ResourceType(row["type"]),
        hard_skills=json.loads(row["hard_skills"]),
        attributes=row["attributes"],
        availability_windows=[window],
    )


def _resource_dict_from_row(row) -> dict:
    """Return resource as dict including status fields."""
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "hard_skills": json.loads(row["hard_skills"]),
        "attributes": row["attributes"],
        "status": row["status"] if row["status"] else "available",
        "current_timeblock_id": row["current_timeblock_id"],
        "clinic_id": row["clinic_id"] if row["clinic_id"] else None,
    }


def _timeblock_from_row(row) -> TimeBlock:
    return TimeBlock(
        id=UUID(row["id"]),
        job_id=UUID(row["job_id"]),
        resource_ids=[UUID(r) for r in json.loads(row["resource_ids"])],
        start_time=datetime.fromisoformat(row["start_time"]),
        end_time=datetime.fromisoformat(row["end_time"]),
        patient_id=row["patient_id"],
        intake_status=row["intake_status"] or "not_started",
        followup_status=row["followup_status"] or "not_started",
        risk_level=row["risk_level"],
        status=row["status"] or "scheduled",
        clinic_id=row["clinic_id"] if "clinic_id" in row.keys() else None,
    )


def _patient_from_row(row) -> Patient:
    row_keys = row.keys()
    return Patient(
        id=row["id"],
        name=row["name"],
        species=row["species"],
        breed=row["breed"],
        dob=row["dob"],
        weight_kg=row["weight_kg"],
        flags=json.loads(row["flags"]),
        flag_notes=row["flag_notes"] or "",
        owner_id=row["owner_id"],
        visit_count=row["visit_count"] or 0,
        last_visit_date=row["last_visit_date"],
        last_visit_procedure=row["last_visit_procedure"],
        home_clinic_id=row["home_clinic_id"] if "home_clinic_id" in row_keys else None,
    )


def _owner_from_row(row) -> Owner:
    return Owner(
        id=row["id"],
        name=row["name"],
        phone=row["phone"],
        email=row["email"],
        patient_ids=json.loads(row["patient_ids"]),
    )


def _brief_from_row(row) -> PreExamBrief:
    return PreExamBrief(
        id=row["id"],
        timeblock_id=row["timeblock_id"],
        chief_complaint=row["chief_complaint"] or "",
        symptoms=json.loads(row["symptoms"]),
        owner_verbatim=row["owner_verbatim"] or "",
        suggested_focus=json.loads(row["suggested_focus"]),
        status=row["status"] or "not_started",
        created_at=row["created_at"],
    )


def _risk_from_row(row) -> RiskScore:
    return RiskScore(
        id=row["id"],
        timeblock_id=row["timeblock_id"],
        risk_level=row["risk_level"],
        score=row["score"],
        factors=json.loads(row["factors"]),
        calculated_at=row["calculated_at"],
    )


def _soap_from_row(row) -> SoapNote:
    return SoapNote(
        id=row["id"],
        timeblock_id=row["timeblock_id"],
        subjective=row["subjective"] or "",
        objective=json.loads(row["objective"]),
        assessment=row["assessment"] or "",
        plan=row["plan"] or "",
        signed=bool(row["signed"]),
        signed_at=row["signed_at"],
        signed_by=row["signed_by"],
    )


def _followup_from_row(row) -> FollowUpDraft:
    return FollowUpDraft(
        id=row["id"],
        timeblock_id=row["timeblock_id"],
        subject=row["subject"] or "",
        body=row["body"] or "",
        tone=row["tone"] or "wellness",
        status=row["status"] or "draft",
        generated_at=row["generated_at"],
        approved_at=row["approved_at"],
    )


class InMemoryRepository(BaseRepository):
    """SQLite-backed repository (name kept for compatibility)."""

    def __init__(self):
        _init_db()
        self._seed_if_empty()

    def _get_conn(self):
        """Expose module-level _get_conn for agent raw queries."""
        return _get_conn()

    def _seed_if_empty(self):
        with _get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        if count > 0:
            return  # Already seeded

        from datetime import datetime
        now = datetime.now()
        start = now.replace(hour=8, minute=0, second=0, microsecond=0)
        end = now.replace(hour=17, minute=0, second=0, microsecond=0)
        windows_json = json.dumps([{"start_time": start.isoformat(), "end_time": end.isoformat()}])

        seed_data = [
            # Vets
            (str(uuid4()), "Dr. Smith",  "Vet",  ["Surgery", "General Practice"],          "Experienced surgeon. Great with dogs. Prefers morning slots."),
            (str(uuid4()), "Dr. Jones",  "Vet",  ["Avian", "Exotics", "General Practice"], "Specialist in birds and exotic animals. Fast and precise."),
            (str(uuid4()), "Dr. Patel",  "Vet",  ["Surgery", "Dental", "General Practice"],"Dental and soft-tissue surgery specialist. Very thorough."),
            # Rooms
            (str(uuid4()), "Operating Room A", "Room", ["Surgery"],                             "Fully equipped surgical suite with anesthesia station."),
            (str(uuid4()), "Operating Room B", "Room", ["Surgery", "Dental"],                   "Surgical suite with dental equipment and overhead lighting."),
            (str(uuid4()), "Exam Room 1",       "Room", ["General Practice", "Avian", "Exotics"],"Standard exam room. Suitable for routine checkups and exotic animals."),
            (str(uuid4()), "Exam Room 2",       "Room", ["General Practice", "Vaccination"],     "Vaccination and wellness check room."),
            (str(uuid4()), "Grooming Suite",    "Room", ["Grooming"],                            "Dedicated grooming station with bathing and drying equipment."),
            (str(uuid4()), "Imaging Room",      "Room", ["X-Ray", "Ultrasound"],                 "Digital X-ray and ultrasound equipment. Lead-lined walls."),
            (str(uuid4()), "Isolation Ward",    "Room", ["General Practice", "Surgery"],         "Negative-pressure isolation room for infectious or post-op patients."),
        ]

        with _get_conn() as conn:
            for rid, name, rtype, skills, attrs in seed_data:
                conn.execute(
                    "INSERT OR IGNORE INTO resources (id, name, type, hard_skills, attributes, availability_windows) VALUES (?,?,?,?,?,?)",
                    (rid, name, rtype, json.dumps(skills), attrs, windows_json),
                )

    # ------------------------------------------------------------------ #
    #  Resource methods
    # ------------------------------------------------------------------ #

    def get_all_resources(self) -> List[Resource]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM resources").fetchall()
        return [_resource_from_row(r) for r in rows]

    def get_resource(self, resource_id: UUID) -> Optional[Resource]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM resources WHERE id=?", (str(resource_id),)).fetchone()
        return _resource_from_row(row) if row else None

    def get_all_rooms_dict(self) -> List[dict]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM resources WHERE type='Room'").fetchall()
        return [_resource_dict_from_row(r) for r in rows]

    def update_room_status(self, room_id: str, status: str, timeblock_id: Optional[str] = None) -> Optional[dict]:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE resources SET status=?, current_timeblock_id=? WHERE id=?",
                (status, timeblock_id, room_id)
            )
            row = conn.execute("SELECT * FROM resources WHERE id=?", (room_id,)).fetchone()
        return _resource_dict_from_row(row) if row else None

    # ------------------------------------------------------------------ #
    #  Job methods
    # ------------------------------------------------------------------ #

    def save_job(self, job: Job) -> Job:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?,?)",
                (str(job.id), job.model_dump_json()),
            )
        return job

    # ------------------------------------------------------------------ #
    #  TimeBlock methods
    # ------------------------------------------------------------------ #

    def save_timeblock(self, timeblock: TimeBlock) -> TimeBlock:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO timeblocks
                   (id, job_id, resource_ids, start_time, end_time,
                    patient_id, intake_status, followup_status, risk_level, status, clinic_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(timeblock.id),
                    str(timeblock.job_id),
                    json.dumps([str(r) for r in timeblock.resource_ids]),
                    timeblock.start_time.isoformat(),
                    timeblock.end_time.isoformat(),
                    timeblock.patient_id,
                    timeblock.intake_status,
                    timeblock.followup_status,
                    timeblock.risk_level,
                    timeblock.status,
                    timeblock.clinic_id,
                ),
            )
        return timeblock

    def get_timeblock(self, timeblock_id: str) -> Optional[TimeBlock]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM timeblocks WHERE id=?", (timeblock_id,)).fetchone()
        return _timeblock_from_row(row) if row else None

    def update_timeblock_field(self, timeblock_id: str, field: str, value) -> None:
        allowed = {"patient_id", "intake_status", "followup_status", "risk_level", "status", "clinic_id"}
        if field not in allowed:
            raise ValueError(f"Unknown field: {field}")
        with _get_conn() as conn:
            conn.execute(f"UPDATE timeblocks SET {field}=? WHERE id=?", (value, timeblock_id))

    def get_timeblocks(self, resource_id: UUID) -> List[TimeBlock]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM timeblocks").fetchall()
        result = []
        for row in rows:
            ids = json.loads(row["resource_ids"])
            if str(resource_id) in ids:
                result.append(_timeblock_from_row(row))
        return result

    def get_all_timeblocks(self) -> List[TimeBlock]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM timeblocks").fetchall()
        return [_timeblock_from_row(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  Patient methods (T004)
    # ------------------------------------------------------------------ #

    def get_all_patients(self) -> List[Patient]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM patients").fetchall()
        return [_patient_from_row(r) for r in rows]

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
        return _patient_from_row(row) if row else None

    def create_patient(self, patient: Patient) -> Patient:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO patients
                   (id, name, species, breed, dob, weight_kg, flags, flag_notes,
                    owner_id, visit_count, last_visit_date, last_visit_procedure, home_clinic_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    patient.id, patient.name, patient.species, patient.breed,
                    patient.dob, patient.weight_kg, json.dumps(patient.flags),
                    patient.flag_notes, patient.owner_id, patient.visit_count,
                    patient.last_visit_date, patient.last_visit_procedure,
                    patient.home_clinic_id,
                ),
            )
        return patient

    def get_all_owners(self) -> List[Owner]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM owners").fetchall()
        return [_owner_from_row(r) for r in rows]

    def get_owner(self, owner_id: str) -> Optional[Owner]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM owners WHERE id=?", (owner_id,)).fetchone()
        return _owner_from_row(row) if row else None

    def create_owner(self, owner: Owner) -> Owner:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO owners (id, name, phone, email, patient_ids) VALUES (?,?,?,?,?)",
                (owner.id, owner.name, owner.phone, owner.email, json.dumps(owner.patient_ids)),
            )
        return owner

    def get_patient_with_owner(self, patient_id: str) -> Optional[PatientWithOwner]:
        p = self.get_patient(patient_id)
        if not p:
            return None
        o = self.get_owner(p.owner_id)
        owner_summary = OwnerSummary(id=o.id, name=o.name, phone=o.phone) if o else None
        return PatientWithOwner(**p.model_dump(), owner=owner_summary)

    # ------------------------------------------------------------------ #
    #  PreExamBrief methods (T022, T023)
    # ------------------------------------------------------------------ #

    def save_pre_exam_brief(self, brief: PreExamBrief) -> PreExamBrief:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO pre_exam_briefs
                   (id, timeblock_id, chief_complaint, symptoms, owner_verbatim,
                    suggested_focus, status, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    brief.id, brief.timeblock_id, brief.chief_complaint,
                    json.dumps(brief.symptoms), brief.owner_verbatim,
                    json.dumps(brief.suggested_focus), brief.status, brief.created_at,
                ),
            )
        return brief

    def get_pre_exam_brief(self, timeblock_id: str) -> Optional[PreExamBrief]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM pre_exam_briefs WHERE timeblock_id=?", (timeblock_id,)
            ).fetchone()
        return _brief_from_row(row) if row else None

    # ------------------------------------------------------------------ #
    #  RiskScore methods (T019)
    # ------------------------------------------------------------------ #

    def save_risk_score(self, score: RiskScore) -> RiskScore:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO risk_scores
                   (id, timeblock_id, risk_level, score, factors, calculated_at)
                   VALUES (?,?,?,?,?,?)""",
                (
                    score.id, score.timeblock_id, score.risk_level,
                    score.score, json.dumps(score.factors), score.calculated_at,
                ),
            )
        return score

    def get_risk_score(self, timeblock_id: str) -> Optional[RiskScore]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM risk_scores WHERE timeblock_id=?", (timeblock_id,)
            ).fetchone()
        return _risk_from_row(row) if row else None

    # ------------------------------------------------------------------ #
    #  SoapNote methods (T031)
    # ------------------------------------------------------------------ #

    def save_soap_note(self, note: SoapNote) -> SoapNote:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO soap_notes
                   (id, timeblock_id, subjective, objective, assessment, plan,
                    signed, signed_at, signed_by)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    note.id, note.timeblock_id, note.subjective,
                    json.dumps(note.objective), note.assessment, note.plan,
                    1 if note.signed else 0, note.signed_at, note.signed_by,
                ),
            )
        return note

    def get_soap_note(self, timeblock_id: str) -> Optional[SoapNote]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM soap_notes WHERE timeblock_id=?", (timeblock_id,)
            ).fetchone()
        return _soap_from_row(row) if row else None

    def get_soap_note_by_id(self, note_id: str) -> Optional[SoapNote]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM soap_notes WHERE id=?", (note_id,)).fetchone()
        return _soap_from_row(row) if row else None

    def update_soap_note(self, note: SoapNote) -> SoapNote:
        return self.save_soap_note(note)

    def sign_soap_note(self, note_id: str, signed_by: str) -> Optional[SoapNote]:
        from datetime import datetime
        signed_at = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            conn.execute(
                "UPDATE soap_notes SET signed=1, signed_at=?, signed_by=? WHERE id=?",
                (signed_at, signed_by, note_id)
            )
            row = conn.execute("SELECT * FROM soap_notes WHERE id=?", (note_id,)).fetchone()
        return _soap_from_row(row) if row else None

    # ------------------------------------------------------------------ #
    #  FollowUpDraft methods (T027)
    # ------------------------------------------------------------------ #

    def save_followup_draft(self, draft: FollowUpDraft) -> FollowUpDraft:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO followup_drafts
                   (id, timeblock_id, subject, body, tone, status, generated_at, approved_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    draft.id, draft.timeblock_id, draft.subject, draft.body,
                    draft.tone, draft.status, draft.generated_at, draft.approved_at,
                ),
            )
        return draft

    def get_followup_draft(self, timeblock_id: str) -> Optional[FollowUpDraft]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM followup_drafts WHERE timeblock_id=?", (timeblock_id,)
            ).fetchone()
        return _followup_from_row(row) if row else None

    def get_followup_draft_by_id(self, draft_id: str) -> Optional[FollowUpDraft]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM followup_drafts WHERE id=?", (draft_id,)).fetchone()
        return _followup_from_row(row) if row else None

    def update_followup_draft(self, draft: FollowUpDraft) -> FollowUpDraft:
        return self.save_followup_draft(draft)

    def approve_followup_draft(self, draft_id: str) -> Optional[FollowUpDraft]:
        from datetime import datetime
        approved_at = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            conn.execute(
                "UPDATE followup_drafts SET status='sent', approved_at=? WHERE id=?",
                (approved_at, draft_id)
            )
            row = conn.execute("SELECT * FROM followup_drafts WHERE id=?", (draft_id,)).fetchone()
        return _followup_from_row(row) if row else None


    # ------------------------------------------------------------------ #
    #  Clinic CRUD (T003)
    # ------------------------------------------------------------------ #

    def get_all_clinics(self) -> List[Clinic]:
        """Return all active clinics sorted by name asc."""
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM clinics WHERE is_active=1 ORDER BY name ASC"
            ).fetchall()
        return [_clinic_from_row(r) for r in rows]

    def get_clinic(self, clinic_id: str) -> Optional[Clinic]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM clinics WHERE id=?", (clinic_id,)).fetchone()
        return _clinic_from_row(row) if row else None

    def create_clinic(self, clinic: Clinic) -> Clinic:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO clinics
                   (id, name, address, phone, email, timezone, color_hex, is_active)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    clinic.id, clinic.name, clinic.address, clinic.phone,
                    clinic.email, clinic.timezone, clinic.color_hex,
                    1 if clinic.is_active else 0,
                ),
            )
        return clinic

    def get_default_clinic(self) -> Optional[Clinic]:
        """Return the first clinic alphabetically."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM clinics WHERE is_active=1 ORDER BY name ASC LIMIT 1"
            ).fetchone()
        return _clinic_from_row(row) if row else None

    # ------------------------------------------------------------------ #
    #  VetClinicAssignment CRUD (T004)
    # ------------------------------------------------------------------ #

    def get_assignments_for_clinic(self, clinic_id: str) -> List[VetClinicAssignment]:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM vet_clinic_assignments WHERE clinic_id=?", (clinic_id,)
            ).fetchall()
        return [_assignment_from_row(r) for r in rows]

    def get_assignments_for_vet(self, vet_id: str) -> List[VetClinicAssignment]:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM vet_clinic_assignments WHERE vet_id=?", (vet_id,)
            ).fetchall()
        return [_assignment_from_row(r) for r in rows]

    def save_assignment(self, assignment: VetClinicAssignment) -> VetClinicAssignment:
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO vet_clinic_assignments
                   (id, vet_id, clinic_id, schedule_days, is_primary)
                   VALUES (?,?,?,?,?)""",
                (
                    assignment.id, assignment.vet_id, assignment.clinic_id,
                    json.dumps(assignment.schedule_days),
                    1 if assignment.is_primary else 0,
                ),
            )
        return assignment

    def delete_assignment(self, assignment_id: str) -> None:
        with _get_conn() as conn:
            conn.execute("DELETE FROM vet_clinic_assignments WHERE id=?", (assignment_id,))

    def get_vets_available_at_clinic(
        self, clinic_id: str, day_name: str
    ) -> List[Resource]:
        """Return vets assigned to a clinic on a given day name (e.g. 'Monday')."""
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT r.* FROM resources r
                   JOIN vet_clinic_assignments a ON a.vet_id = r.id
                   WHERE a.clinic_id = ? AND r.type = 'Vet'
                   AND instr(a.schedule_days, ?) > 0""",
                (clinic_id, day_name),
            ).fetchall()
        return [_resource_from_row(r) for r in rows]

    def get_all_resources_for_clinic(self, clinic_id: str) -> List[dict]:
        """Return all resources (rooms + vets) for a clinic."""
        with _get_conn() as conn:
            # Rooms directly assigned to this clinic
            room_rows = conn.execute(
                "SELECT * FROM resources WHERE type='Room' AND clinic_id=?", (clinic_id,)
            ).fetchall()
            # Vets via vet_clinic_assignments
            vet_rows = conn.execute(
                """SELECT r.* FROM resources r
                   JOIN vet_clinic_assignments a ON a.vet_id = r.id
                   WHERE a.clinic_id=? AND r.type='Vet'""",
                (clinic_id,),
            ).fetchall()
        return [_resource_dict_from_row(r) for r in room_rows + vet_rows]

    # ------------------------------------------------------------------ #
    #  Labs methods
    # ------------------------------------------------------------------ #

    def get_labs_for_patient(self, patient_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM labs WHERE patient_id=? ORDER BY ordered_at DESC",
                (patient_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_labs_for_timeblock(self, timeblock_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM labs WHERE timeblock_id=? ORDER BY ordered_at DESC",
                (timeblock_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def create_lab(self, lab: dict) -> dict:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO labs (id, patient_id, timeblock_id, panel_name, status, ordered_by, ordered_at, results) VALUES (?,?,?,?,?,?,?,?)",
                (lab['id'], lab['patient_id'], lab.get('timeblock_id'), lab['panel_name'],
                 lab.get('status', 'pending'), lab.get('ordered_by', ''), lab['ordered_at'], lab.get('results', '{}'))
            )
        return lab

    def result_lab(self, lab_id: str, results: dict, resulted_at: str) -> bool:
        with _get_conn() as conn:
            import json as _json
            conn.execute(
                "UPDATE labs SET status='resulted', results=?, resulted_at=? WHERE id=?",
                (_json.dumps(results), resulted_at, lab_id)
            )
            return conn.execute("SELECT changes()").fetchone()[0] > 0

    def save_owner_image(self, img: dict) -> dict:
        import json as _json
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO owner_images (id, timeblock_id, patient_id, filename, content_type, data, caption, submitted_at, source) VALUES (?,?,?,?,?,?,?,?,?)",
                (img["id"], img["timeblock_id"], img.get("patient_id"), img.get("filename","photo.jpg"),
                 img.get("content_type","image/jpeg"), img["data"], img.get("caption",""),
                 img["submitted_at"], img.get("source","owner"))
            )
        return img

    def get_images_for_timeblock(self, timeblock_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT id, timeblock_id, patient_id, filename, content_type, data, caption, submitted_at, source FROM owner_images WHERE timeblock_id=? ORDER BY submitted_at ASC",
                (timeblock_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  T002/T009 — Confirmation status (F013 Reminders)
    # ------------------------------------------------------------------ #

    def update_confirmation_status(self, timeblock_id: str, status: str, timestamp: str = None) -> None:
        """Update confirmation_status and optionally confirmed_at or reminder_sent_at."""
        with _get_conn() as conn:
            if status == 'sent':
                conn.execute(
                    "UPDATE timeblocks SET confirmation_status=?, reminder_sent_at=? WHERE id=?",
                    (status, timestamp, timeblock_id)
                )
            elif status == 'confirmed':
                conn.execute(
                    "UPDATE timeblocks SET confirmation_status=?, confirmed_at=? WHERE id=?",
                    (status, timestamp, timeblock_id)
                )
            else:
                conn.execute(
                    "UPDATE timeblocks SET confirmation_status=? WHERE id=?",
                    (status, timeblock_id)
                )

    def get_action_queue(self, clinic_id: str = None) -> list:
        """Return timeblocks where confirmation_status is unconfirmed or reschedule_requested."""
        with _get_conn() as conn:
            if clinic_id:
                rows = conn.execute(
                    """SELECT t.*, p.name as patient_name, o.name as owner_name
                       FROM timeblocks t
                       LEFT JOIN patients p ON p.id = t.patient_id
                       LEFT JOIN owners o ON o.id = p.owner_id
                       WHERE t.confirmation_status IN ('unconfirmed','reschedule_requested')
                       AND t.clinic_id=?""",
                    (clinic_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT t.*, p.name as patient_name, o.name as owner_name
                       FROM timeblocks t
                       LEFT JOIN patients p ON p.id = t.patient_id
                       LEFT JOIN owners o ON o.id = p.owner_id
                       WHERE t.confirmation_status IN ('unconfirmed','reschedule_requested')"""
                ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  T004/T017 — Waitlist CRUD (F014)
    # ------------------------------------------------------------------ #

    def get_active_waitlist(self, clinic_id: str = None) -> list:
        with _get_conn() as conn:
            if clinic_id:
                rows = conn.execute(
                    "SELECT w.*, p.name as patient_name, o.name as owner_name FROM waitlist w "
                    "LEFT JOIN patients p ON p.id=w.patient_id "
                    "LEFT JOIN owners o ON o.id=p.owner_id "
                    "WHERE w.offer_status NOT IN ('accepted') AND w.clinic_id=? ORDER BY w.join_date ASC",
                    (clinic_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT w.*, p.name as patient_name, o.name as owner_name FROM waitlist w "
                    "LEFT JOIN patients p ON p.id=w.patient_id "
                    "LEFT JOIN owners o ON o.id=p.owner_id "
                    "WHERE w.offer_status NOT IN ('accepted') ORDER BY w.join_date ASC"
                ).fetchall()
        return [dict(r) for r in rows]

    def add_waitlist_entry(self, entry: dict) -> dict:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO waitlist (id, patient_id, clinic_id, procedure_type, preferred_vet_id, urgency, offer_status, join_date) VALUES (?,?,?,?,?,?,?,?)",
                (entry['id'], entry['patient_id'], entry['clinic_id'], entry['procedure_type'],
                 entry.get('preferred_vet_id'), entry.get('urgency','flexible'),
                 entry.get('offer_status','waiting'), entry['join_date'])
            )
        return entry

    def update_waitlist_status(self, entry_id: str, status: str) -> None:
        with _get_conn() as conn:
            conn.execute("UPDATE waitlist SET offer_status=? WHERE id=?", (status, entry_id))

    def remove_waitlist_entry(self, entry_id: str) -> None:
        with _get_conn() as conn:
            conn.execute("DELETE FROM waitlist WHERE id=?", (entry_id,))

    def get_waitlist_entry(self, entry_id: str) -> dict:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM waitlist WHERE id=?", (entry_id,)).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    #  T004/T028 — Care Protocol & Events CRUD (F015)
    # ------------------------------------------------------------------ #

    def get_all_care_protocols(self) -> list:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM care_protocols ORDER BY protocol_name ASC").fetchall()
        return [dict(r) for r in rows]

    def get_care_protocol(self, protocol_id: str) -> dict:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM care_protocols WHERE id=?", (protocol_id,)).fetchone()
        return dict(row) if row else None

    def get_care_events_for_patient(self, patient_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT ce.*, cp.protocol_name, cp.interval_months
                   FROM care_events ce
                   JOIN care_protocols cp ON cp.id = ce.protocol_id
                   WHERE ce.patient_id=? ORDER BY ce.administered_date DESC""",
                (patient_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def create_care_event(self, event: dict) -> dict:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO care_events (id, patient_id, protocol_id, timeblock_id, administered_date, next_due_date, batch_number, administered_by) VALUES (?,?,?,?,?,?,?,?)",
                (event['id'], event['patient_id'], event['protocol_id'], event.get('timeblock_id'),
                 event['administered_date'], event['next_due_date'],
                 event.get('batch_number',''), event.get('administered_by',''))
            )
        return event

    def get_overdue_care(self) -> list:
        """Return patients with any care event where next_due_date < today."""
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT ce.*, cp.protocol_name, cp.interval_months,
                          p.name as patient_name, o.name as owner_name
                   FROM care_events ce
                   JOIN care_protocols cp ON cp.id = ce.protocol_id
                   JOIN patients p ON p.id = ce.patient_id
                   LEFT JOIN owners o ON o.id = p.owner_id
                   WHERE ce.next_due_date < date('now')
                   ORDER BY ce.next_due_date ASC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def get_care_due_within_days(self, days: int = 30) -> list:
        """Return care events due within the next N days (includes overdue)."""
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT ce.*, cp.protocol_name, cp.interval_months,
                          p.name as patient_name, o.name as owner_name
                   FROM care_events ce
                   JOIN care_protocols cp ON cp.id = ce.protocol_id
                   JOIN patients p ON p.id = ce.patient_id
                   LEFT JOIN owners o ON o.id = p.owner_id
                   WHERE ce.next_due_date <= date('now', '+' || ? || ' days')
                   ORDER BY ce.next_due_date ASC""",
                (days,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  T004/T033 — Prescriptions & Refill Requests CRUD (F016)
    # ------------------------------------------------------------------ #

    def get_prescriptions_for_patient(self, patient_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM prescriptions WHERE patient_id=? ORDER BY issued_date DESC",
                (patient_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def create_prescription(self, rx: dict) -> dict:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO prescriptions (id, patient_id, timeblock_id, drug_name, dose, frequency, duration_days, refills_remaining, supply_ends_at, issued_by, issued_date) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rx['id'], rx['patient_id'], rx.get('timeblock_id'), rx['drug_name'],
                 rx['dose'], rx['frequency'], rx['duration_days'], rx.get('refills_remaining',0),
                 rx['supply_ends_at'], rx['issued_by'], rx['issued_date'])
            )
        return rx

    def get_prescription(self, prescription_id: str) -> dict:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM prescriptions WHERE id=?", (prescription_id,)).fetchone()
        return dict(row) if row else None

    def create_refill_request(self, req: dict) -> dict:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO refill_requests (id, prescription_id, initiated_by, status, requested_at, reviewed_by, reviewed_at) VALUES (?,?,?,?,?,?,?)",
                (req['id'], req['prescription_id'], req['initiated_by'], req.get('status','pending'),
                 req['requested_at'], req.get('reviewed_by'), req.get('reviewed_at'))
            )
        return req

    def get_pending_refill_requests(self) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT rr.*, pr.drug_name, pr.dose, pr.frequency, pr.refills_remaining,
                          pr.patient_id, p.name as patient_name
                   FROM refill_requests rr
                   JOIN prescriptions pr ON pr.id = rr.prescription_id
                   JOIN patients p ON p.id = pr.patient_id
                   WHERE rr.status IN ('pending','auto_approved','vet_review')
                   ORDER BY rr.requested_at DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def approve_refill(self, refill_id: str) -> dict:
        """Approve a refill request and decrement refills_remaining on the prescription."""
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM refill_requests WHERE id=?", (refill_id,)).fetchone()
            if not row:
                return None
            rr = dict(row)
            conn.execute(
                "UPDATE refill_requests SET status='approved', reviewed_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), refill_id)
            )
            conn.execute(
                "UPDATE prescriptions SET refills_remaining = MAX(0, refills_remaining - 1) WHERE id=?",
                (rr['prescription_id'],)
            )
            pr_row = conn.execute("SELECT * FROM prescriptions WHERE id=?", (rr['prescription_id'],)).fetchone()
        return dict(pr_row) if pr_row else None

    def flag_refill_for_vet(self, refill_id: str) -> None:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE refill_requests SET status='vet_review' WHERE id=?",
                (refill_id,)
            )

    # ------------------------------------------------------------------ #
    #  T004/T038 — Forecast historical data (F019)
    # ------------------------------------------------------------------ #

    def get_historical_weekly_counts(self, clinic_id: str, weeks: int = 8) -> list:
        """G04: Bucket completed timeblocks by ISO week of start_time WHERE status='complete'."""
        # Compute cutoff in Python — SQLite string concat for modifiers is unreliable
        cutoff = (datetime.utcnow() - timedelta(weeks=weeks)).isoformat()
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT strftime('%Y-%W', start_time) as week_label,
                          COUNT(*) as count
                   FROM timeblocks
                   WHERE clinic_id=? AND status='complete'
                     AND start_time >= ?
                   GROUP BY strftime('%Y-%W', start_time)
                   ORDER BY week_label ASC""",
                (clinic_id, cutoff)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  Breed Protocol CRUD (F018)
    # ------------------------------------------------------------------ #

    def get_breed_protocols(self) -> list:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM breed_protocols").fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  T006 — Integration Credentials
    # ------------------------------------------------------------------ #

    def save_integration_credential(self, clinic_id: str, integration_id: str,
                                     key_name: str, encrypted_value: str) -> None:
        cred_id = str(uuid4())
        with _get_conn() as conn:
            # Upsert by clinic_id + integration_id + key_name
            existing = conn.execute(
                "SELECT id FROM integration_credentials WHERE clinic_id=? AND integration_id=? AND key_name=?",
                (clinic_id, integration_id, key_name)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE integration_credentials SET encrypted_value=?, last_verified_at=? WHERE id=?",
                    (encrypted_value, datetime.utcnow().isoformat(), existing["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO integration_credentials (id, clinic_id, integration_id, key_name, encrypted_value, last_verified_at) VALUES (?,?,?,?,?,?)",
                    (cred_id, clinic_id, integration_id, key_name, encrypted_value, datetime.utcnow().isoformat())
                )

    def get_integration_credentials(self, clinic_id: str, integration_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT key_name, encrypted_value FROM integration_credentials WHERE clinic_id=? AND integration_id=?",
                (clinic_id, integration_id)
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_integration_credentials(self, clinic_id: str, integration_id: str) -> None:
        with _get_conn() as conn:
            conn.execute(
                "DELETE FROM integration_credentials WHERE clinic_id=? AND integration_id=?",
                (clinic_id, integration_id)
            )

    def get_credential_value(self, clinic_id: str, integration_id: str, key_name: str) -> Optional[str]:
        """Return single encrypted value for decryption."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT encrypted_value FROM integration_credentials WHERE clinic_id=? AND integration_id=? AND key_name=?",
                (clinic_id, integration_id, key_name)
            ).fetchone()
        return row["encrypted_value"] if row else None

    # T009 W-02: resolve clinic_id from a credential value
    def get_clinic_id_by_credential(self, integration_id: str, key_name: str, value: str) -> Optional[str]:
        """Find the clinic that stored `value` as the given credential key for this integration."""
        from .agents.integration_health import decrypt
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT clinic_id, encrypted_value FROM integration_credentials WHERE integration_id=? AND key_name=?",
                (integration_id, key_name)
            ).fetchall()
        for row in rows:
            try:
                if decrypt(row["encrypted_value"]) == value:
                    return row["clinic_id"]
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------ #
    #  T007 — Integration Statuses
    # ------------------------------------------------------------------ #

    def upsert_integration_status(self, status: 'IntegrationStatus') -> None:
        with _get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM integration_statuses WHERE clinic_id=? AND integration_id=?",
                (status.clinic_id, status.integration_id)
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE integration_statuses
                       SET status=?, latency_ms=?, error_message=?, last_checked_at=?
                       WHERE id=?""",
                    (status.status, status.latency_ms, status.error_message,
                     status.last_checked_at, existing["id"])
                )
            else:
                conn.execute(
                    """INSERT INTO integration_statuses
                       (id, clinic_id, integration_id, status, latency_ms, error_message, last_checked_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (str(uuid4()), status.clinic_id, status.integration_id,
                     status.status, status.latency_ms, status.error_message,
                     status.last_checked_at)
                )

    def get_integration_status(self, clinic_id: str, integration_id: str) -> Optional[dict]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM integration_statuses WHERE clinic_id=? AND integration_id=?",
                (clinic_id, integration_id)
            ).fetchone()
        return dict(row) if row else None

    def get_all_integration_statuses(self, clinic_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM integration_statuses WHERE clinic_id=?",
                (clinic_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  T008 — Integration Definitions
    # ------------------------------------------------------------------ #

    def seed_integration_definitions(self) -> None:
        """Insert all 11 integration definitions. Called on startup if table is empty."""
        with _get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM integration_definitions").fetchone()[0]
        if count > 0:
            return
        definitions = [
            ("idexx",      "IDEXX Laboratories",       "labs",      "standard", ["IDEXX_PRACTICE_ID", "IDEXX_WEBHOOK_SECRET"],    ""),
            ("antech",     "Antech Diagnostics",        "labs",      "standard", ["ANTECH_PRACTICE_ID", "ANTECH_API_KEY"],          ""),
            ("heska",      "Heska VetLab",              "labs",      "standard", ["HESKA_PRACTICE_ID", "HESKA_WEBHOOK_SECRET"],     ""),
            ("vetscan",    "Zoetis Vetscan",            "labs",      "standard", ["VETSCAN_DEVICE_ID"],                             ""),
            ("imaging",    "DICOM Imaging System",      "imaging",   "standard", ["IMAGING_WEBHOOK_SECRET"],                        ""),
            ("twilio",     "Twilio SMS",                "comms",     "standard", ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"], ""),
            ("sendgrid",   "SendGrid Email",            "comms",     "standard", ["SENDGRID_API_KEY", "SENDGRID_FROM_EMAIL"],       ""),
            ("stripe",     "Stripe Payments",           "payments",  "standard", ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],    ""),
            ("avimark",    "Avimark PMS Migration",     "migration", "standard", [],                                               ""),
            ("cornerstone","Cornerstone PMS Migration", "migration", "standard", [],                                               ""),
            ("ezyvet",     "ezyVet PMS Migration",      "migration", "standard", ["EZYVET_API_KEY", "EZYVET_PRACTICE_ID"],          ""),
        ]
        with _get_conn() as conn:
            for (did, name, module, tier, keys, endpoint) in definitions:
                conn.execute(
                    "INSERT OR IGNORE INTO integration_definitions (id, name, module, tier, required_keys, test_endpoint) VALUES (?,?,?,?,?,?)",
                    (did, name, module, tier, json.dumps(keys), endpoint)
                )

    def get_all_integration_definitions(self) -> list:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM integration_definitions ORDER BY module, name").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["required_keys"] = json.loads(d["required_keys"])
            except Exception:
                d["required_keys"] = []
            result.append(d)
        return result

    # ------------------------------------------------------------------ #
    #  T015 — Migration Run CRUD
    # ------------------------------------------------------------------ #

    def create_migration_run(self, run: dict) -> dict:
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO migration_runs
                   (id, clinic_id, source_system, status, phase,
                    imported_owners, imported_patients, imported_visits,
                    imported_vaccines, imported_rx, flagged_count,
                    started_at, completed_at, error_message)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run["id"], run["clinic_id"], run["source_system"],
                 run.get("status", "pending"), run.get("phase", ""),
                 0, 0, 0, 0, 0, 0,
                 run.get("started_at"), run.get("completed_at"),
                 run.get("error_message", ""))
            )
        return run

    def update_migration_run(self, run_id: str, updates: dict) -> None:
        allowed = {"status", "phase", "imported_owners", "imported_patients",
                   "imported_visits", "imported_vaccines", "imported_rx",
                   "flagged_count", "completed_at", "error_message"}
        cols = {k: v for k, v in updates.items() if k in allowed}
        if not cols:
            return
        set_clause = ", ".join(f"{k}=?" for k in cols)
        with _get_conn() as conn:
            conn.execute(
                f"UPDATE migration_runs SET {set_clause} WHERE id=?",
                list(cols.values()) + [run_id]
            )

    def get_migration_run(self, run_id: str) -> Optional[dict]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM migration_runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def save_migration_flag(self, flag: dict) -> None:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO migration_flags (id, migration_run_id, record_type, source_row, reason) VALUES (?,?,?,?,?)",
                (str(uuid4()), flag["migration_run_id"], flag["record_type"],
                 json.dumps(flag.get("source_row", {})), flag["reason"])
            )

    def get_migration_flags(self, run_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM migration_flags WHERE migration_run_id=? ORDER BY rowid ASC",
                (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  T022 — Labs extended CRUD (B-01 fix)
    # ------------------------------------------------------------------ #

    def save_lab(self, lab_dict: dict) -> dict:
        """Write/upsert a lab result to the existing labs table."""
        lab_id = lab_dict.get("id") or str(uuid4())
        with _get_conn() as conn:
            existing = conn.execute("SELECT id FROM labs WHERE id=?", (lab_id,)).fetchone()
            if existing:
                conn.execute(
                    """UPDATE labs SET
                       patient_id=?, timeblock_id=?, panel_name=?, status=?,
                       ordered_by=?, ordered_at=?, resulted_at=?, results=?,
                       provider=?, lab_order_id=?, clinic_id=?,
                       flagged_values=?, is_critical=?, acknowledged_by=?, acknowledged_at=?
                       WHERE id=?""",
                    (
                        lab_dict.get("patient_id"), lab_dict.get("timeblock_id"),
                        lab_dict.get("panel_name"), lab_dict.get("status", "resulted"),
                        lab_dict.get("ordered_by", ""), lab_dict.get("ordered_at"),
                        lab_dict.get("resulted_at"), lab_dict.get("results", "{}"),
                        lab_dict.get("provider", "manual"), lab_dict.get("lab_order_id"),
                        lab_dict.get("clinic_id"),
                        json.dumps(lab_dict.get("flagged_values", [])),
                        1 if lab_dict.get("is_critical") else 0,
                        lab_dict.get("acknowledged_by"), lab_dict.get("acknowledged_at"),
                        lab_id
                    )
                )
            else:
                conn.execute(
                    """INSERT INTO labs
                       (id, patient_id, timeblock_id, panel_name, status,
                        ordered_by, ordered_at, resulted_at, results,
                        provider, lab_order_id, clinic_id,
                        flagged_values, is_critical, acknowledged_by, acknowledged_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        lab_id, lab_dict.get("patient_id"), lab_dict.get("timeblock_id"),
                        lab_dict.get("panel_name"), lab_dict.get("status", "resulted"),
                        lab_dict.get("ordered_by", ""), lab_dict.get("ordered_at"),
                        lab_dict.get("resulted_at"),
                        lab_dict.get("results", "{}") if isinstance(lab_dict.get("results"), str)
                            else json.dumps(lab_dict.get("results", {})),
                        lab_dict.get("provider", "manual"), lab_dict.get("lab_order_id"),
                        lab_dict.get("clinic_id"),
                        json.dumps(lab_dict.get("flagged_values", [])),
                        1 if lab_dict.get("is_critical") else 0,
                        lab_dict.get("acknowledged_by"), lab_dict.get("acknowledged_at")
                    )
                )
        lab_dict["id"] = lab_id
        return lab_dict

    def acknowledge_lab(self, lab_id: str, vet_id: str) -> bool:
        acknowledged_at = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            conn.execute(
                "UPDATE labs SET status='acknowledged', acknowledged_by=?, acknowledged_at=? WHERE id=?",
                (vet_id, acknowledged_at, lab_id)
            )
            changed = conn.execute("SELECT changes()").fetchone()[0]
        return changed > 0

    def patch_lab(self, lab_id: str, updates: dict) -> Optional[dict]:
        allowed = {"patient_id", "timeblock_id", "status"}
        cols = {k: v for k, v in updates.items() if k in allowed}
        if not cols:
            return None
        set_clause = ", ".join(f"{k}=?" for k in cols)
        with _get_conn() as conn:
            conn.execute(
                f"UPDATE labs SET {set_clause} WHERE id=?",
                list(cols.values()) + [lab_id]
            )
            row = conn.execute("SELECT * FROM labs WHERE id=?", (lab_id,)).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    #  W-09 — Images for patient
    # ------------------------------------------------------------------ #

    def get_images_for_patient(self, patient_id: str) -> list:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM owner_images WHERE patient_id=? ORDER BY submitted_at ASC",
                (patient_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def save_clinical_image(self, img: dict) -> dict:
        """Save a clinical image (X-ray, ultrasound, etc.) to owner_images."""
        img_id = img.get("id") or str(uuid4())
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO owner_images
                   (id, timeblock_id, patient_id, filename, content_type, data,
                    caption, submitted_at, source, modality, report_text,
                    dicom_study_uid, imaging_system, study_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    img_id, img.get("timeblock_id", ""), img.get("patient_id"),
                    img.get("filename", "imaging.dcm"),
                    img.get("content_type", "application/dicom"),
                    img.get("data", ""), img.get("caption", ""),
                    img.get("submitted_at", datetime.utcnow().isoformat()),
                    img.get("source", "xray"),
                    img.get("modality"), img.get("report_text"),
                    img.get("dicom_study_uid"), img.get("imaging_system"),
                    img.get("study_date")
                )
            )
        img["id"] = img_id
        return img

    # ------------------------------------------------------------------ #
    #  spec-007 — Account repository methods (T009–T020b, T009b)
    # ------------------------------------------------------------------ #

    def get_default_account(self) -> Optional[dict]:
        """T009: Return first account row (single-tenant demo pattern)."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM accounts ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None

    def get_account(self, account_id: str) -> Optional[dict]:
        """T010"""
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        return dict(row) if row else None

    def create_account(self, account: Account) -> dict:
        """T011: INSERT OR IGNORE — idempotent."""
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO accounts
                   (id, name, contact_name, contact_email, contact_phone, address,
                    plan_tier, status, trial_ends_at, created_at,
                    stripe_customer_id, stripe_subscription_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    account.id, account.name, account.contact_name,
                    account.contact_email, account.contact_phone, account.address,
                    account.plan_tier, account.status, account.trial_ends_at,
                    account.created_at, account.stripe_customer_id,
                    account.stripe_subscription_id,
                )
            )
            row = conn.execute("SELECT * FROM accounts WHERE id=?", (account.id,)).fetchone()
        return dict(row) if row else account.model_dump()

    def update_account(self, account_id: str, updates: dict) -> Optional[dict]:
        """T012: Update allowed fields."""
        allowed = {"name", "contact_name", "contact_email", "contact_phone", "address", "plan_tier", "status"}
        cols = {k: v for k, v in updates.items() if k in allowed}
        if not cols:
            return self.get_account(account_id)
        set_clause = ", ".join(f"{k}=?" for k in cols)
        with _get_conn() as conn:
            conn.execute(
                f"UPDATE accounts SET {set_clause} WHERE id=?",
                list(cols.values()) + [account_id]
            )
            row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        return dict(row) if row else None

    def get_module_licenses(self, account_id: str) -> list:
        """T013"""
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM module_licenses WHERE account_id=?", (account_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def account_has_module(self, account_id: str, module_id: str) -> bool:
        """T014"""
        with _get_conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM module_licenses WHERE account_id=? AND module_id=? AND status='active'",
                (account_id, module_id)
            ).fetchone()[0]
        return count > 0

    def add_module_license(self, account_id: str, module_id: str, price_cents: int, interval: str) -> dict:
        """T015: INSERT OR REPLACE."""
        lic_id = str(uuid4())
        purchased_at = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO module_licenses
                   (id, account_id, module_id, status, billing_interval, price_cents, purchased_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (lic_id, account_id, module_id, "active", interval, price_cents, purchased_at)
            )
            row = conn.execute(
                "SELECT * FROM module_licenses WHERE account_id=? AND module_id=?",
                (account_id, module_id)
            ).fetchone()
        return dict(row) if row else {}

    def cancel_module_license(self, account_id: str, module_id: str) -> bool:
        """T016"""
        with _get_conn() as conn:
            conn.execute(
                "UPDATE module_licenses SET status='cancelled' WHERE account_id=? AND module_id=?",
                (account_id, module_id)
            )
            changed = conn.execute("SELECT changes()").fetchone()[0]
        return changed > 0

    def get_account_invoices(self, account_id: str) -> list:
        """T017"""
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM account_invoices WHERE account_id=? ORDER BY created_at DESC",
                (account_id,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["line_items"] = json.loads(d.get("line_items", "[]"))
            except Exception:
                d["line_items"] = []
            result.append(d)
        return result

    def get_account_invoice(self, invoice_id: str) -> Optional[dict]:
        """T018: Parse line_items JSON on read."""
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM account_invoices WHERE id=?", (invoice_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["line_items"] = json.loads(d.get("line_items", "[]"))
        except Exception:
            d["line_items"] = []
        return d

    def create_account_invoice(self, invoice: dict) -> dict:
        """T019: json.dumps line_items on write."""
        inv_id = invoice.get("id") or str(uuid4())
        line_items_json = json.dumps(invoice.get("line_items", []))
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO account_invoices
                   (id, account_id, invoice_number, period_start, period_end,
                    line_items, subtotal_cents, total_cents, status,
                    stripe_invoice_id, paid_at, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    inv_id, invoice["account_id"], invoice["invoice_number"],
                    invoice["period_start"], invoice["period_end"],
                    line_items_json,
                    invoice.get("subtotal_cents", 0), invoice.get("total_cents", 0),
                    invoice.get("status", "pending"),
                    invoice.get("stripe_invoice_id", ""),
                    invoice.get("paid_at"), invoice.get("created_at", datetime.utcnow().isoformat()),
                )
            )
        invoice["id"] = inv_id
        return invoice

    def get_account_users(self, account_id: str) -> list:
        """T020"""
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM account_users WHERE account_id=?", (account_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_clinics_for_account(self, account_id: str) -> list:
        """T020b"""
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM clinics WHERE account_id=?", (account_id,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_active"] = bool(d.get("is_active", 1))
            result.append(d)
        return result

    def set_clinic_account(self, clinic_id: str, account_id: str) -> None:
        """T009b / B-02 fix: Set account_id on an existing clinic."""
        with _get_conn() as conn:
            conn.execute(
                "UPDATE clinics SET account_id=? WHERE id=?",
                (account_id, clinic_id)
            )

    def create_account_user(self, user: dict) -> dict:
        """Helper for seeding account_users."""
        user_id = user.get("id") or str(uuid4())
        with _get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO account_users
                   (id, account_id, name, email, role, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (
                    user_id, user["account_id"], user["name"],
                    user["email"], user.get("role", "admin"),
                    user.get("created_at", datetime.utcnow().isoformat()),
                )
            )
        user["id"] = user_id
        return user


# ── Module-level helpers for Clinic + Assignment rows ──────────────────────

def _clinic_from_row(row) -> Clinic:
    return Clinic(
        id=row["id"],
        name=row["name"],
        address=row["address"] or "",
        phone=row["phone"] or "",
        email=row["email"] or "",
        timezone=row["timezone"] or "America/Los_Angeles",
        color_hex=row["color_hex"] or "#6C63FF",
        is_active=bool(row["is_active"]),
    )


def _assignment_from_row(row) -> VetClinicAssignment:
    return VetClinicAssignment(
        id=row["id"],
        vet_id=row["vet_id"],
        clinic_id=row["clinic_id"],
        schedule_days=json.loads(row["schedule_days"]),
        is_primary=bool(row["is_primary"]),
    )


# Singleton
db = InMemoryRepository()
