from fastapi import FastAPI, HTTPException, Query, Request, BackgroundTasks, UploadFile, File, Body, Depends
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
    return p.model_dump()

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
    log_agent_step("INTAKE AGENT", f"Sent pre-visit questionnaire to owner ({owner_name}) for {patient_name}")
    log_agent_step("INTAKE AGENT", "Photo attachment option included in owner message")
    return {"status": "pending", "message": intake_msg}

@app.post("/api/intake/parse")
def intake_parse(req: IntakeParseRequest):
    tb = db.get_timeblock(req.timeblock_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Timeblock not found")

    # Extract symptoms
    log_agent_step("INTAKE AGENT", "Owner response received — extracting symptoms...")
    intake_agent = IntakeAgent()
    extracted = intake_agent.extract_symptoms(req.owner_response)

    # Log extracted symptoms
    sym_str = ", ".join(
        f"{s['name']} ({s['duration_days']}d, {s['severity']})"
        for s in extracted["symptoms"]
    ) if extracted["symptoms"] else "none detected"
    log_agent_step("INTAKE AGENT", f"Parsed → {sym_str}")
    log_agent_step("INTAKE AGENT", f"Suggested focus areas: {', '.join(extracted['suggested_focus']) or 'general assessment'}")

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
    log_agent_step("INTAKE AGENT", "Pre-Exam Brief saved")

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

    log_agent_step("SOAP AGENT", f"Draft generated from {(procedure or 'General')} template" + (" + intake brief" if brief and brief.status == "received" else ""))
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
        log_agent_step("FOLLOWUP AGENT", f"{'Wellness' if draft.tone == 'wellness' else draft.tone.capitalize()} follow-up draft generated for {patient.name if patient else 'patient'}")

    return {
        "signed": True,
        "signed_at": signed.signed_at if signed else None,
        "followup_draft_id": followup_draft_id,
    }


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
    log_agent_step("FOLLOWUP AGENT", f"{draft.tone.capitalize()} follow-up draft generated for {patient.name if patient else 'patient'}")
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
    log_agent_step("FOLLOWUP AGENT", "Follow-up approved and sent (simulated)")
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
    log_agent_step("DISPATCH", f"Appointment {timeblock_id[:8]}... marked complete")

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
        log_agent_step("FOLLOWUP AGENT", f"{draft.tone.capitalize()} follow-up draft generated for {patient.name if patient else 'patient'} ({owner.name if owner else ''})")
        draft_id = draft.id
    else:
        draft_id = existing_draft.id

    return {"status": "complete", "followup_draft_id": draft_id}


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

def _is_vague(text: str) -> bool:
    lower = text.lower()
    has_procedure = any(kw in lower for kw in _PROCEDURE_HINTS)
    return not has_procedure

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
    # Strip binary data for listing (only keep metadata)
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
