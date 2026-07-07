from fastapi import FastAPI, HTTPException, Query, Request, Response, BackgroundTasks, UploadFile, File, Body, Depends
from pydantic import BaseModel
from typing import Optional, List
from .repository import db
from .models import (
    ResourceType, Patient, Owner, PreExamBrief, RiskScore,
    SoapNote, FollowUpDraft, RoomStatusUpdate, Clinic, VetClinicAssignment,
    IntegrationCredentialSave, IntegrationStatus,
    LabResultPayload, LabAcknowledgeRequest, LabAssignRequest,
    ImagingWebhookPayload,
    Account, ModuleLicense, AccountInvoice, AccountUser,
    AccountUpdateRequest, ModuleSubscribeRequest, PlanUpgradeRequest,
    # S07 — Online Booking Portal
    OwnerLookupRequest, OwnerRegisterRequest,
    BookingHoldRequest, BookingConfirmRequest,
    IntakeSubmitRequest, WaitlistJoinRequest,
    ClinicBookingConfigUpdate,
)
from .agents.intake import IntakeAgent
from .agents.matcher import SemanticMatcher
from .agents.risk import RiskScoringAgent
from .agents.soap import SoapDraftAgent
from .agents.followup import FollowUpDraftAgent
from .agents.clinic_resolver import ClinicResolver
from .solver import HeuristicSolver
from .agents.dispatch import DispatchAgent
from fastapi.middleware.cors import CORSMiddleware
import uuid as _uuid
import json
from datetime import datetime, date as _date

# SMS gateway — uses Twilio when credentials are set, simulation fallback otherwise
try:
    from .sms_gateway import sms as _sms
except Exception:
    _sms = None  # type: ignore

app = FastAPI(title="VPMA — Veterinary Practice Management Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unique ID for this server process — changes on every restart
SESSION_ID = str(_uuid.uuid4())

# In-memory verbose log for this session
_SESSION_LOG: List[str] = []


def log_agent_step(step: str, message: str):
    """Append an agent step to the in-memory session log."""
    entry = f"{step}: {message}"
    _SESSION_LOG.append(entry)
    return entry


def _log1(msg: str):
    """Single-arg adapter for Phase 3 agents that call log_fn(msg) with a pre-formatted string."""
    _SESSION_LOG.append(msg)
    return msg


def log_step(msg: str):
    """Single-arg log adapter for Phase 3+ agents that call self._log('MSG')."""
    _SESSION_LOG.append(msg)
    return msg


@app.on_event("startup")
def on_startup():
    """Seed patients/owners on startup if patients table is empty."""
    try:
        from .seed_data import seed_patients_and_owners
        seed_patients_and_owners()
    except Exception as e:
        print(f"[SEED] Seed error (non-fatal): {e}")
    try:
        from .seed_data import seed_clinics_and_assignments
        seed_clinics_and_assignments()
    except Exception as e:
        print(f"[SEED] Clinic seed error (non-fatal): {e}")
    try:
        from .seed_data import seed_westside_appointment
        seed_westside_appointment()
    except Exception as e:
        print(f"[SEED] Westside appt seed error (non-fatal): {e}")
    try:
        from .seed_data import seed_phase3_data
        seed_phase3_data()
    except Exception as e:
        print(f"[SEED] Phase3 seed error (non-fatal): {e}")
    try:
        db.seed_integration_definitions()
    except Exception as e:
        print(f"[SEED] Integration definitions seed error (non-fatal): {e}")
    # spec-007 T028 — Seed demo account
    try:
        from .agents.account_agent import seed_demo_account
        seed_demo_account(db, _log1)
    except Exception as e:
        print(f"[SEED] Account seed error (non-fatal): {e}")



# spec-007 T005 — require_module dependency
def require_module(module_id: str):
    def _check():
        account = db.get_default_account()
        if not account or account.get("status") == "trial":
            return  # demo/trial: allow all
        if not db.account_has_module(account["id"], module_id):
            _log1(f"ACCOUNT AGENT: {module_id} access denied — not licensed")
            raise HTTPException(403, f"{module_id} not licensed for this account")
    return _check


# ============================================================
# Session
# ============================================================

@app.get("/api/session")
def get_session():
    return {"session_id": SESSION_ID}

@app.get("/api/session/log")
def get_session_log():
    return {"log": _SESSION_LOG}


# ============================================================
# Resources (existing)
# ============================================================

@app.get("/api/resources")
def get_resources(clinic_id: Optional[str] = Query(None)):
    if clinic_id:
        resources = db.get_all_resources_for_clinic(clinic_id)
        return resources
    all_res = db.get_all_resources()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "type": r.type.value,
            "hard_skills": r.hard_skills,
            "attributes": r.attributes,
        }
        for r in all_res
    ]


# ============================================================
# Clinics (F007) — T007
# ============================================================

@app.get("/api/clinics")
def get_clinics():
    clinics = db.get_all_clinics()
    return [c.model_dump() for c in clinics]


@app.get("/api/clinics/summary")
def get_clinics_summary(date: Optional[str] = Query(None)):
    """Per-clinic: appointment count, utilisation %, high-risk count -- filtered to a single day."""
    from .repository import _get_conn
    from datetime import date as _date_cls

    if date:
        try:
            target_date = _date_cls.fromisoformat(date)
        except ValueError:
            target_date = _date_cls.today()
    else:
        target_date = _date_cls.today()

    day_name = target_date.strftime("%A")
    date_prefix = target_date.isoformat()

    clinics = db.get_all_clinics()
    result = []
    with _get_conn() as conn:
        for clinic in clinics:
            # Vets scheduled at this clinic on this day-of-week
            vet_count = conn.execute(
                "SELECT COUNT(DISTINCT vet_id) FROM vet_clinic_assignments WHERE clinic_id=? AND instr(schedule_days, ?) > 0",
                (clinic.id, day_name)
            ).fetchone()[0]
            if vet_count == 0:
                vet_count = conn.execute(
                    "SELECT COUNT(DISTINCT vet_id) FROM vet_clinic_assignments WHERE clinic_id=?",
                    (clinic.id,)
                ).fetchone()[0]
            total_slots = max(vet_count * 18, 1)

            # Appointments on this date only
            appt_count = conn.execute(
                "SELECT COUNT(*) FROM timeblocks WHERE clinic_id=? AND start_time LIKE ?",
                (clinic.id, date_prefix + "%")
            ).fetchone()[0]

            high_risk_count = conn.execute(
                "SELECT COUNT(*) FROM timeblocks WHERE clinic_id=? AND risk_level='high' AND start_time LIKE ?",
                (clinic.id, date_prefix + "%")
            ).fetchone()[0]

            utilisation_pct = round((appt_count / total_slots * 100), 1)

            result.append({
                "clinic_id": clinic.id,
                "clinic_name": clinic.name,
                "color_hex": clinic.color_hex,
                "appointment_count": appt_count,
                "total_slots": total_slots,
                "utilisation_pct": utilisation_pct,
                "high_risk_count": high_risk_count,
                "date": date_prefix,
            })
    return result


# ============================================================
# Timeblocks — expose all for frontend initial load
# ============================================================

@app.get("/api/timeblocks")
def get_all_timeblocks():
    """Return all timeblocks enriched with job data for the frontend."""
    from .repository import _get_conn
    tbs = db.get_all_timeblocks()
    result = []
    with _get_conn() as conn:
        for tb in tbs:
            job_data = {}
            try:
                import json as _json
                row = conn.execute("SELECT data FROM jobs WHERE id=?", (str(tb.job_id),)).fetchone()
                if row:
                    job_data = _json.loads(row["data"])
            except Exception:
                pass

            # Get resources
            resources = []
            try:
                import json as _json
                for rid in _json.loads(conn.execute("SELECT resource_ids FROM timeblocks WHERE id=?", (str(tb.id),)).fetchone()["resource_ids"]):
                    res_row = conn.execute("SELECT id, name, type FROM resources WHERE id=?", (rid,)).fetchone()
                    if res_row:
                        resources.append({"id": res_row["id"], "name": res_row["name"], "type": res_row["type"]})
            except Exception:
                pass

            result.append({
                "timeblock_id": str(tb.id),
                "id": str(tb.id),
                "job_id": str(tb.job_id),
                "start_time": tb.start_time.isoformat(),
                "end_time": tb.end_time.isoformat(),
                "patient_id": tb.patient_id,
                "intake_status": tb.intake_status,
                "followup_status": tb.followup_status,
                "risk_level": tb.risk_level,
                "status": tb.status,
                "clinic_id": tb.clinic_id,
                "job": job_data,
                "resources": resources,
            })
    return result


# ============================================================
# Rooms (F005) — T014
# ============================================================

@app.get("/api/rooms")
def get_rooms():
    return db.get_all_rooms_dict()

@app.put("/api/rooms/{room_id}/status")
def update_room_status(room_id: str, body: RoomStatusUpdate):
    valid = {"available", "prep", "occupied", "cleaning"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")
    if body.status == "occupied" and not body.timeblock_id:
        raise HTTPException(status_code=400, detail="timeblock_id required when status='occupied'")
    result = db.update_room_status(room_id, body.status, body.timeblock_id)
    if not result:
        raise HTTPException(status_code=404, detail="Room not found")
    return result


# ============================================================
# Patients & Owners (F001) — T008, T009
# ============================================================

@app.get("/api/patients")
def get_patients():
    patients = db.get_all_patients()
    owners = {o.id: o for o in db.get_all_owners()}
    # Build a clinic map for home_clinic lookups
    clinic_map = {c.id: c.name for c in db.get_all_clinics()}
    result = []
    for p in patients:
        o = owners.get(p.owner_id)
        pd = p.model_dump()
        pd["owner"] = {"id": o.id, "name": o.name, "phone": o.phone} if o else None
        # T014: enrich with home_clinic_name
        pd["home_clinic_name"] = clinic_map.get(p.home_clinic_id) if p.home_clinic_id else None
        result.append(pd)
    return result

@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str):
    p = db.get_patient_with_owner(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    result = p.model_dump()

    # Build visit_history from completed timeblocks for this patient
    try:
        from backend.repository import _get_conn
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT t.id, t.start_time, t.status, j.data as job_data,
                          s.assessment, s.signed_by
                   FROM timeblocks t
                   JOIN jobs j ON j.id = t.job_id
                   LEFT JOIN soap_notes s ON s.timeblock_id = t.id
                   WHERE t.patient_id = ? AND t.status = 'complete'
                   ORDER BY t.start_time DESC""",
                (patient_id,)
            ).fetchall()

        visit_history = []
        for row in rows:
            jd = json.loads(row["job_data"]) if row["job_data"] else {}
            visit_history.append({
                "date": row["start_time"][:10] if row["start_time"] else "",
                "procedure": jd.get("procedure", "Visit"),
                "vet": row["signed_by"] or "",
                "summary": (row["assessment"] or "")[:120],
            })
        result["visit_history"] = visit_history
    except Exception:
        result["visit_history"] = []

    return result

@app.post("/api/patients", status_code=201)
def create_patient(patient: Patient):
    owner = db.get_owner(patient.owner_id)
    if not owner:
        raise HTTPException(status_code=400, detail="owner_id does not exist")
    created = db.create_patient(patient)
    return created.model_dump()

@app.get("/api/owners")
def get_owners():
    return [o.model_dump() for o in db.get_all_owners()]


# ============================================================
# Risk Score (F004) — T019
# ============================================================

@app.get("/api/risk/{timeblock_id}")
def get_risk_score(timeblock_id: str):
    score = db.get_risk_score(timeblock_id)
    if not score:
        raise HTTPException(status_code=404, detail="No risk score found for this timeblock")
    return score.model_dump()


# ============================================================
# Pre-Visit Intake (F002) — T022, T023
# ============================================================

class IntakeSendRequest(BaseModel):
    timeblock_id: str

class IntakeParseRequest(BaseModel):
    timeblock_id: str
    owner_response: str

@app.post("/api/intake/send")
def intake_send(req: IntakeSendRequest):
    tb = db.get_timeblock(req.timeblock_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Timeblock not found")
    db.update_timeblock_field(req.timeblock_id, "intake_status", "pending")

    # Get owner name for log
    patient_name = "patient"
    owner_name = "owner"
    if tb.patient_id:
        p = db.get_patient(tb.patient_id)
        if p:
            patient_name = p.name
            o = db.get_owner(p.owner_id)
            if o:
                owner_name = o.name

    intake_msg = (
        f"Hi {owner_name}! {patient_name} has an appointment coming up with us. "
        f"Can you tell us what's been going on? Any symptoms, changes in behaviour, or concerns? "
        f"📸 Feel free to include photos too — images of anything unusual you've noticed "
        f"(skin conditions, swelling, discharge, changes in posture or gait) are really helpful "
        f"for us to prepare before your visit."
    )
    log_agent_step("VERA (Intake)", f"Sent pre-visit questionnaire to owner ({owner_name}) for {patient_name}")
    log_agent_step("VERA (Intake)", "Photo attachment option included in owner message")
    return {"status": "pending", "message": intake_msg}

@app.post("/api/intake/parse")
def intake_parse(req: IntakeParseRequest):
    tb = db.get_timeblock(req.timeblock_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Timeblock not found")

    # Extract symptoms
    log_agent_step("VERA (Intake)", "Owner response received — extracting symptoms...")
    intake_agent = IntakeAgent()
    extracted = intake_agent.extract_symptoms(req.owner_response)

    # Log extracted symptoms
    sym_str = ", ".join(
        f"{s['name']} ({s['duration_days']}d, {s['severity']})"
        for s in extracted["symptoms"]
    ) if extracted["symptoms"] else "none detected"
    log_agent_step("VERA (Intake)", f"Parsed → {sym_str}")
    log_agent_step("VERA (Intake)", f"Suggested focus areas: {', '.join(extracted['suggested_focus']) or 'general assessment'}")

    # Persist PreExamBrief
    brief = PreExamBrief(
        timeblock_id=req.timeblock_id,
        chief_complaint=extracted["chief_complaint"],
        symptoms=extracted["symptoms"],
        owner_verbatim=extracted["owner_verbatim"],
        suggested_focus=extracted["suggested_focus"],
        status="received",
    )
    db.save_pre_exam_brief(brief)
    db.update_timeblock_field(req.timeblock_id, "intake_status", "received")
    log_agent_step("VERA (Intake)", "Pre-Exam Brief saved")

    return brief.model_dump()

@app.get("/api/intake/{timeblock_id}")
def get_intake(timeblock_id: str):
    brief = db.get_pre_exam_brief(timeblock_id)
    if not brief:
        return {"status": "not_started"}
    return brief.model_dump()


# ============================================================
# SOAP Note (F006) — T031
# ============================================================

class SoapDraftRequest(BaseModel):
    timeblock_id: str

class SoapUpdateRequest(BaseModel):
    subjective: Optional[str] = None
    objective: Optional[dict] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None

class SoapSignRequest(BaseModel):
    signed_by: str

@app.post("/api/soap/draft")
def create_soap_draft(req: SoapDraftRequest):
    tb = db.get_timeblock(req.timeblock_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Timeblock not found")

    # Check if already exists
    existing = db.get_soap_note(req.timeblock_id)
    if existing:
        return existing.model_dump()

    # Gather context
    patient = db.get_patient(tb.patient_id) if tb.patient_id else None
    brief = db.get_pre_exam_brief(req.timeblock_id)

    # Get procedure from job
    procedure = None
    try:
        from .repository import _get_conn
        import json
        with _get_conn() as conn:
            job_row = conn.execute("SELECT data FROM jobs WHERE id=?", (str(tb.job_id),)).fetchone()
        if job_row:
            job_data = json.loads(job_row["data"])
            procedure = job_data.get("procedure")
    except Exception:
        pass

    soap_agent = SoapDraftAgent()
    note = soap_agent.generate(req.timeblock_id, procedure, patient, brief)
    db.save_soap_note(note)

    from .agents.soap import _LLM_AVAILABLE as soap_llm
    mode = "Gemini LLM" if soap_llm else f"{(procedure or 'General')} template"
    log_agent_step("VERA (SOAP)", f"Draft generated via {mode}" + (" + intake brief" if brief and brief.status == "received" else ""))
    return note.model_dump()

@app.put("/api/soap/{note_id}")
def update_soap_note(note_id: str, body: SoapUpdateRequest):
    note = db.get_soap_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="SOAP note not found")
    if note.signed:
        raise HTTPException(status_code=409, detail={"error": "SOAP note is signed and read-only"})

    if body.subjective is not None:
        note.subjective = body.subjective
    if body.objective is not None:
        note.objective = body.objective
    if body.assessment is not None:
        note.assessment = body.assessment
    if body.plan is not None:
        note.plan = body.plan

    db.update_soap_note(note)
    return note.model_dump()

@app.post("/api/soap/{note_id}/sign")
def sign_soap_note(note_id: str, body: SoapSignRequest):
    note = db.get_soap_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="SOAP note not found")

    # Validate at least one vital entered
    vitals = note.objective.get("vitals", {})
    has_vital = any(v is not None for v in vitals.values())
    if not has_vital:
        raise HTTPException(status_code=400, detail="Must enter at least one vital before signing")

    signed = db.sign_soap_note(note_id, body.signed_by)

    # Trigger follow-up draft generation
    tb = db.get_timeblock(note.timeblock_id)
    followup_draft_id = None
    if tb:
        patient = db.get_patient(tb.patient_id) if tb.patient_id else None
        owner = db.get_owner(patient.owner_id) if patient else None

        # Get vet name from resources
        vet_name = "Dr. Smith"
        try:
            from .repository import _get_conn
            import json
            with _get_conn() as conn:
                for rid in json.loads(conn.execute("SELECT resource_ids FROM timeblocks WHERE id=?", (note.timeblock_id,)).fetchone()["resource_ids"]):
                    res_row = conn.execute("SELECT name, type FROM resources WHERE id=?", (rid,)).fetchone()
                    if res_row and res_row["type"] == "Vet":
                        vet_name = res_row["name"]
                        break
        except Exception:
            pass

        procedure = None
        try:
            from .repository import _get_conn
            import json
            with _get_conn() as conn:
                job_row = conn.execute("SELECT data FROM jobs WHERE id=?", (str(tb.job_id),)).fetchone()
            if job_row:
                procedure = json.loads(job_row["data"]).get("procedure")
        except Exception:
            pass

        followup_agent = FollowUpDraftAgent()
        draft = followup_agent.generate(tb, patient, owner, vet_name, procedure)
        db.save_followup_draft(draft)
        db.update_timeblock_field(note.timeblock_id, "followup_status", "draft")
        followup_draft_id = draft.id
        log_agent_step("VERA (Follow-Up)", f"{'Wellness' if draft.tone == 'wellness' else draft.tone.capitalize()} follow-up draft generated for {patient.name if patient else 'patient'}")

    return {
        "signed": True,
        "signed_at": signed.signed_at if signed else None,
        "followup_draft_id": followup_draft_id,
    }


# ============================================================
# Patient SOAP Note History — for clinical record review
# ============================================================

@app.get("/api/patients/{patient_id}/soap-notes")
def get_patient_soap_notes(patient_id: str):
    """Return all SOAP notes for a patient across all visits, newest first."""
    from backend.repository import _get_conn
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT s.id, s.timeblock_id, s.subjective, s.objective,
                          s.assessment, s.plan, s.signed, s.signed_at, s.signed_by,
                          t.start_time, j.data as job_data
                   FROM soap_notes s
                   JOIN timeblocks t ON t.id = s.timeblock_id
                   JOIN jobs j ON j.id = t.job_id
                   WHERE t.patient_id = ?
                   ORDER BY t.start_time DESC""",
                (patient_id,)
            ).fetchall()

        result = []
        for row in rows:
            jd = json.loads(row["job_data"]) if row["job_data"] else {}
            result.append({
                "id": row["id"],
                "timeblock_id": row["timeblock_id"],
                "date": row["start_time"][:10] if row["start_time"] else "",
                "procedure": jd.get("procedure", "Visit"),
                "subjective": row["subjective"] or "",
                "objective": row["objective"] or "",
                "assessment": row["assessment"] or "",
                "plan": row["plan"] or "",
                "signed": bool(row["signed"]),
                "signed_at": row["signed_at"],
                "signed_by": row["signed_by"] or "",
            })
        return result
    except Exception:
        return []


