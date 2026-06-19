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
        """)
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