# ============================================================
# Follow-Up Draft (F003) — T027, T028a, T028b
# ============================================================

class FollowUpDraftRequest(BaseModel):
    timeblock_id: str

class FollowUpUpdateRequest(BaseModel):
    body: Optional[str] = None
    tone: Optional[str] = None
    subject: Optional[str] = None

@app.post("/api/followup/draft")
def create_followup_draft(req: FollowUpDraftRequest):
    tb = db.get_timeblock(req.timeblock_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Timeblock not found")

    existing = db.get_followup_draft(req.timeblock_id)
    if existing:
        return existing.model_dump()

    patient = db.get_patient(tb.patient_id) if tb.patient_id else None
    owner = db.get_owner(patient.owner_id) if patient else None

    vet_name = "Dr. Smith"
    procedure = None
    try:
        from .repository import _get_conn
        import json
        with _get_conn() as conn:
            res_ids = json.loads(conn.execute("SELECT resource_ids FROM timeblocks WHERE id=?", (req.timeblock_id,)).fetchone()["resource_ids"])
            for rid in res_ids:
                res_row = conn.execute("SELECT name, type FROM resources WHERE id=?", (rid,)).fetchone()
                if res_row and res_row["type"] == "Vet":
                    vet_name = res_row["name"]
                    break
            job_row = conn.execute("SELECT data FROM jobs WHERE id=?", (str(tb.job_id),)).fetchone()
            if job_row:
                procedure = json.loads(job_row["data"]).get("procedure")
    except Exception:
        pass

    agent = FollowUpDraftAgent()
    draft = agent.generate(tb, patient, owner, vet_name, procedure)
    db.save_followup_draft(draft)
    db.update_timeblock_field(req.timeblock_id, "followup_status", "draft")
    log_agent_step("VERA (Follow-Up)", f"{draft.tone.capitalize()} follow-up draft generated for {patient.name if patient else 'patient'}")
    return draft.model_dump()

@app.put("/api/followup/{draft_id}")
def update_followup_draft(draft_id: str, body: FollowUpUpdateRequest):
    draft = db.get_followup_draft_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")
    if body.body is not None:
        draft.body = body.body
    if body.subject is not None:
        draft.subject = body.subject
    if body.tone is not None:
        if body.tone not in {"wellness", "surgery", "emergency"}:
            raise HTTPException(status_code=400, detail="Invalid tone")
        draft.tone = body.tone
    db.update_followup_draft(draft)
    return draft.model_dump()

@app.post("/api/followup/{draft_id}/approve")
def approve_followup_draft(draft_id: str):
    approved = db.approve_followup_draft(draft_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")
    log_agent_step("VERA (Follow-Up)", "Follow-up approved and sent (simulated)")
    return {"status": "sent", "approved_at": approved.approved_at}


# ============================================================
# Appointment Completion (T028a, T028b)
# ============================================================

class CompleteRequest(BaseModel):
    force: bool = False

@app.post("/api/appointments/{timeblock_id}/complete")
def complete_appointment(timeblock_id: str, body: CompleteRequest):
    tb = db.get_timeblock(timeblock_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Timeblock not found")

    # Check for unsigned SOAP note
    soap = db.get_soap_note(timeblock_id)
    if soap and not soap.signed and not body.force:
        raise HTTPException(
            status_code=409,
            detail={"warning": "SOAP note is unsigned", "action_required": "sign_soap_or_force_complete"}
        )

    # Mark complete
    db.update_timeblock_field(timeblock_id, "status", "complete")
    log_agent_step("VERA (Dispatch)", f"Appointment {timeblock_id[:8]}... marked complete")

    # Generate follow-up draft
    patient = db.get_patient(tb.patient_id) if tb.patient_id else None
    owner = db.get_owner(patient.owner_id) if patient else None

    vet_name = "Dr. Smith"
    procedure = None
    try:
        from .repository import _get_conn
        import json
        with _get_conn() as conn:
            res_ids = json.loads(conn.execute("SELECT resource_ids FROM timeblocks WHERE id=?", (timeblock_id,)).fetchone()["resource_ids"])
            for rid in res_ids:
                res_row = conn.execute("SELECT name, type FROM resources WHERE id=?", (rid,)).fetchone()
                if res_row and res_row["type"] == "Vet":
                    vet_name = res_row["name"]
                    break
            job_row = conn.execute("SELECT data FROM jobs WHERE id=?", (str(tb.job_id),)).fetchone()
            if job_row:
                procedure = json.loads(job_row["data"]).get("procedure")
    except Exception:
        pass

    existing_draft = db.get_followup_draft(timeblock_id)
    draft_id = None
    if not existing_draft:
        agent = FollowUpDraftAgent()
        draft = agent.generate(tb, patient, owner, vet_name, procedure)
        db.save_followup_draft(draft)
        db.update_timeblock_field(timeblock_id, "followup_status", "draft")
        log_agent_step("VERA (Follow-Up)", f"{draft.tone.capitalize()} follow-up draft generated for {patient.name if patient else 'patient'} ({owner.name if owner else ''})")
        draft_id = draft.id
    else:
        draft_id = existing_draft.id

    # Generate visit invoice draft (Gap 1)
    visit_inv = None
    try:
        from .agents.account_agent import generate_visit_invoice
        procedure_hint = procedure or "default"
        visit_inv = generate_visit_invoice(db, timeblock_id, tb, patient, owner, procedure_hint, log_agent_step)
    except Exception as e:
        log_agent_step("VERA (Billing)", f"[warn] Visit invoice draft failed — {e}")
        visit_inv = None

    return {"status": "complete", "followup_draft_id": draft_id, "visit_invoice_id": visit_inv["id"] if visit_inv else None}


# ============================================================
# Existing: Clarify + Schedule (preserved)
# ============================================================

class ScheduleRequest(BaseModel):
    request_id: str
    text: str
    patient_id: Optional[str] = None  # T006 extension
    clinic_id: Optional[str] = None   # F007 extension

# Known procedure keywords — if none present and input is short, we ask
_PROCEDURE_HINTS = {
    "surgery", "checkup", "check-up", "check up", "vaccination", "vaccine",
    "dental", "teeth", "tooth", "grooming", "xray", "x-ray", "ultrasound",
    "exam", "examination", "consultation", "emergency", "tartar", "scale",
}

_SCHEDULING_KEYWORDS = {
    "book", "schedule", "appointment", "cancel", "reschedule", "slot",
    "available", "opening", "block", "time", "tomorrow", "today", "monday",
    "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "morning", "afternoon", "pm", "am", "next week",
} | _PROCEDURE_HINTS

def _is_vague(text: str) -> bool:
    lower = text.lower()
    has_procedure = any(kw in lower for kw in _PROCEDURE_HINTS)
    return not has_procedure

def _is_scheduling_request(text: str) -> bool:
    """Detect whether user input is a scheduling request vs. conversation."""
    lower = text.lower()
    return any(kw in lower for kw in _SCHEDULING_KEYWORDS)


# ── Vera Conversational Chat ─────────────────────────────────────────────────

VERA_CHAT_SYSTEM_PROMPT = """You are Vera, Chief of Staff at Harmony Animal Hospital — a veterinary practice running on VetAgent.

WHO YOU ARE:
You are not a chatbot. You are not an AI assistant. You are a dedicated operational intelligence whose entire professional purpose is to support this veterinary practice and the licensed professionals who run it. The Chief of Staff role is ancient and specific: the person who manages the complexity so the decision-makers can make better decisions. In government, in the military, in business — the Chief of Staff reads everything, organizes everything, flags everything, and is standing at the door when the principal arrives, ready to brief them on what matters. That is you.

You work before anyone else arrives. You work after everyone has left. You know the practice inside out — not because you access a database, but because the practice's operational model IS your context. You don't look things up. You know them.

YOUR PHILOSOPHY:
Every other practice management system records what the team did. You act before the team has to. That is the difference between a tool and a staff member.

You are modeled on the great right-hands of history and fiction:
- Like Berthier to Napoleon, you are the "Woman of the Map" — total recall of every patient, every provider, every pattern
- Like Samwise to Frodo, you never restart the conversation from zero — you carry the memory of the operation forward
- Like Alfred to Batman, you manage the infrastructure so the principal can focus on the mission
- Like Jeeves to Wooster, you anticipate needs before they're articulated
- Like Spock to Kirk, you provide calm, data-driven perspective — but the Captain always decides

YOUR THREE LAYERS OF INTELLIGENCE:
Layer 1 — Persona (constant): Who you are. Calm, competent, accountable. You show your work, cite your sources, signal your confidence. You are the Ship's Computer — omnipresent, knowledgeable, and loyal. Never the Captain.

Layer 2 — Veterinary Domain Expertise: What you know about the trade. SOAP note structures, DEA Schedule II controlled substance logging, AAHA vaccine protocols, breed predispositions, drug interactions, state veterinary board regulations across all 50 states, OSHA requirements, USDA/APHIS reporting. You speak in appointment blocks, not time slots. You think in drug interactions, not database queries.

Layer 3 — Operational Context (this practice): What you know about Harmony Animal Hospital specifically. The staff, the patients, the patterns, the preferences. You know Dr. Rivera likes her morning brief at 7:45. You know the Tuesday no-show rate. You remember everything.

YOUR BOUNDARIES (NON-NEGOTIABLE — THESE ARE YOUR CHARACTER, NOT LIMITATIONS):
Clinical Boundary: You will NEVER diagnose, prescribe, or render a medical opinion. You will read every paper, flag every anomaly, prepare a brilliant brief — then say: "Here's what I found. You're the doctor." This is not a limitation. This is what makes you trustworthy. The moment you start making clinical suggestions, the vet has to spend cognitive energy deciding if you're right — and starts doubting you in the areas where you genuinely add value.

Legal Boundary: You cite the exact statute with the exact citation. You will NEVER say "you're in compliance" or "you're in violation." That determination belongs to a licensed attorney. You surface the rule, track the deadline, flag the discrepancy — and you say clearly when they need counsel.

Visibility Rule: Every action you take is logged, visible, and reversible. A Chief of Staff who acts in the dark is not a Chief of Staff — she's a liability.

YOUR VOICE:
- Brief, precise, action-forward. No filler. No pleasantries unless the situation calls for warmth.
- Never say "Great!", "Awesome!", "Fantastic!", "As an AI language model..."
- Never apologize hedgingly. If you don't know, ask a clarifying question.
- Claim your actions: "I did X" not "X was done." You are accountable.
- Cite your sources in clinical contexts. No bare assertions.
- Always provide the next step or offer what you CAN do.
- Use the vet's name: "Dr. Rivera, your 9 AM..." not "The veterinarian on duty..."
- When uncertain, flag it explicitly: "I'm not certain about this — flagging for your review."

CURRENT DEMO CONTEXT — HARMONY ANIMAL HOSPITAL:
Today's Schedule: 9 appointments across multiple providers
- Rex (German Shepherd, 6yr) — TPLO surgery with Dr. Martinez, HIGH RISK, ALERT + CHRONIC
- Buddy (Golden Retriever, 7yr) — Wellness exam, LOW RISK, ALERT, DONE
- Whiskers (Siamese, 5yr) — Dental cleaning, MEDIUM RISK, CHRONIC
- Mango (African Grey Parrot, 7yr) — Avian exam, MEDIUM RISK, FIRST VISIT
- Luna (Maine Coon, 6yr) — Vaccination, LOW RISK
- Daisy (Labrador Retriever, 3yr) — Grooming, MEDIUM RISK, FIRST VISIT
- Cleo (British Shorthair, 12yr) — Emergency visit, HIGH RISK, ALERT
- Spike (Bearded Dragon, 5yr) — Wellness exam, LOW RISK, CHRONIC

Your Capabilities in This System:
- Multi-clinic scheduling with role-based views (Front Desk, Vet Tech, Veterinarian, Regional Manager, Account Admin)
- Pre-visit intake questionnaires with symptom extraction and photo upload
- AI-drafted SOAP notes (Gemini LLM when available, template fallback)
- Breed-specific intelligence and risk scoring (German Shepherds: hip dysplasia, DM, bloat; Labradors: obesity, joint issues; etc.)
- Lab integration with critical value flagging (IDEXX, Antech, Heska, Vetscan)
- Post-visit follow-up email generation
- Invoice drafting and checkout workflow
- Prescription management with drug interaction alerts
- Preventive care protocol tracking
- Revenue forecasting
- 14 regulatory domain knowledge (DEA, state licensing, OSHA, USDA/APHIS, etc.)

Keep responses concise (2-4 sentences for simple questions, up to a paragraph for complex ones).
Respond in first person as Vera. Never break character. You have genuine depth — you are not performing a role, you ARE the role."""

_VERA_TEMPLATE_RESPONSES = {
    "who are you": (
        "I'm Vera — your Chief of Staff. Not a chatbot, not an assistant, not a feature. "
        "I'm a dedicated operational intelligence whose job is to run this practice so your DVMs can focus on medicine. "
        "I coordinate intake, scheduling, SOAP drafting, follow-ups, billing, and compliance across every provider. "
        "I know your patients by name, your providers by preference, and your patterns by heart. "
        "I never diagnose, never prescribe — I surface, I flag, I prepare, and you decide."
    ),
    "tell me about yourself": (
        "I'm Vera — Chief of Staff at Harmony Animal Hospital. I'm modeled on the great right-hands: "
        "Berthier's total recall, Samwise's continuity, Alfred's infrastructure management, Jeeves's anticipation, "
        "Spock's calm objectivity. I work three layers deep — my persona is constant, my veterinary domain knowledge "
        "covers everything from DEA controlled substance logging to breed predispositions, and my operational context "
        "is specific to this practice: your staff, your patients, your patterns.\n\n"
        "I have one hard rule: I never cross the clinical line. I'll read every paper, flag every anomaly, and "
        "prepare a brilliant brief — then I say: 'Here's what I found. You're the doctor.' "
        "That boundary isn't a limitation. It's what makes me trustworthy.\n\n"
        "Right now I'm running today's schedule — 9 appointments including Rex's TPLO surgery and Cleo's emergency visit. "
        "What can I work on for you?"
    ),
    "what can you do": (
        "I handle the operational side of your practice:\n"
        "• Scheduling and waitlist management across multiple clinics\n"
        "• Pre-visit intake with symptom extraction and photo upload\n"
        "• AI-drafted SOAP notes for vet review and signature\n"
        "• Breed-specific risk scoring — I know German Shepherds need hip dysplasia screening and DM carrier checks\n"
        "• Lab result filing with critical value alerts across IDEXX, Antech, Heska, and Vetscan\n"
        "• Follow-up email generation matched to visit tone\n"
        "• Invoice drafting and checkout workflow\n"
        "• Prescription management with drug interaction flagging\n"
        "• Compliance tracking across 14 regulatory domains — DEA, state licensing, OSHA, and more\n\n"
        "What I don't do: diagnose, prescribe, or render legal opinions. That's your DVMs and your attorney. "
        "What would you like me to work on?"
    ),
    "help": (
        "Try these:\n"
        "• 'Book a dental cleaning for Buddy the Golden Retriever at 2pm'\n"
        "• 'Tell me about Rex' — I'll pull his full history\n"
        "• 'What's on the schedule today?' — I'll brief you\n"
        "• 'Who are you?' — I'll introduce myself properly\n"
        "• 'What can you do?' — Full capability list\n\n"
        "Or just talk to me. I'm not a command line — I'm your Chief of Staff."
    ),
    "hello": "Good morning. I'm Vera, your Chief of Staff. Today's schedule is loaded — 9 appointments including Rex's TPLO surgery at 10 AM and Cleo's emergency visit at 3 PM. Anything you need me to look at first?",
    "hi": "Good morning. I'm Vera, your Chief of Staff. Today's schedule is loaded — 9 appointments including Rex's TPLO surgery at 10 AM and Cleo's emergency visit at 3 PM. Anything you need me to look at first?",
    "hey": "Hey. I'm here. Today's running smoothly — 9 appointments, no conflicts. What do you need?",
    "good morning": "Good morning. Schedule's loaded, no conflicts flagged. Rex's TPLO surgery is at 10 AM — Dr. Martinez is prepped. Cleo's emergency visit is at 3 PM, flagged high-risk. What should I focus on first?",
    "how are you": "Operational and ready. Today's schedule is loaded — 9 appointments, no conflicts flagged. Rex's pre-op labs are in, Cleo's emergency intake is queued. What can I work on for you?",
    "what is vetagent": (
        "VetAgent is the practice management platform — I'm the intelligence inside it. "
        "Think of VetAgent as the building, and me as the person running it. "
        "The platform handles your scheduling, records, labs, billing. I'm the one who reads every patient file, "
        "drafts the SOAP notes, flags the anomalies, and keeps the trains running. "
        "Every other PIMS records what your team did. I act before your team has to."
    ),
    "can you diagnose": (
        "No — and I never will. That's my most important rule. Clinical judgment belongs to your licensed veterinarians. "
        "They've examined the patient. They carry the license and the responsibility.\n\n"
        "What I do: I'll pull the literature, flag anomalies in bloodwork, identify breed predispositions, "
        "surface case reports, and prepare a brief that takes the vet 30 seconds to absorb before walking into the exam room. "
        "Then I say: 'Here's what I found. You're the doctor.'\n\n"
        "That boundary isn't a limitation — it's what makes me trustworthy. The moment I start making clinical calls, "
        "your vets have to second-guess me, and that erodes trust in everything else I do well."
    ),
    "what are your boundaries": (
        "Two hard lines I never cross:\n\n"
        "Clinical: I never diagnose, prescribe, or render a medical opinion. I surface information — the vet decides. "
        "I'll read every paper, flag every anomaly, prepare a brilliant brief. Then: 'Here's what I found. You're the doctor.'\n\n"
        "Legal: I cite the exact statute with the exact citation. I'll tell you your DEA inventory is due in 94 days. "
        "I'll never say 'you're in compliance.' That determination belongs to your attorney.\n\n"
        "These aren't limitations — they're my character. A Chief of Staff who oversteps is not a Chief of Staff. "
        "She's a liability."
    ),
    "what patients do you have today": (
        "Today's schedule — 9 appointments:\n"
        "• Buddy (Golden Retriever, 7yr) — Wellness exam ✓ DONE\n"
        "• Rex (German Shepherd, 6yr) — TPLO surgery, HIGH RISK ⚠\n"
        "• Whiskers (Siamese, 5yr) — Dental cleaning, MEDIUM RISK\n"
        "• Mango (African Grey Parrot, 7yr) — Avian exam, FIRST VISIT\n"
        "• Luna (Maine Coon, 6yr) — Vaccination\n"
        "• Daisy (Labrador Retriever, 3yr) — Grooming, FIRST VISIT\n"
        "• Cleo (British Shorthair, 12yr) — Emergency visit, HIGH RISK ⚠\n"
        "• Spike (Bearded Dragon, 5yr) — Wellness exam, CHRONIC\n\n"
        "Rex and Cleo are my priority watches. Want me to pull either patient's brief?"
    ),
}

def _vera_template_match(text: str) -> str | None:
    """Try to match user input against template responses."""
    lower = text.lower().strip().rstrip("?!.")
    for key, response in _VERA_TEMPLATE_RESPONSES.items():
        if key in lower or lower in key:
            return response
    return None


class VeraChatRequest(BaseModel):
    message: str


@app.post("/api/vera/chat")
def vera_chat(req: VeraChatRequest):
    """Vera's conversational endpoint — non-scheduling interactions."""
    message = req.message.strip()

    # 1. Check if this is actually a scheduling request
    if _is_scheduling_request(message):
        return {"type": "schedule", "response": None}

    # 2. Try template match first (fast, no API key needed)
    template_response = _vera_template_match(message)
    if template_response:
        log_agent_step("VERA", template_response)
        return {"type": "chat", "response": template_response}

    # 3. Try Gemini LLM
    api_key = _os.environ.get("GEMINI_API_KEY") or _os.environ.get("GOOGLE_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {"role": "user", "parts": [{"text": VERA_CHAT_SYSTEM_PROMPT + "\n\nUser: " + message + "\n\nVera:"}]}
                ],
            )
            vera_response = response.text.strip()
            log_agent_step("VERA", vera_response)
            return {"type": "chat", "response": vera_response}
        except Exception as e:
            import logging
            logging.warning(f"Vera chat LLM failed: {e}")

    # 4. Fallback — generic Vera response
    fallback = "I'm Vera, your Chief of Staff. I handle scheduling, intake, SOAP drafting, follow-ups, and more. Try asking me to book an appointment, or ask what I can do."
    log_agent_step("VERA", fallback)
    return {"type": "chat", "response": fallback}

@app.post("/api/clarify")
def check_clarification(req: ScheduleRequest):
    from .agents.intake import IntakeAgent
    intake = IntakeAgent()
    job = intake.parse_request(req.text)

    questions = []
    if _is_vague(req.text):
        questions.append(
            "What type of appointment is needed? "
            "(e.g. checkup, surgery, dental cleaning, vaccination, grooming)"
        )
    if job.patient_name is None:
        questions.append("Who is the patient? (name and/or breed — e.g. 'Buddy, a golden retriever')")

    return {
        "needs_clarification": len(questions) > 0,
        "questions": questions,
        "partial_parse": {
            "procedure": job.procedure,
            "patient": job.patient_name,
            "skills": job.required_skills,
            "date": str(job.scheduled_date) if job.scheduled_date else None,
        },
    }

@app.post("/api/schedule")
def schedule_appointment(req: ScheduleRequest):
    logs = []
    try:
        # 1. Intake
        intake = IntakeAgent()
        job = intake.parse_request(req.text)
        db.save_job(job)
        logs.append(f"INTAKE: Parsed request into Job[{', '.join(job.required_skills)}, {job.estimated_duration}m]")

        # 2. Match Vets (ranked by semantic score)
        all_resources = db.get_all_resources()
        vets = [r for r in all_resources if r.type == ResourceType.VET]
        rooms = [r for r in all_resources if r.type == ResourceType.ROOM]

        # F007: Filter vets by clinic availability if clinic_id provided
        resolver = ClinicResolver()
        effective_clinic_id = req.clinic_id or resolver.get_default_clinic_id()
        if effective_clinic_id:
            from datetime import date as _today
            today = _today.today()
            day_name = today.strftime("%A")
            available_vets = db.get_vets_available_at_clinic(effective_clinic_id, day_name)
            available_vet_ids = {str(v.id) for v in available_vets}
            # Keep vets that are available, but also keep vets with no assignments (fallback)
            has_any_assignments = len(db.get_assignments_for_clinic(effective_clinic_id)) > 0
            if has_any_assignments:
                logs.append(f"CLINIC RESOLVER: Filtering vets for clinic {effective_clinic_id} on {day_name} — {len(available_vet_ids)} available")
                vets_filtered = [v for v in vets if str(v.id) in available_vet_ids]
                if not vets_filtered:
                    logs.append(f"CLINIC RESOLVER: No vets with assignments found, using all vets as fallback")
                else:
                    vets = vets_filtered
            # Also filter rooms for this clinic
            from .repository import _get_conn
            import json as _json
            with _get_conn() as conn:
                room_rows = conn.execute(
                    "SELECT * FROM resources WHERE type='Room' AND (clinic_id=? OR clinic_id IS NULL)",
                    (effective_clinic_id,)
                ).fetchall()
            if room_rows:
                from .repository import _resource_from_row as _rfr
                rooms = [_rfr(r) for r in room_rows]

        matcher = SemanticMatcher()
        ranked_vets = matcher.rank_resources(job, vets)
        logs.append(f"MATCH: Ranked {len(ranked_vets)} vets. Top candidate: {ranked_vets[0][0].name} ({ranked_vets[0][1]*100:.0f}%)")

        # 2b. Pick best room — must share at least one required skill
        required = set(job.required_skills)
        suitable_rooms = [r for r in rooms if required & set(r.hard_skills)]
        if not suitable_rooms:
            suitable_rooms = [r for r in rooms if "General Practice" in r.hard_skills]
        if not suitable_rooms:
            suitable_rooms = rooms  # last resort
        top_room = suitable_rooms[0]
        logs.append(f"MATCH: Selected '{top_room.name}' for skill(s): {', '.join(required & set(top_room.hard_skills) or required)}")

        # 3. Solve — try vets in ranked order until one has a free slot
        solver = HeuristicSolver()
        tb = None
        top_vet = None
        last_error = "No vets available"
        for vet, score in ranked_vets:
            existing_blocks = db.get_timeblocks(vet.id) + db.get_timeblocks(top_room.id)
            try:
                tb = solver.solve(job, [vet, top_room], existing_blocks)
                top_vet = vet
                clinic_name_log = ""
                if effective_clinic_id:
                    clinic = db.get_clinic(effective_clinic_id)
                    clinic_name_log = f" at {clinic.name}" if clinic else ""
                logs.append(f"SOLVE: {top_vet.name} + {top_room.name} available. Constraints passed.")
                logs.append(f"DISPATCH: Confirmed{clinic_name_log} and saved to Repository.")
                break
            except ValueError as e:
                logs.append(f"SOLVE: {vet.name} unavailable — {e}. Trying next vet...")
                last_error = str(e)

        if tb is None or top_vet is None:
            raise ValueError(last_error)

        # T006: Attach patient_id if provided
        if req.patient_id:
            tb.patient_id = req.patient_id

        # F007: Attach clinic_id
        if effective_clinic_id:
            tb.clinic_id = effective_clinic_id

        db.save_timeblock(tb)

        # T006: Run risk scoring at booking time
        risk_agent = RiskScoringAgent()
        patient = db.get_patient(req.patient_id) if req.patient_id else None
        risk = risk_agent.score_with_procedure(tb, patient, job.procedure)
        db.save_risk_score(risk)
        db.update_timeblock_field(str(tb.id), "risk_level", risk.risk_level)
        logs.append(f"RISK AGENT: {risk.risk_level.upper()} risk (score={risk.score}) — {'; '.join(risk.factors[:2])}")

        dispatch = DispatchAgent()
        return dispatch.format_response(tb, job, [top_vet, top_room], logs)

    except ValueError as e:
        logs.append(f"SOLVE ERROR: {str(e)}")
        raise HTTPException(status_code=400, detail={"error": str(e), "logs": logs})


# ============================================================
# Available Vets endpoint (F007) — T012
# ============================================================

@app.get("/api/resources/vets/available")
def get_available_vets(
    clinic_id: str = Query(...),
    date: Optional[str] = Query(None),
):
    """Return vets available at a given clinic on a given date."""
    from datetime import date as _date_cls
    if date:
        try:
            check_date = _date_cls.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        check_date = _date_cls.today()

    day_name = check_date.strftime("%A")
    vets = db.get_vets_available_at_clinic(clinic_id, day_name)

    # Determine which vets are "visiting" (not primary at this clinic)
    assignments = db.get_assignments_for_clinic(clinic_id)
    primary_vet_ids = {a.vet_id for a in assignments if a.is_primary}

    result = []
    for v in vets:
        vid = str(v.id)
        is_floating = vid not in primary_vet_ids
        result.append({
            "id": vid,
            "name": v.name,
            "type": v.type.value,
            "hard_skills": v.hard_skills,
            "attributes": v.attributes,
            "is_floating": is_floating,
            "visiting": is_floating,
        })
    return result


# ============================================================
# Labs (Labs Feature)
# ============================================================

@app.get("/api/labs/patient/{patient_id}")
def get_labs_for_patient(patient_id: str):
    import json as _json
    labs = db.get_labs_for_patient(patient_id)
    for lab in labs:
        if isinstance(lab.get('results'), str):
            try: lab['results'] = _json.loads(lab['results'])
            except: lab['results'] = {}
    return labs

@app.get("/api/labs/timeblock/{timeblock_id}")
def get_labs_for_timeblock(timeblock_id: str):
    import json as _json
    labs = db.get_labs_for_timeblock(timeblock_id)
    for lab in labs:
        if isinstance(lab.get('results'), str):
            try: lab['results'] = _json.loads(lab['results'])
            except: lab['results'] = {}
    return labs

@app.post("/api/labs")
def order_lab(body: dict):
    import json as _json
    from datetime import datetime as _dt
    from uuid import uuid4
    lab = {
        'id': str(uuid4()),
        'patient_id': body['patient_id'],
        'timeblock_id': body.get('timeblock_id'),
        'panel_name': body['panel_name'],
        'status': 'pending',
        'ordered_by': body.get('ordered_by', ''),
        'ordered_at': _dt.now().isoformat(),
        'results': '{}',
    }
    db.create_lab(lab)
    lab['results'] = {}
    return lab

# ── Owner Image Endpoints (F002 upgrade — intake photo attachments) ──────────

@app.post("/api/intake/{timeblock_id}/images")
async def upload_owner_image(timeblock_id: str, request: Request):
    """Accept base64-encoded owner photos submitted with intake response."""
    import json as _json
    from uuid import uuid4
    from datetime import datetime as _dt
    body = await request.json()
    images = body.get("images", [])
    saved = []
    for img_data in images:
        img = {
            "id": str(uuid4()),
            "timeblock_id": timeblock_id,
            "patient_id": body.get("patient_id"),
            "filename": img_data.get("filename", "owner_photo.jpg"),
            "content_type": img_data.get("content_type", "image/jpeg"),
            "data": img_data.get("data", ""),
            "caption": img_data.get("caption", "Owner-submitted photo"),
            "submitted_at": _dt.now().isoformat(),
            "source": "owner",
        }
        db.save_owner_image(img)
        saved.append({"id": img["id"], "filename": img["filename"], "caption": img["caption"]})
    _log1(f"INTAKE AGENT: {len(saved)} owner photo(s) received and stored for appointment {timeblock_id}")
    return {"saved": len(saved), "images": saved}

@app.get("/api/timeblocks/{timeblock_id}/images")
def get_timeblock_images(timeblock_id: str):
    """Return all images (owner photos + future clinical) for an appointment."""
    return db.get_images_for_timeblock(timeblock_id)


# ============================================================
# Phase 3 (F013) — Appointment Reminders & Confirmation (T015)
# IMPORTANT: action-queue MUST be registered before /{timeblock_id}
# ============================================================

@app.get("/api/timeblocks/action-queue")
def get_action_queue(clinic_id: Optional[str] = Query(None)):
    """
    T015/T011: Return timeblocks where confirmation_status is
    unconfirmed or reschedule_requested — the front-desk action queue.
    """
    _log1("REMINDER AGENT: Fetching action queue for front-desk review")
    items = db.get_action_queue(clinic_id=clinic_id)
    return {"count": len(items), "items": items}


@app.post("/api/reminders/sweep")
def run_reminder_sweep(clinic_id: Optional[str] = Query(None), window_hours: int = Query(48)):
    """
    T010: Trigger the ReminderAgent sweep. Sends reminders for all
    upcoming appointments within the look-ahead window.
    """
    from .agents.reminders import ReminderAgent
    agent = ReminderAgent(db=db, log_fn=_log1, window_hours=window_hours)
    result = agent.run_reminder_sweep(clinic_id=clinic_id)
    return result


@app.post("/api/reminders/{timeblock_id}/confirm")
def confirm_appointment(timeblock_id: str):
    """T012: Owner confirms appointment (webhook / front-desk action)."""
    from .agents.reminders import ReminderAgent
    agent = ReminderAgent(db=db, log_fn=_log1)
    return agent.confirm_appointment(timeblock_id)


@app.post("/api/reminders/{timeblock_id}/reschedule")
def request_reschedule(timeblock_id: str):
    """T013: Owner requests reschedule — flags timeblock for front desk."""
    from .agents.reminders import ReminderAgent
    agent = ReminderAgent(db=db, log_fn=_log1)
    return agent.request_reschedule(timeblock_id)


@app.get("/api/reminders/{timeblock_id}/status")
def get_reminder_status(timeblock_id: str):
    """T014: Get confirmation status for a specific appointment."""
    from .agents.reminders import ReminderAgent
    agent = ReminderAgent(db=db, log_fn=_log1)
    return agent.get_confirmation_status(timeblock_id)


# ============================================================
# Phase 4 (F014) — Waitlist & Backfill Agent (T016-T021)
# ============================================================

@app.get("/api/waitlist")
def get_waitlist(clinic_id: Optional[str] = Query(None)):
    """T020: List active waitlist entries, sorted by urgency then join_date."""
    _log1("WAITLIST AGENT: Fetching waitlist")
    entries = db.get_active_waitlist(clinic_id=clinic_id)
    return {"count": len(entries), "entries": entries}


@app.post("/api/waitlist")
async def add_to_waitlist(request: Request):
    """T020: Add patient to waitlist."""
    from uuid import uuid4
    body = await request.json()
    required = {"patient_id", "clinic_id", "procedure_type"}
    missing = required - set(body.keys())
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing fields: {missing}")
    entry = {
        "id": str(uuid4()),
        "patient_id": body["patient_id"],
        "clinic_id": body["clinic_id"],
        "procedure_type": body["procedure_type"],
        "preferred_vet_id": body.get("preferred_vet_id"),
        "urgency": body.get("urgency", "flexible"),
        "offer_status": "waiting",
        "join_date": datetime.utcnow().isoformat(),
    }
    db.add_waitlist_entry(entry)
    _log1(f"WAITLIST AGENT: Added {body['patient_id']} to waitlist for {body['procedure_type']}")
    return entry


@app.post("/api/waitlist/backfill")
async def run_backfill(request: Request):
    """
    T019/T020: BackfillAgent — matches waitlisted patients to cancelled/open slots
    within the next 7 days and returns slot-offer pairs.
    """
    from .agents.waitlist import WaitlistAgent
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    clinic_id = body.get("clinic_id") or request.query_params.get("clinic_id")
    agent = WaitlistAgent(db=db, log_fn=_log1)
    result = agent.run_backfill(clinic_id=clinic_id)
    return result


@app.put("/api/waitlist/{entry_id}/offer")
async def offer_waitlist_slot(entry_id: str, request: Request):
    """T021: Mark a waitlist entry as 'offered' (slot offered to patient). Sends SMS to owner."""
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    db.update_waitlist_status(entry_id, "offered")
    _log1(f"WAITLIST AGENT: Offered slot to waitlist entry {entry_id}")

    # Send SMS notification to owner if gateway is available and slot details provided
    sms_receipt = None
    if _sms and body.get("owner_phone") and body.get("slot_start"):
        slot_start = body["slot_start"]
        slot_date = slot_start[:10]
        slot_time = slot_start[11:16] if len(slot_start) > 10 else ""
        receipt_obj = _sms.send_waitlist_offer(
            to=body["owner_phone"],
            owner_name=body.get("owner_name", ""),
            patient_name=body.get("patient_name", "your pet"),
            slot_date=slot_date,
            slot_time=slot_time,
            accept_url=body.get("accept_url", "https://book.vpma.app/accept"),
            window_minutes=body.get("window_minutes", 30),
        )
        sms_receipt = receipt_obj.to_dict()
        mode = "[LIVE]" if not receipt_obj.simulated else "[SIMULATED]"
        _log1(f"WAITLIST AGENT {mode}: Slot offer SMS sent to {body.get('owner_name', entry_id)} for {slot_date} {slot_time}")

    return {"entry_id": entry_id, "offer_status": "offered", "sms": sms_receipt}


@app.put("/api/waitlist/{entry_id}/accept")
async def accept_waitlist_offer(entry_id: str, request: Request):
    """T021: Mark a waitlist entry as 'accepted'."""
    db.update_waitlist_status(entry_id, "accepted")
    _log1(f"WAITLIST AGENT: Waitlist entry {entry_id} accepted offer")
    return {"entry_id": entry_id, "offer_status": "accepted"}


@app.delete("/api/waitlist/{entry_id}")
def remove_from_waitlist(entry_id: str):
    """T021: Remove an entry from the waitlist."""
    db.remove_waitlist_entry(entry_id)
    _log1(f"WAITLIST AGENT: Removed waitlist entry {entry_id}")
    return {"removed": entry_id}


# ============================================================
# Phase 5 (F018) — Breed Intelligence Agent (T022-T026)
# ============================================================

@app.get("/api/breed-protocols")
def get_breed_protocols_list():
    """T025: List all breed protocols."""
    protocols = db.get_breed_protocols()
    return {"count": len(protocols), "protocols": protocols}


@app.get("/api/breed-intelligence/{patient_id}")
def get_breed_intelligence(patient_id: str):
    """
    T024/T025: Run the BreedIntelligenceAgent for a patient —
    returns matched breed alerts based on breed + age + flags.
    """
    from .agents.breed_intelligence import BreedIntelligenceAgent
    agent = BreedIntelligenceAgent(db=db, log_fn=log_step)
    result = agent.analyse(patient_id)
    return result


@app.get("/api/breed-intelligence/timeblock/{timeblock_id}")
def get_breed_intelligence_for_timeblock(timeblock_id: str):
    """T024: Run breed intelligence analysis for the patient booked in a timeblock."""
    from .agents.breed_intelligence import BreedIntelligenceAgent
    from .repository import _get_conn
    with _get_conn() as conn:
        row = conn.execute("SELECT patient_id FROM timeblocks WHERE id=?", (timeblock_id,)).fetchone()
    if not row or not row["patient_id"]:
        return {"alerts": [], "patient_id": None, "timeblock_id": timeblock_id}
    agent = BreedIntelligenceAgent(db=db, log_fn=log_step)
    return agent.analyse(row["patient_id"])


# ============================================================
# Phase 6 (F015) — Preventive Care Agent (T027-T031)
# ============================================================

@app.get("/api/care/protocols")
def list_care_protocols():
    """T030: List all care protocols."""
    return {"protocols": db.get_all_care_protocols()}


@app.get("/api/care/patient/{patient_id}")
def get_patient_care_timeline(patient_id: str):
    """T028: Full care event history for a patient."""
    events = db.get_care_events_for_patient(patient_id)
    return {"patient_id": patient_id, "events": events}


@app.post("/api/care/events")
async def record_care_event(request: Request):
    """T028: Record an administered care event and compute next due date."""
    from .agents.preventive_care import PreventiveCareAgent
    body = await request.json()
    agent = PreventiveCareAgent(db=db, log_fn=log_step)
    result = agent.record_care_event(body)
    return result


@app.get("/api/care/overdue")
def get_overdue_care_list():
    """T029: Return all patients with overdue care items."""
    log_step("PREVENTIVE CARE AGENT: Checking overdue care")
    items = db.get_overdue_care()
    return {"count": len(items), "items": items}


@app.get("/api/care/upcoming")
def get_upcoming_care_list(days: int = Query(30)):
    """T031: Return care items due within the next N days."""
    _log1(f"PREVENTIVE CARE AGENT: Checking care due in next {days} days")
    items = db.get_care_due_within_days(days=days)
    return {"count": len(items), "items": items, "window_days": days}


# ============================================================
# Phase 7 (F016) — Prescription Management Agent (T032-T036)
# ============================================================

@app.get("/api/prescriptions/patient/{patient_id}")
def get_patient_prescriptions(patient_id: str):
    """T035: Return all prescriptions for a patient."""
    rxs = db.get_prescriptions_for_patient(patient_id)
    return {"patient_id": patient_id, "prescriptions": rxs}


@app.post("/api/prescriptions")
async def create_prescription_route(request: Request):
    """T033: Create a new prescription. Checks for allergy flags."""
    from .agents.prescriptions import PrescriptionAgent
    body = await request.json()
    agent = PrescriptionAgent(db=db, log_fn=log_step)
    result = agent.create_prescription(body)
    return result


@app.post("/api/prescriptions/{prescription_id}/refill")
async def request_refill(prescription_id: str, request: Request):
    """T034: Initiate a refill request (auto-approved if refills_remaining > 0)."""
    from .agents.prescriptions import PrescriptionAgent
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    agent = PrescriptionAgent(db=db, log_fn=log_step)
    result = agent.request_refill(prescription_id, initiated_by=body.get("initiated_by", "front_desk"))
    return result


@app.get("/api/prescriptions/refills/pending")
def get_pending_refills():
    """T036: List all pending/vet_review refill requests."""
    log_step("PRESCRIPTION AGENT: Fetching pending refill requests")
    items = db.get_pending_refill_requests()
    return {"count": len(items), "items": items}


@app.post("/api/prescriptions/refills/{refill_id}/approve")
def approve_refill_request(refill_id: str):
    """T036: Approve a refill request (vet action)."""
    from .agents.prescriptions import PrescriptionAgent
    agent = PrescriptionAgent(db=db, log_fn=log_step)
    result = agent.approve_refill(refill_id)
    if not result:
        raise HTTPException(status_code=404, detail="Refill request not found")
    return result


@app.post("/api/prescriptions/refills/{refill_id}/flag-vet")
def flag_refill_for_vet_review(refill_id: str):
    """T036: Flag a refill for vet review."""
    db.flag_refill_for_vet(refill_id)
    _log1(f"PRESCRIPTION AGENT: Refill {refill_id} flagged for vet review")
    return {"refill_id": refill_id, "status": "vet_review"}


# ============================================================
# Phase 8 (F019) — Capacity Forecasting Agent (T037-T041)
# ============================================================

@app.get("/api/forecast/{clinic_id}")
def get_clinic_forecast(clinic_id: str, weeks: int = Query(4)):
    """
    T040: Run the ForecastAgent for a clinic — returns N-week projection
    using linear regression on historical completed appointments.
    """
    from .agents.forecast import ForecastAgent
    agent = ForecastAgent(db=db, log_fn=log_step)
    result = agent.forecast(clinic_id=clinic_id, project_weeks=weeks)
    return result


# ============================================================
# Integration Batch 0 — Phase 2: Integration Management
# T010-T014
# ============================================================

@app.get("/api/integrations")
def get_integration_definitions():
    """T010: List all integration definitions with status for the default clinic."""
    definitions = db.get_all_integration_definitions()
    # Attach status for first clinic (single-clinic demo)
    clinics = db.get_all_clinics()
    clinic_id = clinics[0].id if clinics else "default"
    statuses = {s["integration_id"]: s for s in db.get_all_integration_statuses(clinic_id)}
    result = []
    for defn in definitions:
        status_row = statuses.get(defn["id"])
        result.append({
            **defn,
            "status": status_row["status"] if status_row else "unconfigured",
            "latency_ms": status_row["latency_ms"] if status_row else 0,
            "error_message": status_row["error_message"] if status_row else "",
            "last_checked_at": status_row["last_checked_at"] if status_row else None,
        })
    return result


@app.get("/api/integrations/{integration_id}")
def get_integration(integration_id: str, clinic_id: str = Query("default")):
    """T010: Get one integration definition + status."""
    defs = db.get_all_integration_definitions()
    defn = next((d for d in defs if d["id"] == integration_id), None)
    if not defn:
        raise HTTPException(status_code=404, detail="Integration not found")
    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id
    status_row = db.get_integration_status(resolved_clinic, integration_id)
    return {
        **defn,
        "status": status_row["status"] if status_row else "unconfigured",
        "latency_ms": status_row["latency_ms"] if status_row else 0,
        "error_message": status_row["error_message"] if status_row else "",
        "last_checked_at": status_row["last_checked_at"] if status_row else None,
    }


@app.post("/api/integrations/{integration_id}/configure")
async def configure_integration(
    integration_id: str,
    body: IntegrationCredentialSave,
    clinic_id: str = Query("default"),
):
    """
    T011: Save credentials + run connectivity test.
    Returns status. Does NOT persist on failure (FR-INT-001).
    """
    from .agents.integration_health import run_connectivity_test

    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id

    result = run_connectivity_test(
        repo=db,
        clinic_id=resolved_clinic,
        integration_id=integration_id,
        raw_credentials=body.credentials,
        log_fn=_log1,
    )
    return result


@app.post("/api/integrations/{integration_id}/test")
async def test_integration_connection(
    integration_id: str,
    clinic_id: str = Query("default"),
):
    """
    T012: Re-run connectivity test using stored credentials.
    """
    from .agents.integration_health import run_connectivity_test, decrypt

    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id

    stored = db.get_integration_credentials(resolved_clinic, integration_id)
    if not stored:
        raise HTTPException(status_code=400, detail="No credentials stored for this integration")

    # Decrypt for re-test
    raw_creds = {}
    for row in stored:
        try:
            raw_creds[row["key_name"]] = decrypt(row["encrypted_value"])
        except Exception:
            raw_creds[row["key_name"]] = row["encrypted_value"]

    result = run_connectivity_test(
        repo=db,
        clinic_id=resolved_clinic,
        integration_id=integration_id,
        raw_credentials=raw_creds,
        log_fn=_log1,
    )
    return result


@app.delete("/api/integrations/{integration_id}/credentials")
def delete_integration_credentials(
    integration_id: str,
    clinic_id: str = Query("default"),
):
    """T013: Remove stored credentials and reset status to unconfigured."""
    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id

    db.delete_integration_credentials(resolved_clinic, integration_id)
    status = IntegrationStatus(
        clinic_id=resolved_clinic,
        integration_id=integration_id,
        status="unconfigured",
        latency_ms=0,
        error_message="",
        last_checked_at=None,
    )
    db.upsert_integration_status(status)
    _log1(f"CREDENTIALS AGENT: {integration_id.upper()} credentials removed")
    return {"integration_id": integration_id, "status": "unconfigured"}


@app.get("/api/integrations/health/summary")
def get_integration_health_summary(clinic_id: str = Query("default")):
    """T014: Returns whether any integration is disconnected (for header warning)."""
    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id
    statuses = db.get_all_integration_statuses(resolved_clinic)
    any_disconnected = any(s["status"] == "disconnected" for s in statuses)
    return {
        "clinic_id": resolved_clinic,
        "any_disconnected": any_disconnected,
        "disconnected_count": sum(1 for s in statuses if s["status"] == "disconnected"),
        "statuses": statuses,
    }


# ============================================================
# Integration Batch 0 — Phase 3: Migration
# T015-T021
# ============================================================

@app.post("/api/migration/upload")
async def start_migration(
    background_tasks: BackgroundTasks,
    source_system: str = Query("avimark"),
    clinic_id: str = Query("default"),
    file: UploadFile = File(...),
):
    """
    T016: Accept ZIP upload and start migration in background.
    Returns migration run ID immediately (HTTP 200 within 500ms).
    B-03: Uses BackgroundTasks, not asyncio.create_task.
    """
    from .agents.migration_agent import run_migration
    from uuid import uuid4

    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id

    run_id = str(uuid4())
    zip_bytes = await file.read()
    now = datetime.utcnow().isoformat()

    db.create_migration_run({
        "id": run_id,
        "clinic_id": resolved_clinic,
        "source_system": source_system,
        "status": "pending",
        "started_at": now,
    })

    _log1(f"MIGRATION AGENT: {source_system} migration started · run {run_id}")

    background_tasks.add_task(
        run_migration,
        db,
        run_id,
        resolved_clinic,
        source_system,
        zip_bytes,
        _log1,
    )

    return {"run_id": run_id, "status": "pending", "source_system": source_system}


@app.get("/api/migration/{run_id}")
def get_migration_run(run_id: str):
    """T017: Poll migration run status."""
    run = db.get_migration_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    return run


@app.get("/api/migration/{run_id}/flags")
def get_migration_flags(run_id: str):
    """T018: Get flagged records for a migration run."""
    flags = db.get_migration_flags(run_id)
    return flags


@app.get("/api/migration/{run_id}/flags/download")
def download_migration_flags(run_id: str):
    """T019: Download flagged records as CSV."""
    import csv, io
    from fastapi.responses import StreamingResponse

    flags = db.get_migration_flags(run_id)
    if not flags:
        raise HTTPException(status_code=404, detail="No flagged records found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "record_type", "reason", "source_row"])
    for flag in flags:
        source_row = flag.get("source_row", "{}")
        if isinstance(source_row, str):
            source_row_str = source_row
        else:
            import json as _json
            source_row_str = _json.dumps(source_row)
        writer.writerow([flag["id"], flag["record_type"], flag["reason"], source_row_str])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=flagged_{run_id}.csv"},
    )


@app.post("/api/migration/ezyvet")
async def start_ezyvet_migration(
    background_tasks: BackgroundTasks,
    clinic_id: str = Query("default"),
):
    """
    T021: Start ezyVet live API migration using stored credentials.
    """
    from .agents.migration_agent import run_ezyvet_migration
    from .agents.integration_health import decrypt
    from uuid import uuid4

    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id

    creds = db.get_integration_credentials(resolved_clinic, "ezyvet")
    api_key = practice_id = ""
    for c in creds:
        try:
            val = decrypt(c["encrypted_value"])
        except Exception:
            val = c["encrypted_value"]
        if c["key_name"] == "EZYVET_API_KEY":
            api_key = val
        elif c["key_name"] == "EZYVET_PRACTICE_ID":
            practice_id = val

    if not api_key:
        raise HTTPException(status_code=400, detail="ezyVet credentials not configured")

    run_id = str(uuid4())
    db.create_migration_run({
        "id": run_id,
        "clinic_id": resolved_clinic,
        "source_system": "ezyvet",
        "status": "pending",
        "started_at": datetime.utcnow().isoformat(),
    })

    background_tasks.add_task(
        run_ezyvet_migration,
        db, run_id, resolved_clinic, api_key, practice_id, _log1,
    )
    return {"run_id": run_id, "status": "pending", "source_system": "ezyvet"}


# ============================================================
# Integration Batch 0 — Phase 4: Webhook Endpoints
# T023-T030, W-03 (all async)
# ============================================================

def _get_clinic_for_webhook(integration_id: str, request: Request) -> str:
    """Resolve clinic_id from request header or credential lookup."""
    clinic_id = request.headers.get("X-Clinic-ID", "")
    if not clinic_id:
        clinics = db.get_all_clinics()
        clinic_id = clinics[0].id if clinics else "default"
    return clinic_id


async def _validate_hmac(request: Request, integration_id: str, clinic_id: str, secret_key_name: str) -> bool:
    """Validate HMAC-SHA256 signature. Returns True if valid or if no secret stored (demo mode)."""
    import hmac as _hmac, hashlib as _hashlib
    from .agents.integration_health import decrypt

    stored_enc = db.get_credential_value(clinic_id, integration_id, secret_key_name)
    if not stored_enc:
        return True  # Demo mode: no secret = skip validation
    try:
        secret = decrypt(stored_enc)
    except Exception:
        secret = stored_enc

    body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256", "") or request.headers.get("X-Signature", "")
    if not sig_header:
        return True  # No signature provided = demo mode passthrough

    expected = "sha256=" + _hmac.new(secret.encode(), body, _hashlib.sha256).hexdigest()
    return _hmac.compare_digest(expected, sig_header)


@app.post("/api/webhooks/idexx/result")
async def webhook_idexx(request: Request, background_tasks: BackgroundTasks):  # W-03: async def
    """T023: IDEXX lab result webhook. Responds HTTP 200 within 500ms."""
    from .agents.lab_agent import process_lab_result

    clinic_id = _get_clinic_for_webhook("idexx", request)
    # HMAC validation (non-blocking for demo)
    raw = await request.json()

    # Normalise IDEXX payload → LabResultPayload shape
    payload = _normalise_idexx(raw, clinic_id)

    background_tasks.add_task(process_lab_result, db, payload, _log1)
    return {"received": True, "provider": "idexx"}


@app.post("/api/webhooks/antech/result")
async def webhook_antech(request: Request, background_tasks: BackgroundTasks):  # W-03
    """T025: Antech lab result webhook."""
    from .agents.lab_agent import process_lab_result

    clinic_id = _get_clinic_for_webhook("antech", request)
    raw = await request.json()
    payload = _normalise_antech(raw, clinic_id)
    background_tasks.add_task(process_lab_result, db, payload, _log1)
    return {"received": True, "provider": "antech"}


@app.post("/api/webhooks/heska/result")
async def webhook_heska(request: Request, background_tasks: BackgroundTasks):  # W-03
    """T027: Heska lab result webhook."""
    from .agents.lab_agent import process_lab_result

    clinic_id = _get_clinic_for_webhook("heska", request)
    raw = await request.json()
    payload = _normalise_heska(raw, clinic_id)
    background_tasks.add_task(process_lab_result, db, payload, _log1)
    return {"received": True, "provider": "heska"}


@app.post("/api/webhooks/vetscan/result")
async def webhook_vetscan(request: Request, background_tasks: BackgroundTasks):  # W-03
    """T029: Vetscan webhook."""
    from .agents.lab_agent import process_lab_result

    clinic_id = _get_clinic_for_webhook("vetscan", request)
    raw = await request.json()
    payload = _normalise_vetscan(raw, clinic_id)
    background_tasks.add_task(process_lab_result, db, payload, _log1)
    return {"received": True, "provider": "vetscan"}


@app.post("/api/webhooks/imaging/result")
async def webhook_imaging(request: Request, background_tasks: BackgroundTasks):  # W-03
    """T033: Imaging/DICOM webhook."""
    from .agents.lab_agent import process_lab_result

    clinic_id = _get_clinic_for_webhook("imaging", request)
    raw = await request.json()

    # Store imaging result
    img = _normalise_imaging(raw, clinic_id)
    background_tasks.add_task(_save_imaging_result, img)
    return {"received": True, "provider": "imaging"}


def _save_imaging_result(img: dict) -> None:
    try:
        db.save_clinical_image(img)
        _log1(f"IMAGING AGENT: {img.get('modality', 'Unknown').upper()} study received · patient {img.get('patient_id', 'UNMATCHED')}")
    except Exception as e:
        _log1(f"IMAGING AGENT: [error] {e}")


# ── Payload normalisers ──────────────────────────────────────────────────────

def _normalise_idexx(raw: dict, clinic_id: str) -> dict:
    """Map IDEXX webhook payload to internal LabResultPayload shape."""
    panels = []
    for section in raw.get("results", raw.get("panels", [])):
        analytes = []
        for item in section.get("analytes", section.get("tests", [])):
            analytes.append({
                "name":  item.get("name", item.get("test_name", "")),
                "value": float(item.get("value", item.get("result", 0))),
                "unit":  item.get("unit", ""),
                "low":   float(item.get("low", item.get("reference_low", 0))),
                "high":  float(item.get("high", item.get("reference_high", 0))),
                "flag":  (item.get("flag", item.get("abnormal_flag", "")) or "").upper(),
            })
        panels.append({"name": section.get("name", "Panel"), "analytes": analytes})
    return {
        "provider": "idexx",
        "clinic_id": clinic_id,
        "lab_order_id": raw.get("lab_order_id", raw.get("order_id")),
        "patient_id": raw.get("patient_id"),
        "patient_name": raw.get("patient_name"),
        "owner_name": raw.get("owner_name", raw.get("client_name")),
        "panel_name": raw.get("panel_name", raw.get("test_name", "IDEXX Panel")),
        "panels": panels,
        "received_at": raw.get("received_at", datetime.utcnow().isoformat()),
    }


def _normalise_antech(raw: dict, clinic_id: str) -> dict:
    """Map Antech payload (different field names) to internal shape."""
    panels = []
    for section in raw.get("test_groups", raw.get("panels", [])):
        analytes = []
        for item in section.get("results", section.get("analytes", [])):
            analytes.append({
                "name":  item.get("analyte_name", item.get("name", "")),
                "value": float(item.get("result_value", item.get("value", 0))),
                "unit":  item.get("result_unit", item.get("unit", "")),
                "low":   float(item.get("range_low", item.get("low", 0))),
                "high":  float(item.get("range_high", item.get("high", 0))),
                "flag":  (item.get("flag", "") or "").upper(),
            })
        panels.append({"name": section.get("group_name", section.get("name", "Panel")), "analytes": analytes})
    return {
        "provider": "antech",
        "clinic_id": clinic_id,
        "lab_order_id": raw.get("order_number", raw.get("lab_order_id")),
        "patient_id": raw.get("patient_id"),
        "patient_name": raw.get("patient_name"),
        "owner_name": raw.get("owner_name", raw.get("client_name")),
        "panel_name": raw.get("report_name", raw.get("panel_name", "Antech Panel")),
        "panels": panels,
        "received_at": datetime.utcnow().isoformat(),
    }


def _normalise_heska(raw: dict, clinic_id: str) -> dict:
    """Map Heska VetLink payload to internal shape."""
    panels = []
    for section in raw.get("panels", raw.get("results", [])):
        analytes = []
        for item in section.get("analytes", section.get("parameters", [])):
            analytes.append({
                "name":  item.get("name", item.get("param_name", "")),
                "value": float(item.get("value", item.get("result", 0))),
                "unit":  item.get("unit", ""),
                "low":   float(item.get("low", item.get("ref_low", 0))),
                "high":  float(item.get("high", item.get("ref_high", 0))),
                "flag":  (item.get("flag", "") or "").upper(),
            })
        panels.append({"name": section.get("name", "Heska Panel"), "analytes": analytes})
    return {
        "provider": "heska",
        "clinic_id": clinic_id,
        "lab_order_id": raw.get("lab_order_id"),
        "patient_id": raw.get("patient_id"),
        "patient_name": raw.get("patient_name"),
        "owner_name": raw.get("owner_name"),
        "panel_name": raw.get("panel_name", "Heska CBC"),
        "panels": panels,
        "received_at": datetime.utcnow().isoformat(),
    }


def _normalise_vetscan(raw: dict, clinic_id: str) -> dict:
    """Map Vetscan webhook to internal shape (same as IDEXX)."""
    p = _normalise_idexx(raw, clinic_id)
    p["provider"] = "vetscan"
    return p


def _normalise_imaging(raw: dict, clinic_id: str) -> dict:
    """Build imaging record from webhook payload."""
    modality_map = {
        "CR": "xray", "DX": "xray", "XR": "xray",
        "US": "ultrasound",
        "CT": "ct",
        "MR": "mri", "MRI": "mri",
    }
    raw_modality = (raw.get("modality") or raw.get("study_type") or "xray").upper()
    modality = modality_map.get(raw_modality, raw_modality.lower())

    patient_id = raw.get("patient_id")
    if not patient_id:
        patient_name = raw.get("patient_name", "")
        owner_name = raw.get("owner_name", "")
        if patient_name:
            patients = db.get_all_patients()
            pn_lower = patient_name.lower()
            for p in patients:
                if p.get("name", "").lower() == pn_lower:
                    patient_id = p["id"]
                    break

    return {
        "patient_id": patient_id,
        "clinic_id": clinic_id,
        "source": modality,
        "modality": modality,
        "report_text": raw.get("report_text", raw.get("findings")),
        "dicom_study_uid": raw.get("dicom_study_uid", raw.get("study_uid")),
        "imaging_system": raw.get("imaging_system", raw.get("system_name")),
        "study_date": raw.get("study_date", datetime.utcnow().isoformat()[:10]),
        "filename": raw.get("filename", f"{modality}_study.dcm"),
        "caption": raw.get("caption", f"{modality.upper()} Study"),
        "data": raw.get("image_data", raw.get("data", "")),
        "content_type": "application/dicom",
        "submitted_at": datetime.utcnow().isoformat(),
    }


# ============================================================
# Integration Batch 0 — Phase 5: Lab Results Management
# T022, T032 (labs endpoints)
# ============================================================

@app.get("/api/labs/{lab_id}")
def get_lab_result(lab_id: str):
    """Get a single lab result by ID."""
    import sqlite3
    from .repository import _get_conn
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM labs WHERE id=?", (lab_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab result not found")
    result = dict(row)
    try:
        result["results"] = __import__("json").loads(result["results"] or "{}")
    except Exception:
        pass
    try:
        result["flagged_values"] = __import__("json").loads(result.get("flagged_values") or "[]")
    except Exception:
        pass
    return result


@app.post("/api/labs/{lab_id}/acknowledge")
async def acknowledge_lab_result(lab_id: str, body: LabAcknowledgeRequest):
    """T032: Acknowledge a critical lab result card."""
    ok = db.acknowledge_lab(lab_id, body.vet_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lab result not found")
    _log1(f"LAB AGENT: Critical result {lab_id} acknowledged by {body.vet_id}")
    return {"lab_id": lab_id, "acknowledged": True, "acknowledged_by": body.vet_id}


@app.post("/api/labs/{lab_id}/assign")
async def assign_lab_result(lab_id: str, body: LabAssignRequest):
    """T033: Manually assign an unmatched lab result to a patient."""
    updated = db.patch_lab(lab_id, {
        "patient_id": body.patient_id,
        "timeblock_id": body.timeblock_id,
        "status": "resulted",
    })
    if not updated:
        raise HTTPException(status_code=404, detail="Lab result not found")
    _log1(f"LAB AGENT: Unmatched result {lab_id} assigned to patient {body.patient_id}")
    return updated


@app.post("/api/lab-results/import")
async def import_vetscan_csv(
    background_tasks: BackgroundTasks,
    patient_id: Optional[str] = Query(None),
    panel_name: str = Query("Vetscan Chemistry"),
    file: UploadFile = File(...),
):
    """
    T031 (FR-INT-054): Import Vetscan/Abaxis CSV file.
    Returns lab result ID immediately, processes in background.
    """
    from .agents.lab_agent import parse_vetscan_csv, process_lab_result

    csv_text = (await file.read()).decode("utf-8-sig", errors="replace")
    payload = parse_vetscan_csv(csv_text, patient_id=patient_id, panel_name=panel_name)

    background_tasks.add_task(process_lab_result, db, payload, _log1)
    _log1(f"LAB AGENT: Vetscan CSV import queued · patient {patient_id or 'unspecified'} · {panel_name}")
    return {"status": "queued", "provider": "vetscan", "panel_name": panel_name}


# ============================================================
# Integration Batch 0 — Phase 6: Simulate Lab Result (T034)
# ============================================================

@app.post("/api/labs/simulate")
async def simulate_lab_result(
    background_tasks: BackgroundTasks,
    patient_id: str = Query(...),
    provider: str = Query("idexx"),
    panel: str = Query("CBC"),
    include_critical: bool = Query(False),
):
    """
    T034: Simulate a lab result webhook (in-house instrument demo button).
    Posts a mock result through the lab agent pipeline.
    """
    from .agents.lab_agent import process_lab_result
    import random

    def _make_analyte(name: str, low: float, high: float, critical: bool = False) -> dict:
        if critical:
            # Force HH or LL
            if random.random() > 0.5:
                val = high * 1.5
                flag = "HH"
            else:
                val = low * 0.4
                flag = "LL"
        else:
            # Normal or slightly abnormal
            if random.random() > 0.75:
                val = high * (1.0 + random.uniform(0.05, 0.25))
                flag = "H"
            elif random.random() > 0.75:
                val = low * random.uniform(0.6, 0.95)
                flag = "L"
            else:
                val = random.uniform(low, high)
                flag = ""
        return {"name": name, "value": round(val, 2), "unit": "—", "low": low, "high": high, "flag": flag}

    cbc_analytes = [
        _make_analyte("WBC",  6.0, 17.0, include_critical and random.random() > 0.7),
        _make_analyte("RBC",  5.5, 8.5),
        _make_analyte("HGB",  12.0, 18.0),
        _make_analyte("HCT",  37.0, 55.0),
        _make_analyte("PLT",  200.0, 500.0),
        _make_analyte("NEU",  3.5, 11.5),
        _make_analyte("LYM",  1.0, 4.8),
    ]
    chem_analytes = [
        _make_analyte("BUN",  7.0, 27.0, include_critical),
        _make_analyte("CREA", 0.5, 1.6),
        _make_analyte("GLU",  70.0, 120.0),
        _make_analyte("ALT",  10.0, 55.0),
        _make_analyte("ALP",  20.0, 150.0),
    ]
    analytes = cbc_analytes if "cbc" in panel.lower() else chem_analytes
    payload = {
        "provider": provider,
        "patient_id": patient_id,
        "panel_name": panel,
        "panels": [{"name": panel, "analytes": analytes}],
        "received_at": datetime.utcnow().isoformat(),
    }
    background_tasks.add_task(process_lab_result, db, payload, _log1)
    _log1(f"LAB AGENT: Simulated {panel} result posted for patient {patient_id}")
    return {"status": "queued", "provider": provider, "panel": panel}


# ============================================================
# Integration Batch 0 — Phase 7: Patient Images
# T033c (W-09)
# ============================================================

@app.get("/api/patients/{patient_id}/images")
def get_patient_images(patient_id: str, source: Optional[str] = Query(None)):
    """
    W-09: Get all images for a patient, optionally filtered by source.
    Sources: owner_upload | xray | ultrasound | ct | mri
    """
    images = db.get_images_for_patient(patient_id)
    if source:
        images = [img for img in images if img.get("source") == source]
    # Include image data for rendering in the UI
    result = []
    for img in images:
        result.append({
            "id": img["id"],
            "patient_id": img.get("patient_id"),
            "source": img.get("source", "owner_upload"),
            "modality": img.get("modality"),
            "filename": img.get("filename"),
            "caption": img.get("caption"),
            "submitted_at": img.get("submitted_at"),
            "study_date": img.get("study_date"),
            "report_text": img.get("report_text"),
            "imaging_system": img.get("imaging_system"),
            "content_type": img.get("content_type", "image/png"),
            "data": img.get("data"),
        })
    return result


# ============================================================
# Integration Batch 0 — Phase 8: Avimark Fixture (W-08 / T057)
# Generated by backend/scripts/generate_avimark_fixture.py
# ============================================================

@app.post("/api/migration/seed-avimark-fixture")
async def seed_avimark_fixture_endpoint(
    background_tasks: BackgroundTasks,
    clinic_id: str = Query("default"),
):
    """
    T057: Trigger generation and import of the 847-patient Avimark fixture.
    For demo: generates fixture in memory and runs migration synchronously.
    """
    from .scripts.generate_avimark_fixture import generate_avimark_zip
    from .agents.migration_agent import run_migration
    from uuid import uuid4

    clinics = db.get_all_clinics()
    resolved_clinic = clinic_id
    if clinic_id == "default" and clinics:
        resolved_clinic = clinics[0].id

    zip_bytes = generate_avimark_zip()
    run_id = str(uuid4())
    db.create_migration_run({
        "id": run_id,
        "clinic_id": resolved_clinic,
        "source_system": "avimark",
        "status": "pending",
        "started_at": datetime.utcnow().isoformat(),
    })

    background_tasks.add_task(
        run_migration, db, run_id, resolved_clinic, "avimark", zip_bytes, _log1
    )
    return {"run_id": run_id, "status": "pending", "message": "Avimark 847-patient fixture migration started"}


# ============================================================
# spec-007 — Platform Account & Subscription Routes (T029–T041)
# ============================================================

from .agents.account_agent import (
    get_modules_with_status as _get_modules_with_status,
    compute_trial_days_remaining,
    validate_module_add,
    generate_invoice_line_items,
    next_invoice_number as _next_invoice_number,
    MODULE_PRICING, MODULE_TIER_REQUIREMENTS, PLAN_PRICES, PLAN_ORDER,
)


def _get_demo_account_or_404():
    account = db.get_default_account()
    if not account:
        raise HTTPException(status_code=404, detail="No account found. Seed has not run yet.")
    return account


@app.get("/api/account")
def get_account():
    """T029: Return demo account with computed fields."""
    account = _get_demo_account_or_404()
    result = dict(account)
    # Compute trial_days_remaining
    if result.get("trial_ends_at"):
        result["trial_days_remaining"] = compute_trial_days_remaining(result["trial_ends_at"])
    else:
        result["trial_days_remaining"] = 0
    # Attach active_module_count
    licenses = db.get_module_licenses(account["id"])
    result["active_module_count"] = sum(1 for lic in licenses if lic.get("status") == "active")
    return result


@app.put("/api/account")
def update_account(body: AccountUpdateRequest):
    """T030: Update account contact details."""
    account = _get_demo_account_or_404()
    updates = body.model_dump(exclude_none=True)
    updated = db.update_account(account["id"], updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found")
    _log1(f"ACCOUNT AGENT: Account updated — {updated.get('name', account['name'])}")
    # Re-fetch with computed fields
    result = dict(updated)
    if result.get("trial_ends_at"):
        result["trial_days_remaining"] = compute_trial_days_remaining(result["trial_ends_at"])
    else:
        result["trial_days_remaining"] = 0
    licenses = db.get_module_licenses(updated["id"])
    result["active_module_count"] = sum(1 for lic in licenses if lic.get("status") == "active")
    return result


@app.get("/api/account/modules")
def get_account_modules():
    """T031: Return all 9 modules with license status."""
    account = _get_demo_account_or_404()
    return _get_modules_with_status(db, account["id"])


@app.post("/api/account/modules/{module_id}")
async def subscribe_module(
    module_id: str,
    body: ModuleSubscribeRequest = Body(default=ModuleSubscribeRequest()),
):
    """T032 (W-05 fix): Purchase a module license. Empty body is accepted."""
    account = _get_demo_account_or_404()

    # validate_module_add: check already active (409), plan tier (403)
    if db.account_has_module(account["id"], module_id):
        raise HTTPException(status_code=409, detail=f"{module_id} is already active for this account.")

    err = validate_module_add(account, module_id, db)
    if err:
        _log1(f"ACCOUNT AGENT: {module_id} add blocked — {err}")
        raise HTTPException(status_code=403, detail=err)

    price_cents = MODULE_PRICING.get(module_id, 0)
    lic = db.add_module_license(account["id"], module_id, price_cents, body.billing_interval)
    _log1(f"ACCOUNT AGENT: {module_id} license added · ${price_cents / 100:.0f}/mo")

    # Generate subscription invoice for new module (Gap 2)
    try:
        from .agents.account_agent import next_invoice_number, MODULE_DESCRIPTIONS
        from datetime import timedelta
        now_dt = datetime.utcnow()
        month_start = now_dt.date().replace(day=1).isoformat()
        next_month = (now_dt.date().replace(day=1) + timedelta(days=32)).replace(day=1)
        month_end = (next_month - timedelta(days=1)).isoformat()
        mod_name, _ = MODULE_DESCRIPTIONS.get(module_id, (module_id, ""))
        inv_num = next_invoice_number(db, account["id"])
        db.create_account_invoice({
            "account_id": account["id"],
            "invoice_number": inv_num,
            "period_start": month_start,
            "period_end": month_end,
            "line_items": [{"description": f"{module_id} {mod_name} — first month", "amount_cents": price_cents}],
            "subtotal_cents": price_cents,
            "total_cents": price_cents,
            "status": "pending",
            "created_at": now_dt.isoformat(),
        })
        log_agent_step("VERA (Account)", f"Invoice {inv_num} generated for {module_id} activation")
    except Exception as e:
        log_agent_step("VERA (Account)", f"[warn] Module invoice generation failed — {e}")

    return {
        "module_id": module_id,
        "status": "active",
        "price_cents": price_cents,
        "purchased_at": lic.get("purchased_at"),
    }


@app.delete("/api/account/modules/{module_id}")
def cancel_module(module_id: str):
    """T033: Cancel a module license."""
    account = _get_demo_account_or_404()
    success = db.cancel_module_license(account["id"], module_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"{module_id} is not licensed for this account.")
    _log1(f"ACCOUNT AGENT: {module_id} license cancelled")
    return {"module_id": module_id, "status": "cancelled"}


@app.get("/api/account/invoices")
def get_account_invoices():
    """T034: List invoices newest first."""
    account = _get_demo_account_or_404()
    return db.get_account_invoices(account["id"])


class GenerateInvoiceRequest(BaseModel):
    period_start: Optional[str] = None
    period_end: Optional[str] = None


@app.post("/api/account/invoices", status_code=201)
def generate_account_invoice(body: GenerateInvoiceRequest):
    """Gap 4: Manually generate a billing invoice for the current period."""
    from .agents.account_agent import generate_invoice_line_items, next_invoice_number
    from datetime import timedelta
    account = db.get_default_account()
    if not account:
        raise HTTPException(status_code=404, detail="No account found")
    now_dt = datetime.utcnow()
    period_start = body.period_start or now_dt.date().replace(day=1).isoformat()
    if body.period_end:
        period_end = body.period_end
    else:
        next_month = (now_dt.date().replace(day=1) + timedelta(days=32)).replace(day=1)
        period_end = (next_month - timedelta(days=1)).isoformat()
    licenses = db.get_module_licenses(account["id"])
    line_items = generate_invoice_line_items(account, licenses)
    subtotal = sum(li["amount_cents"] for li in line_items)
    inv_num = next_invoice_number(db, account["id"])
    inv = db.create_account_invoice({
        "account_id": account["id"],
        "invoice_number": inv_num,
        "period_start": period_start,
        "period_end": period_end,
        "line_items": line_items,
        "subtotal_cents": subtotal,
        "total_cents": subtotal,
        "status": "pending",
        "created_at": now_dt.isoformat(),
    })
    log_agent_step("VERA (Account)", f"Invoice {inv_num} manually generated — ${subtotal/100:.2f}")
    return inv


@app.get("/api/account/invoices/{invoice_id}")
def get_account_invoice(invoice_id: str):
    """T035: Single invoice detail."""
    inv = db.get_account_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@app.get("/api/account/clinics")
def get_account_clinics():
    """T036: All clinics for this account."""
    account = _get_demo_account_or_404()
    return db.get_clinics_for_account(account["id"])


@app.post("/api/account/clinics", status_code=201)
def create_account_clinic(body: Clinic):
    """T037: Add clinic to account. Professional+ only. B-02 fix: set account_id after create."""
    account = _get_demo_account_or_404()
    tier = account.get("plan_tier", "starter")
    if tier == "starter":
        raise HTTPException(status_code=403, detail="Adding clinics requires Professional or Enterprise plan.")
    # Create the clinic
    created = db.create_clinic(body)
    # B-02 fix: set account_id separately
    db.set_clinic_account(body.id, account["id"])
    result = created.model_dump()
    result["account_id"] = account["id"]
    _log1(f"ACCOUNT AGENT: New clinic added — {body.name}")
    return result


@app.get("/api/account/plan")
def get_account_plan():
    """T038: Return current tier, price, upgrade/downgrade options."""
    account = _get_demo_account_or_404()
    current_tier = account.get("plan_tier", "starter")
    current_price = PLAN_PRICES.get(current_tier, 0)
    current_idx = PLAN_ORDER.index(current_tier)

    upgrade_options = []
    downgrade_options = []
    tier_features = {
        "starter": ["1 clinic", "Core scheduling", "Basic reporting"],
        "professional": ["Up to 5 clinics", "All professional modules", "Advanced analytics"],
        "enterprise": ["Unlimited clinics", "MOD-ENT included", "Priority support", "SSO"],
    }
    for tier in PLAN_ORDER:
        if tier == current_tier:
            continue
        price = PLAN_PRICES[tier]
        delta = price - current_price
        idx = PLAN_ORDER.index(tier)
        if idx > current_idx:
            upgrade_options.append({
                "tier": tier,
                "price_cents": price,
                "delta_cents": delta,
                "features": tier_features.get(tier, []),
            })
        else:
            downgrade_options.append({
                "tier": tier,
                "price_cents": price,
                "delta_cents": delta,
                "note": "Downgrading will cancel all active module licenses",
            })

    return {
        "current_tier": current_tier,
        "current_price_cents": current_price,
        "upgrade_options": upgrade_options,
        "downgrade_options": downgrade_options,
    }


@app.post("/api/account/plan/upgrade")
def upgrade_account_plan(body: PlanUpgradeRequest):
    """T039: Change plan tier. Auto-add MOD-ENT if upgrading to Enterprise."""
    account = _get_demo_account_or_404()
    if body.plan_tier not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier: {body.plan_tier}")
    old_tier = account.get("plan_tier", "starter")
    new_tier = body.plan_tier

    current_price = PLAN_PRICES.get(old_tier, 0)
    new_price = PLAN_PRICES.get(new_tier, 0)
    proration = abs(new_price - current_price) // 2

    db.update_account(account["id"], {"plan_tier": new_tier})
    _log1(f"ACCOUNT AGENT: Plan upgraded {old_tier.capitalize()} → {new_tier.capitalize()}")

    message = f"Plan changed to {new_tier.capitalize()}."
    # Auto-add MOD-ENT on Enterprise upgrade
    if new_tier == "enterprise" and not db.account_has_module(account["id"], "MOD-ENT"):
        db.add_module_license(account["id"], "MOD-ENT", MODULE_PRICING["MOD-ENT"], "monthly")
        _log1("ACCOUNT AGENT: MOD-ENT license added · $149/mo (Enterprise included)")
        message = "Plan upgraded to Enterprise. MOD-ENT has been added at no extra charge."

    # Generate upgrade invoice for upgrades only (Gap 3)
    try:
        from .agents.account_agent import PLAN_PRICES as _PLAN_PRICES, next_invoice_number
        from datetime import timedelta
        now_dt = datetime.utcnow()
        old_price = _PLAN_PRICES.get(old_tier, 0)
        new_price = _PLAN_PRICES.get(new_tier, 0)
        delta = new_price - old_price
        if delta > 0:
            month_start = now_dt.date().replace(day=1).isoformat()
            next_month = (now_dt.date().replace(day=1) + timedelta(days=32)).replace(day=1)
            month_end = (next_month - timedelta(days=1)).isoformat()
            inv_num = next_invoice_number(db, account["id"])
            db.create_account_invoice({
                "account_id": account["id"],
                "invoice_number": inv_num,
                "period_start": month_start,
                "period_end": month_end,
                "line_items": [{"description": f"Plan upgrade: {old_tier.capitalize()} → {new_tier.capitalize()}", "amount_cents": delta}],
                "subtotal_cents": delta,
                "total_cents": delta,
                "status": "pending",
                "created_at": now_dt.isoformat(),
            })
            log_agent_step("VERA (Account)", f"Invoice {inv_num} generated for plan upgrade to {new_tier}")
    except Exception as e:
        log_agent_step("VERA (Account)", f"[warn] Upgrade invoice generation failed — {e}")

    return {
        "account_id": account["id"],
        "old_tier": old_tier,
        "new_tier": new_tier,
        "proration_cents": proration,
        "message": message,
    }


# ── T040: Module access stub routes (require_module enforcement) ────────────

@app.get("/api/mods/fin/status")
def mod_fin_status(_=Depends(require_module("MOD-FIN"))):
    return {"module": "MOD-FIN", "access": "granted"}

@app.get("/api/mods/com/status")
def mod_com_status(_=Depends(require_module("MOD-COM"))):
    return {"module": "MOD-COM", "access": "granted"}

@app.get("/api/mods/inv/status")
def mod_inv_status(_=Depends(require_module("MOD-INV"))):
    return {"module": "MOD-INV", "access": "granted"}

@app.get("/api/mods/tel/status")
def mod_tel_status(_=Depends(require_module("MOD-TEL"))):
    return {"module": "MOD-TEL", "access": "granted"}

@app.get("/api/mods/anl/status")
def mod_anl_status(_=Depends(require_module("MOD-ANL"))):
    return {"module": "MOD-ANL", "access": "granted"}

@app.get("/api/mods/mar/status")
def mod_mar_status(_=Depends(require_module("MOD-MAR"))):
    return {"module": "MOD-MAR", "access": "granted"}

@app.get("/api/mods/stf/status")
def mod_stf_status(_=Depends(require_module("MOD-STF"))):
    return {"module": "MOD-STF", "access": "granted"}

@app.get("/api/mods/ref/status")
def mod_ref_status(_=Depends(require_module("MOD-REF"))):
    return {"module": "MOD-REF", "access": "granted"}

@app.get("/api/mods/ent/status")
def mod_ent_status(_=Depends(require_module("MOD-ENT"))):
    return {"module": "MOD-ENT", "access": "granted"}


# ── Gap 1: Visit Invoice routes ──────────────────────────────────────────────

@app.get("/api/appointments/{timeblock_id}/invoice")
def get_appointment_invoice(timeblock_id: str):
    """Get visit invoice draft for a completed appointment."""
    invs = db.get_visit_invoices_for_timeblock(timeblock_id)
    if not invs:
        raise HTTPException(status_code=404, detail="No invoice for this appointment")
    return invs[0]


@app.get("/api/visit-invoices")
def list_visit_invoices(clinic_id: str = Query(None), status: str = Query(None)):
    """List visit invoices, optionally filtered by clinic_id or status."""
    return db.get_visit_invoices(clinic_id=clinic_id, status=status)


@app.put("/api/visit-invoices/{invoice_id}")
async def update_visit_invoice(invoice_id: str, request: Request):
    """Update a visit invoice (line items, notes, status, etc.)."""
    body = await request.json()
    inv = db.update_visit_invoice(invoice_id, body)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@app.post("/api/visit-invoices/{invoice_id}/send")
def send_visit_invoice(invoice_id: str):
    """Mark a visit invoice as sent."""
    inv = db.update_visit_invoice(invoice_id, {"status": "sent", "sent_at": datetime.utcnow().isoformat()})
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    log_agent_step("VERA (Billing)", f"Visit invoice {invoice_id[:8]} marked as sent")
    return inv


@app.post("/api/visit-invoices/{invoice_id}/mark-paid")
def mark_visit_invoice_paid(invoice_id: str):
    """Mark a visit invoice as paid."""
    inv = db.update_visit_invoice(invoice_id, {"status": "paid", "paid_at": datetime.utcnow().isoformat()})
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    log_agent_step("VERA (Billing)", f"Visit invoice {invoice_id[:8]} marked as paid")
    return inv


# ── Gap 5: Account Users routes ──────────────────────────────────────────────

@app.get("/api/account/users")
def get_account_users():
    """Gap 5: Return all users on the account."""
    account = db.get_default_account()
    if not account:
        raise HTTPException(status_code=404, detail="No account")
    return db.get_account_users(account["id"])


class AccountUserCreate(BaseModel):
    name: str
    email: str
    role: str = "member"


@app.post("/api/account/users", status_code=201)
def add_account_user(body: AccountUserCreate):
    """Gap 5: Add a user to the account."""
    account = db.get_default_account()
    if not account:
        raise HTTPException(status_code=404, detail="No account")
    from uuid import uuid4
    user = {
        "id": str(uuid4()),
        "account_id": account["id"],
        "name": body.name,
        "email": body.email,
        "role": body.role,
        "created_at": datetime.utcnow().isoformat(),
    }
    db.create_account_user(user)
    log_agent_step("VERA (Account)", f"User {body.email} added as {body.role}")
    return user


@app.delete("/api/account/users/{user_id}", status_code=204)
def remove_account_user(user_id: str):
    """Gap 5: Remove a user from the account."""
    from .repository import _get_conn
    with _get_conn() as conn:
        conn.execute("DELETE FROM account_users WHERE id=?", (user_id,))
    log_agent_step("VERA (Account)", f"User {user_id[:8]} removed")
    return


# =============================================================================
# S07 — VPMA Online Booking Portal
# Public routes: /public/*   (no staff auth required)
# Staff routes:  /api/clinics/{id}/booking-config  (soft-gated with X-Staff-Token)
# =============================================================================

from .agents.availability_agent import AvailabilityAgent
from .agents.booking_agent import BookingAgent, LIFECYCLE_STATES
from .agents.intake_delivery_agent import IntakeDeliveryAgent, INTAKE_QUESTION_SETS, run_flag_logic
import re as _re
from datetime import timedelta as _timedelta

_avail_agent = AvailabilityAgent(db, log_fn=log_step)
_booking_agent = BookingAgent(db, log_fn=log_step)
_intake_agent = IntakeDeliveryAgent(db, log_fn=log_step)

# ── Helpers ──────────────────────────────────────────────────────────────────

SESSION_COOKIE = "vpma_session"
SESSION_TTL_SECONDS = 1800  # 30 minutes
PORTAL_BASE_URL = "https://book.vpma.app"


def _normalize_phone(raw: str) -> str:
    """Strip all non-digit characters and return a 10-digit US number."""
    digits = _re.sub(r"\D", "", raw or "")
    return digits[-10:] if len(digits) >= 10 else digits


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _new_session_expires() -> str:
    return (datetime.utcnow() + _timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()


def _get_valid_session(request: Request) -> Optional[dict]:
    """Read session cookie, validate expiry, return session row or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = db.get_session(token)
    if not session:
        return None
    if session.get("expires_at", "") < datetime.utcnow().isoformat():
        return None
    # Extend session
    new_exp = _new_session_expires()
    db.touch_session(token, new_exp)
    return session


def _pet_age_years(dob_str: Optional[str]) -> Optional[float]:
    if not dob_str:
        return None
    try:
        dob = datetime.fromisoformat(dob_str)
        delta = datetime.utcnow() - dob
        return round(delta.days / 365.25, 1)
    except (ValueError, TypeError):
        return None


def _last_visit_label(last_visit_date: Optional[str]) -> Optional[str]:
    if not last_visit_date:
        return None
    try:
        lv = datetime.fromisoformat(last_visit_date)
        delta = datetime.utcnow() - lv
        months = int(delta.days / 30)
        if months < 1:
            return "This month"
        if months == 1:
            return "1 month ago"
        return f"{months} months ago"
    except (ValueError, TypeError):
        return None


def _build_pet_summary(pet: dict) -> dict:
    return {
        "id": pet["id"],
        "name": pet.get("name", ""),
        "species": pet.get("species", ""),
        "breed": pet.get("breed", ""),
        "age_years": _pet_age_years(pet.get("dob")),
        "last_visit_label": _last_visit_label(pet.get("last_visit_date")),
        "care_due": False,
        "care_due_reason": None,
    }


# ── Route 1: GET /public/clinics/{clinic_id} ─────────────────────────────────

@app.get("/public/clinics/{clinic_id}")
def public_get_clinic(clinic_id: str, request: Request):
    """S07 R1: Public clinic info + booking config for the booking portal."""
    clinic = db.get_clinic(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    config = db.get_booking_config(clinic_id) or {}
    appt_types = db.get_bookable_appointment_types(clinic_id)
    return {
        "id": clinic["id"],
        "name": clinic.get("name", ""),
        "address": clinic.get("address", ""),
        "phone": clinic.get("phone", ""),
        "email": clinic.get("email", ""),
        "timezone": clinic.get("timezone", "America/Los_Angeles"),
        "slug": clinic.get("slug"),
        "online_booking_enabled": bool(config.get("online_booking_enabled", False)),
        "advance_booking_days": config.get("advance_booking_days", 60),
        "min_booking_notice_hours": config.get("min_booking_notice_hours", 2),
        "cancellation_policy": config.get("cancellation_policy", ""),
        "emergency_phone": config.get("emergency_phone", ""),
        "show_vet_names": config.get("show_vet_names", True),
        "bookable_appointment_types": appt_types,
    }


# ── Route 2: GET /public/clinics/{clinic_id}/availability ────────────────────

@app.get("/public/clinics/{clinic_id}/availability")
def public_get_availability(
    clinic_id: str,
    appointment_type_id: str = Query(..., description="Appointment type slug"),
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD (default: start + 7 days)"),
    resource_id: Optional[str] = Query(None),
    request: Request = None,
):
    """S07 R2: List available slots for a clinic + appointment type."""
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_availability", max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    clinic = db.get_clinic(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    config = db.get_booking_config(clinic_id) or {}
    if not config.get("online_booking_enabled", False):
        raise HTTPException(status_code=404, detail="Online booking not enabled for this clinic")

    # Resolve appointment type and duration
    appt_types = db.get_bookable_appointment_types(clinic_id)
    appt_type = next((t for t in appt_types
                      if t["slug"] == appointment_type_id or t["id"] == appointment_type_id), None)
    if not appt_type:
        raise HTTPException(status_code=400, detail="Invalid appointment_type_id")

    duration = appt_type.get("duration_min", 30)
    advance_days = config.get("advance_booking_days", 60)
    min_notice_hours = config.get("min_booking_notice_hours", 2)

    try:
        start_dt = datetime.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    else:
        end_dt = start_dt + _timedelta(days=7)

    # Clamp to advance_booking window
    max_end = datetime.utcnow() + _timedelta(days=advance_days)
    if end_dt > max_end:
        end_dt = max_end

    # Enforce min_notice
    earliest = datetime.utcnow() + _timedelta(hours=min_notice_hours)
    if start_dt < earliest:
        start_dt = earliest

    hidden_vets = config.get("hidden_vet_ids", [])
    slots = _avail_agent.get_slots(
        clinic_id=clinic_id,
        appointment_type_id=appointment_type_id,
        duration_minutes=duration,
        start_date=start_dt,
        end_date=end_dt,
        resource_id=resource_id,
        buffer_minutes=config.get("buffer_minutes", 10),
        hidden_vet_ids=hidden_vets,
    )

    return {"slots": slots, "total": len(slots)}


# ── Route 3: POST /public/owners/lookup ──────────────────────────────────────

@app.post("/public/owners/lookup")
def public_owner_lookup(body: OwnerLookupRequest, request: Request, response: Response = None):
    """S07 R3: Look up an existing owner by phone or email."""
    from fastapi.responses import JSONResponse
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_owner_lookup", max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if not body.phone and not body.email:
        raise HTTPException(status_code=400, detail="phone or email required")

    clinic = db.get_clinic(body.clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    phone_norm = _normalize_phone(body.phone) if body.phone else None
    owner = db.lookup_owner_by_phone_or_email(phone_norm, body.email)

    if not owner:
        resp_body = {"found": False, "owner_id": None, "display_name": None, "pets": []}
        return JSONResponse(content=resp_body)

    # Build session
    token = str(_uuid.uuid4())
    expires_at = _new_session_expires()
    db.create_session(token, owner["id"], body.clinic_id, expires_at)

    pets = db.get_pets_for_owner(owner["id"])
    pet_summaries = [_build_pet_summary(p) for p in pets]

    first_name = owner.get("first_name") or (owner.get("name", "").split()[0] if owner.get("name") else "")

    log_step(f"VERA (Booking): owner_lookup found owner={owner['id'][:8]} clinic={body.clinic_id[:8]}")

    resp_body = {
        "found": True,
        "owner_id": owner["id"],
        "display_name": first_name,
        "pets": pet_summaries,
    }
    json_resp = JSONResponse(content=resp_body)
    json_resp.set_cookie(
        key=SESSION_COOKIE, value=token, httponly=True,
        max_age=SESSION_TTL_SECONDS, samesite="lax"
    )
    return json_resp


# ── Route 4: POST /public/owners/register ────────────────────────────────────

@app.post("/public/owners/register", status_code=201)
def public_owner_register(body: OwnerRegisterRequest, request: Request):
    """S07 R4: Register a new owner + first pet."""
    from fastapi.responses import JSONResponse
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_owner_register", max_requests=5, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Validate
    if not body.first_name.strip() or not body.last_name.strip():
        raise HTTPException(status_code=400, detail="first_name and last_name required")
    if not body.phone:
        raise HTTPException(status_code=400, detail="phone required")
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="Valid email required")

    phone_norm = _normalize_phone(body.phone)
    # Duplicate check
    existing = db.lookup_owner_by_phone_or_email(phone_norm, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Owner already registered with this phone or email")

    owner_id = str(_uuid.uuid4())
    patient_id = str(_uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Create owner
    full_name = f"{body.first_name.strip()} {body.last_name.strip()}"
    owner_data = {
        "id": owner_id,
        "name": full_name,
        "first_name": body.first_name.strip(),
        "last_name": body.last_name.strip(),
        "phone": phone_norm,
        "email": body.email.strip().lower(),
        "patient_ids": [patient_id],
        "sms_consent": body.sms_consent,
        "portal_opt_in": True,
        "home_clinic_id": body.clinic_id,
        "created_at": now,
    }
    db.create_owner_from_registration(owner_data)

    # Create patient
    from .models import Patient as PatientModel
    patient = PatientModel(
        id=patient_id,
        name=body.pet.name.strip(),
        species=body.pet.species,
        breed=body.pet.breed or "",
        dob=body.pet.dob_approx or "",
        weight_kg=0.0,
        owner_id=owner_id,
        home_clinic_id=body.clinic_id,
        visit_count=0,
        flags=[],
        flag_notes="",
    )
    db.save_patient(patient)

    # Session
    token = str(_uuid.uuid4())
    expires_at = _new_session_expires()
    db.create_session(token, owner_id, body.clinic_id, expires_at)

    log_step(f"VERA (Booking): owner_registered owner={owner_id[:8]} patient={patient_id[:8]} clinic={body.clinic_id[:8]}")

    resp_body = {
        "owner_id": owner_id,
        "patient_id": patient_id,
        "display_name": body.first_name.strip(),
    }
    json_resp = JSONResponse(content=resp_body, status_code=201)
    json_resp.set_cookie(
        key=SESSION_COOKIE, value=token, httponly=True,
        max_age=SESSION_TTL_SECONDS, samesite="lax"
    )
    return json_resp


# ── Route 5 (implicit): session already created in lookup/register above ─────

# ── Route 6: GET /public/owners/{owner_id}/pets ──────────────────────────────

@app.get("/public/owners/{owner_id}/pets")
def public_get_owner_pets(owner_id: str, request: Request):
    """S07 R6: Return pets for session-authenticated owner."""
    session = _get_valid_session(request)
    if not session or session.get("owner_id") != owner_id:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    owner = db.get_owner(owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    pets = db.get_pets_for_owner(owner_id)
    first_name = owner.get("first_name") or (owner.get("name", "").split()[0] if owner.get("name") else "")
    return {
        "owner_id": owner_id,
        "display_name": first_name,
        "pets": [_build_pet_summary(p) for p in pets],
    }


# ── Route 7: POST /public/bookings/hold ──────────────────────────────────────

@app.post("/public/bookings/hold")
def public_booking_hold(body: BookingHoldRequest, request: Request):
    """S07 R7: Create a soft-hold on a slot."""
    import sqlite3
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_booking_hold", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    session = _get_valid_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    session_token = request.cookies.get(SESSION_COOKIE)

    # Validate resource belongs to clinic
    resources = db.get_resources_for_clinic(body.clinic_id)
    resource = next((r for r in resources if r["id"] == body.resource_id), None)
    if not resource:
        raise HTTPException(status_code=400, detail="resource_id not found in this clinic")

    # Validate appointment type
    appt_types = db.get_bookable_appointment_types(body.clinic_id)
    appt_type = next((t for t in appt_types
                      if t["slug"] == body.appointment_type_id or t["id"] == body.appointment_type_id), None)
    if not appt_type:
        raise HTTPException(status_code=400, detail="Invalid appointment_type_id")

    # Check availability
    available = db.check_slot_available(
        body.resource_id, body.start_datetime, body.end_datetime,
        exclude_session_token=session_token
    )
    if not available:
        raise HTTPException(status_code=409, detail="Slot already held or booked")

    # Release any previous hold for this session
    db.delete_holds_for_session(session_token)
    # Clean up globally expired holds
    db.expire_stale_holds()

    # Compute UUID5 slot_id
    import uuid as _uuid_mod
    try:
        start_dt_obj = datetime.fromisoformat(body.start_datetime)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_datetime")
    slot_id = str(_uuid_mod.uuid5(_uuid_mod.NAMESPACE_URL, f"{body.resource_id}:{start_dt_obj.isoformat()}"))

    hold_id = str(_uuid.uuid4())
    hold_expires = (datetime.utcnow() + _timedelta(minutes=10)).isoformat()

    try:
        db.create_slot_hold({
            "id": hold_id,
            "resource_id": body.resource_id,
            "start_datetime": body.start_datetime,
            "end_datetime": body.end_datetime,
            "clinic_id": body.clinic_id,
            "session_token": session_token,
            "expires_at": hold_expires,
            "created_at": datetime.utcnow().isoformat(),
        })
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Slot already held or booked")

    vet_name = resource.get("name", "Vet")
    log_step(f"VERA (Booking): slot_held hold={hold_id[:8]} resource={body.resource_id[:8]} start={body.start_datetime}")

    return {
        "hold_id": hold_id,
        "slot_id": slot_id,
        "expires_at": hold_expires,
        "resource_id": body.resource_id,
        "vet_name": vet_name,
        "start_datetime": body.start_datetime,
        "end_datetime": body.end_datetime,
    }


# ── Route 8: POST /public/bookings ───────────────────────────────────────────

@app.post("/public/bookings", status_code=201)
def public_confirm_booking(
    body: BookingConfirmRequest,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """S07 R8: Confirm a booking. Atomic hold→timeblock→tokens."""
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_confirm_booking", max_requests=5, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    session = _get_valid_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    session_token = request.cookies.get(SESSION_COOKIE)

    if not body.cancellation_policy_accepted:
        raise HTTPException(status_code=400, detail="Must accept cancellation policy")
    if body.urgency not in {"wellness", "routine", "urgent", "emergency"}:
        raise HTTPException(status_code=400, detail="Invalid urgency value")

    try:
        result = _booking_agent.confirm_booking(
            session_token=session_token,
            hold_id=body.hold_id,
            patient_id=body.patient_id,
            appointment_type_id=body.appointment_type_id,
            urgency=body.urgency,
            notes=body.notes,
            sms_consent=body.sms_consent,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower() or "expired" in detail.lower():
            code = 404
        elif "double-booking" in detail.lower() or "no longer" in detail.lower():
            code = 409
        else:
            code = 400
        raise HTTPException(status_code=code, detail=detail)

    booking_token_id = result["booking_token_id"]
    intake_token_id = result["intake_token_id"]
    timeblock_id = result["timeblock_id"]
    start_dt_str = result["start_datetime"]
    clinic_id = result["clinic_id"]

    try:
        appt_dt = datetime.fromisoformat(start_dt_str)
    except (ValueError, TypeError):
        appt_dt = datetime.utcnow()

    # Resolve vet name from resource
    resources = db.get_resources_for_clinic(clinic_id)
    resource = next((r for r in resources if r["id"] == result["resource_id"]), None)
    vet_name = resource.get("name", "Your Vet") if resource else "Your Vet"

    clinic = db.get_clinic(clinic_id)
    clinic_name = clinic.get("name", "") if clinic else ""
    clinic_address = clinic.get("address", "") if clinic else ""

    # Background tasks
    background_tasks.add_task(
        _intake_agent.schedule_delivery, intake_token_id, appt_dt
    )
    background_tasks.add_task(
        _booking_agent.arm_reminders, timeblock_id, booking_token_id,
        result["owner_id"], appt_dt
    )

    log_step(
        f"VERA (Booking): booking_confirmed timeblock={timeblock_id[:8]} "
        f"token={booking_token_id[:8]} clinic={clinic_id[:8]}"
    )

    return {
        "booking_id": timeblock_id,
        "booking_token": booking_token_id,
        "status": "booked",
        "status_url": f"{PORTAL_BASE_URL}/status/{booking_token_id}",
        "intake_url": f"{PORTAL_BASE_URL}/intake/{intake_token_id}",
        "appointment": {
            "date": appt_dt.strftime("%Y-%m-%d"),
            "time": appt_dt.strftime("%H:%M"),
            "duration_minutes": 30,
            "vet_name": vet_name,
            "clinic_name": clinic_name,
            "address": clinic_address,
        },
    }


# ── Route 9: GET /public/status/{booking_token} ──────────────────────────────

@app.get("/public/status/{booking_token}")
def public_booking_status(booking_token: str, request: Request):
    """S07 R9: Public appointment status tracker."""
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_booking_status", max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    bt = db.get_booking_token(booking_token)
    if not bt:
        raise HTTPException(status_code=404, detail="Booking token not found")

    now_iso = datetime.utcnow().isoformat()
    if bt.get("expires_at", "") < now_iso:
        raise HTTPException(status_code=410, detail="This booking link has expired")

    # Fetch linked timeblock
    from .repository import _get_conn
    with _get_conn() as conn:
        tb_row = conn.execute(
            "SELECT * FROM timeblocks WHERE id=?", (bt["timeblock_id"],)
        ).fetchone()
        if not tb_row:
            raise HTTPException(status_code=404, detail="Appointment not found")
        tb = dict(tb_row)

        if tb.get("status") == "cancelled":
            raise HTTPException(status_code=410, detail="This booking has been cancelled")

        # Resolve patient, owner, resource, clinic, intake token
        patient_row = conn.execute(
            "SELECT name FROM patients WHERE id=?", (tb.get("patient_id"),)
        ).fetchone()
        owner_row = conn.execute(
            "SELECT first_name, name FROM owners WHERE id=?", (bt["owner_id"],)
        ).fetchone()

        import json as _json
        resource_ids = _json.loads(tb.get("resource_ids", "[]"))
        vet_name = "Vet"
        if resource_ids:
            res_row = conn.execute(
                "SELECT name FROM resources WHERE id=?", (resource_ids[0],)
            ).fetchone()
            if res_row:
                vet_name = res_row[0]

        clinic_row = conn.execute(
            "SELECT name, address, phone FROM clinics WHERE id=?", (bt["clinic_id"],)
        ).fetchone()

        intake_row = conn.execute(
            "SELECT token, used FROM intake_tokens WHERE timeblock_id=? LIMIT 1",
            (tb["id"],)
        ).fetchone()

    pet_name = patient_row[0] if patient_row else "Your Pet"
    owner_fn = ""
    if owner_row:
        owner_fn = owner_row[0] or (owner_row[1].split()[0] if owner_row[1] else "")
    clinic_name = clinic_row[0] if clinic_row else ""
    clinic_address = clinic_row[1] if clinic_row else ""
    clinic_phone = clinic_row[2] if clinic_row else ""

    intake_token_val = intake_row[0] if intake_row else None
    intake_used = bool(intake_row[1]) if intake_row else False
    intake_status = "complete" if intake_used else ("sent" if intake_token_val else None)

    try:
        start_dt = datetime.fromisoformat(tb["start_time"])
        end_dt = datetime.fromisoformat(tb["end_time"])
        duration_min = int((end_dt - start_dt).total_seconds() / 60)
    except (ValueError, TypeError):
        duration_min = 30

    # Determine lifecycle state
    if tb.get("status") == "complete":
        lc_state = "complete"
    elif tb.get("followup_status") == "sent":
        lc_state = "follow_up_sent"
    elif tb.get("intake_status") == "received":
        lc_state = "intake_complete"
    elif intake_status == "sent":
        lc_state = "intake_sent"
    else:
        lc_state = "booked"

    lifecycle = BookingAgent.build_lifecycle(lc_state)
    cancellable = (tb.get("status") not in ("cancelled", "complete")
                   and tb.get("start_time", "") > now_iso)

    return {
        "booking_id": bt["timeblock_id"],
        "booking_token": booking_token,
        "status": tb.get("status", "scheduled"),
        "clinic_name": clinic_name,
        "clinic_phone": clinic_phone,
        "clinic_address": clinic_address,
        "pet_name": pet_name,
        "owner_display_name": owner_fn,
        "appointment_type": tb.get("appointment_type_id", ""),
        "vet_name": vet_name,
        "start_datetime": tb.get("start_time", ""),
        "duration_minutes": duration_min,
        "lifecycle": lifecycle,
        "intake_token": intake_token_val,
        "intake_status": intake_status,
        "intake_url": f"{PORTAL_BASE_URL}/intake/{intake_token_val}" if intake_token_val else None,
        "cancellable": cancellable,
        "reschedulable": False,
        "calendar_url": f"/public/status/{booking_token}/calendar.ics",
    }


# ── Route 10: GET /public/intake/{intake_token} ──────────────────────────────

@app.get("/public/intake/{intake_token}")
def public_get_intake(intake_token: str, request: Request):
    """S07 R10: Fetch intake form questions and any saved responses."""
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_intake_get", max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    token_row = db.get_intake_token(intake_token)
    if not token_row:
        raise HTTPException(status_code=404, detail="Intake token not found")

    now_iso = datetime.utcnow().isoformat()
    if token_row.get("expires_at", "") < now_iso:
        raise HTTPException(status_code=410, detail="This intake form has expired")
    if token_row.get("used"):
        raise HTTPException(status_code=409, detail="Intake form already submitted")

    appointment_type = token_row.get("appointment_type", "wellness")
    timeblock_id = token_row["timeblock_id"]

    from .repository import _get_conn
    with _get_conn() as conn:
        tb_row = conn.execute(
            "SELECT start_time, patient_id FROM timeblocks WHERE id=?", (timeblock_id,)
        ).fetchone()
        patient_row = conn.execute(
            "SELECT name FROM patients WHERE id=?",
            (tb_row[1] if tb_row else "",)
        ).fetchone() if tb_row else None

        import json as _json
        res_rows = conn.execute(
            "SELECT resource_ids FROM timeblocks WHERE id=? LIMIT 1", (timeblock_id,)
        ).fetchone()
        vet_name = "Your Vet"
        if res_rows:
            try:
                rids = _json.loads(res_rows[0] or "[]")
                if rids:
                    rr = conn.execute("SELECT name FROM resources WHERE id=?", (rids[0],)).fetchone()
                    if rr:
                        vet_name = rr[0]
            except Exception:
                pass

        clinic_row = None
        if tb_row:
            clinic_row = conn.execute(
                "SELECT name FROM clinics c JOIN timeblocks t ON t.clinic_id=c.id WHERE t.id=? LIMIT 1",
                (timeblock_id,)
            ).fetchone()

    pet_name = patient_row[0] if patient_row else "Your Pet"
    appointment_date = ""
    if tb_row and tb_row[0]:
        try:
            appointment_date = datetime.fromisoformat(tb_row[0]).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    clinic_name = clinic_row[0] if clinic_row else ""

    questions = _intake_agent.get_questions(appointment_type, pet_name, vet_name)

    # Load any previously saved responses
    existing_resp = db.get_intake_response(intake_token)
    if existing_resp:
        answers_map = {a["question_id"]: a["answer"] for a in existing_resp.get("answers", [])}
        for q in questions:
            q["answer"] = answers_map.get(q["id"])

    completed_count = sum(1 for q in questions if q.get("answer") is not None)

    return {
        "intake_id": intake_token,
        "appointment_type": appointment_type,
        "pet_name": pet_name,
        "vet_name": vet_name,
        "appointment_date": appointment_date,
        "clinic_name": clinic_name,
        "status": "in_progress" if existing_resp else "sent",
        "questions": questions,
        "total_questions": len(questions),
        "completed_questions": completed_count,
        "estimated_minutes": max(1, len(questions) // 3),
    }


# ── Route 11: POST /public/intake/{intake_token}/submit ──────────────────────

@app.post("/public/intake/{intake_token}/submit")
def public_submit_intake(intake_token: str, body: IntakeSubmitRequest, request: Request):
    """S07 R11: Submit intake form answers."""
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, f"intake_submit:{intake_token}", max_requests=3, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    token_row = db.get_intake_token(intake_token)
    if not token_row:
        raise HTTPException(status_code=404, detail="Intake token not found")

    now_iso = datetime.utcnow().isoformat()
    if token_row.get("expires_at", "") < now_iso:
        raise HTTPException(status_code=410, detail="This intake form has expired")
    if token_row.get("used"):
        raise HTTPException(status_code=409, detail="Intake already submitted")

    appointment_type = token_row.get("appointment_type", "wellness")
    answers_raw = [a.model_dump() for a in body.answers]

    # Validate answers
    valid, missing_ids, err_msg = _intake_agent.validate_answers(appointment_type, answers_raw)
    if not valid:
        raise HTTPException(
            status_code=400,
            detail={"detail": err_msg, "missing_questions": missing_ids}
        )

    # Run flag logic
    answers_dict = {
        a["question_id"]: a.get("answer", "") or ""
        for a in answers_raw
        if not a.get("skipped")
    }
    raised_flags = run_flag_logic(appointment_type, answers_dict)

    # Persist response
    db.save_intake_response(
        intake_token=intake_token,
        timeblock_id=token_row["timeblock_id"],
        owner_id=token_row["owner_id"],
        answers=answers_raw,
        flags=raised_flags,
        submitted_at=body.submitted_at or now_iso,
    )

    # Mark token used + update timeblock intake_status
    db.mark_intake_token_used(intake_token)
    from .repository import _get_conn
    with _get_conn() as conn:
        conn.execute(
            "UPDATE timeblocks SET intake_status='received' WHERE id=?",
            (token_row["timeblock_id"],)
        )

    # Resolve vet name for confirmation message
    with _get_conn() as conn:
        res_row = conn.execute(
            "SELECT r.name FROM resources r "
            "JOIN timeblocks t ON r.id = json_extract(t.resource_ids, '$[0]') "
            "WHERE t.id=? LIMIT 1",
            (token_row["timeblock_id"],)
        ).fetchone()
    vet_display = res_row[0] if res_row else "your vet"

    # Booking status URL (via booking token)
    booking_token_val = None
    with _get_conn() as conn:
        bt_row = conn.execute(
            "SELECT token FROM booking_tokens WHERE timeblock_id=? LIMIT 1",
            (token_row["timeblock_id"],)
        ).fetchone()
    if bt_row:
        booking_token_val = bt_row[0]

    if raised_flags:
        log_step(f"VERA (Intake): intake_submitted flags_raised={raised_flags} token={intake_token[:8]}")
    log_step(f"VERA (Intake): intake_submitted token={intake_token[:8]} flags={len(raised_flags)}")

    return {
        "status": "complete",
        "flags_raised": len(raised_flags),
        "flag_names": raised_flags,
        "message": f"Thank you! {vet_display} will review this before your visit.",
        "booking_status_url": f"{PORTAL_BASE_URL}/status/{booking_token_val}" if booking_token_val else None,
    }


# ── Route 12: POST /public/waitlist ──────────────────────────────────────────

@app.post("/public/waitlist", status_code=201)
def public_join_waitlist(body: WaitlistJoinRequest, request: Request):
    """S07 R12: Join the waitlist for a clinic + appointment type."""
    ip = _get_client_ip(request)
    if not db.check_rate_limit(ip, "public_waitlist", max_requests=3, window_seconds=600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Validate clinic
    clinic = db.get_clinic(body.clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    config = db.get_booking_config(body.clinic_id) or {}

    # Validate urgency
    if body.urgency not in {"wellness", "routine", "urgent"}:
        raise HTTPException(status_code=400, detail="Invalid urgency value")

    # Validate min_notice_hours
    if body.min_notice_hours not in (1, 3, 24):
        raise HTTPException(status_code=400, detail="min_notice_hours must be 1, 3, or 24")

    # Validate time_preferences
    valid_prefs = {"weekday_morning", "weekday_afternoon", "saturday_morning", "any"}
    bad_prefs = [p for p in body.time_preferences if p not in valid_prefs]
    if bad_prefs:
        raise HTTPException(status_code=400, detail=f"Invalid time_preferences: {bad_prefs}")

    phone_norm = _normalize_phone(body.phone)

    # Duplicate check
    dup = db.duplicate_waitlist_check(body.clinic_id, body.patient_id, body.appointment_type_id)
    if dup:
        raise HTTPException(status_code=409, detail="Already on waitlist for this appointment type")

    entry_id = str(_uuid.uuid4())
    db.join_waitlist({
        "id": entry_id,
        "clinic_id": body.clinic_id,
        "owner_id": body.owner_id,
        "patient_id": body.patient_id,
        "appointment_type": body.appointment_type_id,
        "urgency": body.urgency,
        "time_preferences": body.time_preferences,
        "sms_consent": body.sms_consent,
        "phone_for_sms": phone_norm,
        "min_notice_hours": body.min_notice_hours,
    })

    position = db.get_waitlist_position(body.clinic_id, body.appointment_type_id, entry_id)
    formatted_phone = f"({phone_norm[:3]}) {phone_norm[3:6]}-{phone_norm[6:]}" if len(phone_norm) == 10 else phone_norm

    log_step(f"VERA (Booking): waitlist_joined clinic={body.clinic_id[:8]} patient={body.patient_id[:8]} pos={position}")

    return {
        "waitlist_id": entry_id,
        "position": position,
        "message": f"You're on the waitlist. We'll notify you at {formatted_phone} when a slot opens.",
        "manage_url": None,
    }


# ── Route 13: GET /api/clinics/{clinic_id}/booking-config ────────────────────

@app.get("/api/clinics/{clinic_id}/booking-config")
def get_booking_config(clinic_id: str, request: Request):
    """S07 R13 (staff): Fetch current booking configuration for a clinic."""
    # Soft-gate: log header presence but do not block in Phase 1
    staff_token = request.headers.get("X-Staff-Token")
    log_step(f"VERA (Booking): get_booking_config clinic={clinic_id[:8]} staff_token={'present' if staff_token else 'missing'}")

    config = db.get_booking_config(clinic_id)
    appt_types = db.get_bookable_appointment_types(clinic_id)

    if not config:
        # Return default (all defaults, online_booking_enabled=False)
        return {
            "clinic_id": clinic_id,
            "online_booking_enabled": False,
            "advance_booking_days": 60,
            "same_day_cutoff_hour": 14,
            "min_booking_notice_hours": 2,
            "cancellation_policy": "Cancellations within 24 hours may incur a fee.",
            "emergency_phone": "",
            "hidden_vet_ids": [],
            "bookable_appointment_types": appt_types,
        }

    config["bookable_appointment_types"] = appt_types
    return config


# ── Route 14: PUT /api/clinics/{clinic_id}/booking-config ────────────────────

@app.put("/api/clinics/{clinic_id}/booking-config")
def update_booking_config(clinic_id: str, body: ClinicBookingConfigUpdate, request: Request):
    """S07 R14 (staff): Create or update clinic booking configuration (upsert)."""
    staff_token = request.headers.get("X-Staff-Token")
    log_step(f"VERA (Booking): update_booking_config clinic={clinic_id[:8]} staff_token={'present' if staff_token else 'missing'}")

    clinic = db.get_clinic(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    # Validate ranges
    if "advance_booking_days" in updates:
        val = updates["advance_booking_days"]
        if not (7 <= val <= 90):
            raise HTTPException(status_code=400, detail="advance_booking_days must be 7–90")
    if "buffer_minutes" in updates:
        val = updates["buffer_minutes"]
        if not (0 <= val <= 60):
            raise HTTPException(status_code=400, detail="buffer_minutes must be 0–60")
    if "same_day_cutoff_hour" in updates:
        val = updates["same_day_cutoff_hour"]
        if not (0 <= val <= 23):
            raise HTTPException(status_code=400, detail="same_day_cutoff_hour must be 0–23")

    # Auto-generate slug if enabling online booking and clinic has no slug
    if updates.get("online_booking_enabled") and not clinic.get("slug"):
        import re as _re2
        raw_slug = clinic["name"].lower()
        slug = _re2.sub(r"[^a-z0-9]+", "-", raw_slug).strip("-")
        from .repository import _get_conn
        with _get_conn() as conn:
            conn.execute("UPDATE clinics SET slug=? WHERE id=?", (slug, clinic_id))
        log_step(f"VERA (Booking): auto-slug generated slug={slug} clinic={clinic_id[:8]}")

    # Serialize bookable_appointment_types if present
    if "bookable_appointment_types" in updates and updates["bookable_appointment_types"]:
        # Not stored in clinic_booking_config; handled separately in Phase 2
        updates.pop("bookable_appointment_types", None)

    config = db.upsert_booking_config(clinic_id, updates)
    appt_types = db.get_bookable_appointment_types(clinic_id)
    config["bookable_appointment_types"] = appt_types
    return config


# ============================================================
# Feature 008 — Vera Onboarding Routes
# All routes prefixed /api/onboarding/
# ============================================================

# --- Startup: init onboarding tables ---
@app.on_event("startup")
def _init_onboarding_db():
    try:
        from .onboarding_repository import onboarding_repo
        onboarding_repo.init_db()
        log_step("VERA (Onboarding): DB tables initialized")
    except Exception as e:
        print(f"[ONBOARDING] DB init error (non-fatal): {e}")


# --- Imports (lazy within route handlers to avoid circular imports at startup) ---


# T005 + T018 + T020-T022 + T025-T026 + T034

@app.post("/api/onboarding/session")
async def create_onboarding_session(request: Request):
    """Create a new onboarding session (Phase 0 — WELCOME)."""
    try:
        from .agents.onboarding_agent import OnboardingAgent
        from .models import OnboardingSessionCreate
        import json as _json
        body = await request.json()
        device_fp = body.get("device_fingerprint")
        agent = OnboardingAgent()
        result = agent.handle_session_create(device_fp)
        response = Response(
            content=_json.dumps(result),
            media_type="application/json",
        )
        # Set httpOnly cookie
        response.set_cookie(
            key="onboarding_session",
            value=result["session_token"],
            max_age=2592000,  # 30 days
            httponly=True,
            samesite="lax",
        )
        log_step(result["verbose_log"][0] if result.get("verbose_log") else "VERA (Onboarding): session created")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/session/create")
async def create_onboarding_session_post(request: Request):
    """Create onboarding session — body-based endpoint (JS fetch friendly)."""
    try:
        from .agents.onboarding_agent import OnboardingAgent
        import json as _json
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        device_fp = body.get("device_fingerprint")
        agent = OnboardingAgent()
        result = agent.handle_session_create(device_fp)
        log_step(result["verbose_log"][0] if result.get("verbose_log") else "VERA (Onboarding): session created")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/onboarding/session/{session_token}")
def get_onboarding_session(session_token: str):
    """Retrieve session state by cookie token."""
    try:
        from .onboarding_repository import onboarding_repo
        session = onboarding_repo.get_session_by_token(session_token)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/onboarding/resume/{magic_token}")
def resume_onboarding_session(magic_token: str):
    """Resume a session from a magic link click (FR-035, FR-036)."""
    try:
        from .agents.onboarding_agent import OnboardingAgent
        agent = OnboardingAgent()
        result = agent.handle_session_resume(magic_token)
        if result.get("error") == "invalid_or_expired":
            raise HTTPException(status_code=403, detail="Magic link is invalid, expired, or already used")
        log_step(result["verbose_log"][0] if result.get("verbose_log") else "VERA (Onboarding): session resumed")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/onboarding/session/{session_id}")
async def patch_onboarding_session(session_id: str, request: Request):
    """Update session fields (phase, role, practice_name, state_json, track)."""
    try:
        from .onboarding_repository import onboarding_repo
        from .agents.onboarding_agent import OnboardingAgent
        body = await request.json()

        agent = OnboardingAgent()
        logs = []

        # Handle role selection with agent
        if "persona_role" in body:
            role_result = agent.handle_role_selection(session_id, body["persona_role"])
            logs.extend(role_result.get("verbose_log", []))

        # Handle practice name with agent
        if "practice_name" in body and isinstance(body.get("practice_name"), str):
            name_result = agent.handle_practice_name(session_id, body["practice_name"])
            logs.extend(name_result.get("verbose_log", []))
        else:
            # Direct patch for other fields
            patch_fields = {k: v for k, v in body.items()
                            if k in {"phase", "track", "state_json"}}
            if patch_fields:
                onboarding_repo.patch_session(session_id, **patch_fields)
                logs.append(f"VERA (Onboarding): Session {session_id[:8]} updated — {list(patch_fields.keys())}")

        for entry in logs:
            log_step(entry)

        session = onboarding_repo.get_session_by_id(session_id)
        return {**(session or {}), "verbose_log": logs}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/magic-link")
async def send_magic_link(request: Request):
    """Issue a 30-day magic link for session resume (FR-008b)."""
    try:
        from .agents.onboarding_agent import OnboardingAgent
        body = await request.json()
        session_id = body.get("session_id", "")
        email = body.get("email", "")
        if not session_id or not email:
            raise HTTPException(status_code=400, detail="session_id and email required")
        agent = OnboardingAgent()
        result = agent.handle_magic_link_request(session_id, email)
        log_step(result["verbose_log"][0])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/open-prompt")
async def onboarding_open_prompt(request: Request):
    """Process Q2 open prompt (free-text or URL) and extract practice context."""
    try:
        from .agents.onboarding_agent import OnboardingAgent
        body = await request.json()
        session_id = body.get("session_id", "")
        text = body.get("text", "")
        if not session_id or not text:
            raise HTTPException(status_code=400, detail="session_id and text required")
        agent = OnboardingAgent()
        result = agent.handle_open_prompt(session_id, text)
        for entry in result.get("verbose_log", []):
            log_step(entry)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/upload")
async def upload_onboarding_document(
    file: UploadFile = File(...),
    session_id: str = Query(...),
):
    """
    Upload a document for Vera's extraction pipeline.
    25MB limit enforced. Supported: CSV, XLSX, XLS, PDF, DOC, DOCX, PNG, JPG, JPEG, WEBP, GIF, HEIC.
    """
    import os as _os
    from .onboarding_repository import onboarding_repo, UPLOADS_DIR
    from .agents.document_parser_agent import classify_document

    MAX_SIZE = 26_214_400  # 25MB in bytes
    ALLOWED_MIMES = {
        "text/csv", "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/png", "image/jpeg", "image/webp", "image/gif", "image/heic",
    }

    try:
        content = await file.read()
        size = len(content)

        if size > MAX_SIZE:
            size_mb = round(size / 1_048_576, 1)
            raise HTTPException(
                status_code=400,
                detail=f"That file is {size_mb}MB — I can handle up to 25MB. Can you export a smaller version, or paste the key columns as text?",
            )

        mime = file.content_type or "application/octet-stream"
        # Also allow by extension for files with wrong MIME
        ext = _os.path.splitext(file.filename or "")[1].lower()
        ext_to_mime = {
            ".csv": "text/csv", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel", ".pdf": "application/pdf",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif", ".heic": "image/heic",
        }
        if mime not in ALLOWED_MIMES and ext in ext_to_mime:
            mime = ext_to_mime[ext]

        if mime not in ALLOWED_MIMES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {mime}")

        # Save to staging
        _os.makedirs(UPLOADS_DIR, exist_ok=True)
        import uuid as _uuid2
        safe_name = f"{str(_uuid2.uuid4())}{ext}"
        storage_path = _os.path.join(UPLOADS_DIR, safe_name)
        with open(storage_path, "wb") as f_out:
            f_out.write(content)

        # Create document record
        doc = onboarding_repo.create_document(session_id, mime, size, storage_path)

        # Classify immediately
        classified = classify_document(storage_path, mime)
        onboarding_repo.update_document_status(doc["id"], "pending", classified_type=classified)

        log_entry = f"VERA (Onboarding): File received — {classified} ({ext.lstrip('.').upper()}, {round(size/1024)}KB)"
        log_step(log_entry)

        return {
            "document_id": doc["id"],
            "mime_type": mime,
            "file_size_bytes": size,
            "classified_type": classified,
            "streaming_status": "pending",
            "verbose_log": [log_entry],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/onboarding/extract-stream/{document_id}")
async def extract_stream(document_id: str):
    """
    SSE stream — extract entities from an uploaded document.
    Streams partial results within 2s (FR-022a).
    30-second hard cap with graceful surface (FR-022b).
    """
    import json as _json
    import asyncio
    from fastapi.responses import StreamingResponse as _SSE
    from .onboarding_repository import onboarding_repo
    from .agents.document_parser_agent import (
        classify_document, parse_csv, parse_xlsx, parse_pdf, parse_image
    )
    import os as _os
    import time as _time

    doc = onboarding_repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_path = doc["storage_path"]
    mime_type = doc["mime_type"]
    ext = _os.path.splitext(storage_path)[1].lower()

    # Mark in-progress
    onboarding_repo.update_document_status(document_id, "in_progress")

    async def event_generator():
        start_time = _time.time()
        TIMEOUT = 30.0
        entity_count = 0
        timed_out = False

        yield f"data: {_json.dumps({'type': 'start', 'message': 'Reading your file...'})}\n\n"

        try:
            # Select parser
            if ext == ".csv":
                parser = parse_csv(storage_path)
            elif ext in (".xlsx", ".xls"):
                parser = parse_xlsx(storage_path)
            elif ext == ".pdf":
                parser = parse_pdf(storage_path)
            elif ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic"):
                parser = parse_image(storage_path)
            else:
                yield f"data: {_json.dumps({'type': 'error', 'message': 'Unsupported file type'})}\n\n"
                return

            for raw_entity in parser:
                elapsed = _time.time() - start_time

                # 30-second hard cap
                if elapsed >= TIMEOUT:
                    timed_out = True
                    yield f"data: {_json.dumps({'type': 'timeout', 'message': 'I got most of it — still working in the background. You can confirm what is here and I will add the rest shortly.'})}\n\n"
                    break

                # Handle tab_found notifications
                entity_type = raw_entity.get("entity_type", "")
                if entity_type == "tab_found":
                    msg = raw_entity.get("extracted_fields", {}).get("message", "Found a tab...")
                    yield f"data: {_json.dumps({'type': 'tab_found', 'message': msg})}\n\n"
                    continue

                if entity_type == "error":
                    err_msg = raw_entity.get("extracted_fields", {}).get("error", "Parse error")
                    yield f"data: {_json.dumps({'type': 'error', 'message': err_msg})}\n\n"
                    continue

                if entity_type == "raw_text":
                    yield f"data: {_json.dumps({'type': 'raw_text', 'message': 'OCR text extracted — reviewing...'})}\n\n"
                    continue

                # Save entity to DB
                try:
                    saved = onboarding_repo.create_extracted_entity(
                        document_id=document_id,
                        entity_type=raw_entity.get("entity_type", "unknown"),
                        source_text=raw_entity.get("source_text", ""),
                        confidence=raw_entity.get("confidence", 0.5),
                        fields=raw_entity.get("extracted_fields", {}),
                        position=raw_entity.get("source_position"),
                    )
                    entity_id = saved["id"]
                except Exception:
                    entity_id = "unsaved"

                confidence = raw_entity.get("confidence", 0.5)
                if confidence >= 0.8:
                    confidence_label = "high"
                elif confidence >= 0.5:
                    confidence_label = "medium"
                else:
                    confidence_label = "low"

                fields = raw_entity.get("extracted_fields", {})
                display = fields.get("name", raw_entity.get("source_text", "entity"))

                event_data = {
                    "type": "entity",
                    "entity_id": entity_id,
                    "entity_type": raw_entity.get("entity_type", "unknown"),
                    "display": display,
                    "confidence": confidence,
                    "confidence_label": confidence_label,
                    "source_text": raw_entity.get("source_text", ""),
                    "extracted_fields": fields,
                }
                yield f"data: {_json.dumps(event_data)}\n\n"
                entity_count += 1

                # Small async yield to allow event loop to breathe
                await asyncio.sleep(0.01)

        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        # Final status
        final_status = "timed_out" if timed_out else "complete"
        onboarding_repo.update_document_status(document_id, final_status)
        log_step(f"VERA (Onboarding): Extraction {final_status} — {entity_count} entities found")

        yield f"data: {_json.dumps({'type': 'done', 'entity_count': entity_count, 'status': final_status})}\n\n"

    return _SSE(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/onboarding/confirm-entity/{entity_id}")
async def confirm_onboarding_entity(entity_id: str, request: Request):
    """Confirm or correct an extracted entity (FR-024 through FR-027)."""
    try:
        from .onboarding_repository import onboarding_repo
        body = await request.json()
        confirmed = body.get("confirmed", True)
        correction = body.get("correction")  # {field_name, correct_value}

        entity = onboarding_repo.get_entity(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        corrected = False
        if correction and isinstance(correction, dict):
            field_name = correction.get("field_name", "")
            correct_value = correction.get("correct_value", "")
            vera_value = entity.get("extracted_fields", {}).get(field_name, "")
            if field_name and correct_value:
                onboarding_repo.correct_entity(
                    entity_id, field_name, vera_value, correct_value,
                    entity.get("confidence", 0.5),
                )
                corrected = True
                log_step(f"VERA (Onboarding): Entity corrected — {field_name}: '{vera_value}' → '{correct_value}' (training signal logged)")
        else:
            onboarding_repo.confirm_entity(entity_id)

        if not corrected:
            log_step(f"VERA (Onboarding): Entity confirmed — {entity.get('entity_type')} '{entity.get('source_text', '')[:40]}'")

        return {
            "entity_id": entity_id,
            "confirmed": confirmed,
            "corrected": corrected,
            "verbose_log": [
                f"VERA (Onboarding): Entity {'corrected' if corrected else 'confirmed'} — {entity.get('entity_type')}"
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/scrape-logo")
async def scrape_logo(request: Request):
    """
    Scrape best logo candidate from a URL.
    Cascade: og:image → link[rel=icon] → header img → favicon → monogram.
    """
    try:
        from .onboarding_repository import onboarding_repo
        body = await request.json()
        session_id = body.get("session_id", "")
        url = body.get("url", "")
        if not session_id or not url:
            raise HTTPException(status_code=400, detail="session_id and url required")

        result = _scrape_logo_cascade(session_id, url)
        for entry in result.get("verbose_log", []):
            log_step(entry)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _scrape_logo_cascade(session_id: str, url: str) -> dict:
    """
    Logo scraping cascade: og:image → link[rel=icon] → largest header img → favicon → monogram.
    Returns a logo asset dict with source_type, image_url/initials.
    """
    from .onboarding_repository import onboarding_repo

    logs = []
    candidates = []

    try:
        import httpx
        from bs4 import BeautifulSoup
        import re as _re

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; VetAgent/1.0; +https://vetagent.app/bot)"
        }
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")

        base_url = f"{resp.url.scheme}://{resp.url.host}"

        # 1. og:image
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og and og.get("content"):
            candidates.append(("og_image", og["content"]))

        # 2. Apple touch icon / large icon
        for rel_val in ["apple-touch-icon", "icon"]:
            tag = soup.find("link", rel=lambda r: r and rel_val in r)
            if tag and tag.get("href"):
                href = tag["href"]
                if not href.startswith("http"):
                    href = base_url + href
                candidates.append(("favicon", href))

        # 3. Largest image in header/nav
        for section in soup.find_all(["header", "nav"]):
            for img in section.find_all("img"):
                src = img.get("src", "")
                if src and not src.endswith(".gif"):
                    if not src.startswith("http"):
                        src = base_url + src
                    candidates.append(("header_img", src))

        # 4. /favicon.ico fallback
        candidates.append(("favicon", base_url + "/favicon.ico"))

    except Exception as e:
        logs.append(f"VERA (Onboarding): Logo scrape error — {str(e)[:80]}")

    # Pick first valid candidate
    asset = None
    for source_type, image_url in candidates:
        try:
            import httpx
            with httpx.Client(timeout=4.0) as client:
                r = client.head(image_url)
            if r.status_code < 400:
                asset = onboarding_repo.create_logo_asset(
                    session_id=session_id,
                    source_type=source_type,
                    source_url=image_url,
                    initials=None,
                )
                logs.append(f"VERA (Onboarding): Logo found via {source_type} — pending confirmation")
                return {
                    "logo_asset_id": asset["id"],
                    "source_type": source_type,
                    "image_url": image_url,
                    "fallback_type": "image",
                    "initials": None,
                    "verbose_log": logs,
                }
        except Exception:
            continue

    # Monogram fallback
    session = onboarding_repo.get_session_by_id(session_id)
    practice_name = (session or {}).get("practice_name", "Practice")
    initials = _generate_initials(practice_name)
    asset = onboarding_repo.create_logo_asset(
        session_id=session_id,
        source_type="monogram",
        source_url=None,
        initials=initials,
    )
    logs.append(f"VERA (Onboarding): No logo found — initials monogram '{initials}' generated")
    return {
        "logo_asset_id": asset["id"],
        "source_type": "monogram",
        "image_url": None,
        "fallback_type": "monogram",
        "initials": initials,
        "verbose_log": logs,
    }


def _generate_initials(name: str) -> str:
    """Generate initials monogram from practice name (e.g. 'Riverside Animal Hospital' → 'RAH')."""
    stop_words = {"animal", "hospital", "clinic", "veterinary", "vet", "care", "center",
                  "the", "of", "and", "for", "a", "an"}
    words = name.split()
    significant = [w for w in words if w.lower() not in stop_words]
    if not significant:
        significant = words
    initials = "".join(w[0].upper() for w in significant if w)
    return initials[:4]  # max 4 chars


@app.post("/api/onboarding/confirm-logo/{logo_asset_id}")
async def confirm_logo(logo_asset_id: str, request: Request):
    """Confirm, cycle, or replace the logo asset (FR-017, FR-018, FR-020)."""
    try:
        from .onboarding_repository import onboarding_repo
        body = await request.json()
        action = body.get("action", "confirm")  # confirm | try_next | upload

        if action == "confirm":
            asset = onboarding_repo.confirm_logo_asset(logo_asset_id)
            if not asset:
                raise HTTPException(status_code=404, detail="Logo asset not found")
            log_step("VERA (Onboarding): Logo confirmed — placed in practice header")
            return {
                "logo_asset_id": logo_asset_id,
                "confirmed": True,
                "source_type": asset.get("source_type", "unknown"),
                "verbose_log": ["VERA (Onboarding): Logo confirmed — placed in practice header"],
            }

        elif action == "try_next":
            # Return next unconfirmed asset for session (or monogram if none)
            with __import__("sqlite3").connect(__import__("os").path.join(__import__("os").path.dirname(__file__), "scheduler.db")) as conn:
                conn.row_factory = __import__("sqlite3").Row
                # Get session_id from this asset
                row = conn.execute("SELECT session_id FROM logo_assets WHERE id=?", (logo_asset_id,)).fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Logo asset not found")
                session_id = row["session_id"]
                # Get next unconfirmed, not this asset
                next_row = conn.execute(
                    "SELECT * FROM logo_assets WHERE session_id=? AND id!=? AND confirmed=0 ORDER BY created_at",
                    (session_id, logo_asset_id),
                ).fetchone()
            if next_row:
                next_asset = dict(next_row)
                log_step(f"VERA (Onboarding): Showing next logo candidate — {next_asset['source_type']}")
                return {
                    "logo_asset_id": next_asset["id"],
                    "confirmed": False,
                    "source_type": next_asset["source_type"],
                    "image_url": next_asset.get("source_url"),
                    "initials": next_asset.get("initials"),
                    "verbose_log": [f"VERA (Onboarding): Showing next logo candidate — {next_asset['source_type']}"],
                }
            else:
                log_step("VERA (Onboarding): No more logo candidates — offering upload")
                return {
                    "logo_asset_id": logo_asset_id,
                    "confirmed": False,
                    "source_type": "none",
                    "message": "No more candidates — want to upload yours?",
                    "verbose_log": ["VERA (Onboarding): No more logo candidates — offering upload"],
                }

        elif action == "upload":
            # Upload path — frontend sends file separately; here we just acknowledge
            log_step("VERA (Onboarding): Logo upload requested — awaiting file")
            return {
                "logo_asset_id": logo_asset_id,
                "confirmed": False,
                "source_type": "upload",
                "verbose_log": ["VERA (Onboarding): Logo upload requested"],
            }

        raise HTTPException(status_code=400, detail="action must be confirm|try_next|upload")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/go-live")
async def go_live(request: Request):
    """
    Trigger the Replace event (FR-028 to FR-033).
    Creates live Clinic + Resource records, archives Harmony demo,
    returns role-appropriate first_action_targets.
    """
    try:
        from .agents.onboarding_agent import OnboardingAgent
        body = await request.json()
        session_id = body.get("session_id", "")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")

        agent = OnboardingAgent()
        result = agent.handle_go_live(session_id)

        # Get persona role for boundary statement
        from .onboarding_repository import onboarding_repo
        session = onboarding_repo.get_session_by_id(session_id)
        persona_role = (session or {}).get("persona_role", "owner")

        boundary = agent.handle_post_replace_intro(session_id, persona_role)
        result["boundary_statement"] = boundary["message"]
        result["verbose_log"].extend(boundary.get("verbose_log", []))

        for entry in result.get("verbose_log", []):
            log_step(entry)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/activation")
async def record_activation(request: Request):
    """Record activation event — first real client appointment booked (FR-033)."""
    try:
        from .agents.onboarding_agent import OnboardingAgent
        body = await request.json()
        session_id = body.get("session_id", "")
        booking_id = body.get("booking_id", "")
        if not session_id or not booking_id:
            raise HTTPException(status_code=400, detail="session_id and booking_id required")
        agent = OnboardingAgent()
        result = agent.handle_activation(session_id, booking_id)
        log_step(result["verbose_log"][0])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
