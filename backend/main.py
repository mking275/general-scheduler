from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, List
from .repository import db
from .models import (
    ResourceType, Patient, Owner, PreExamBrief, RiskScore,
    SoapNote, FollowUpDraft, RoomStatusUpdate, Clinic, VetClinicAssignment,
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

app = FastAPI(title="General Scheduler API")

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
    log_agent_step(f"INTAKE AGENT: {len(saved)} owner photo(s) received and stored for appointment {timeblock_id}")
    return {"saved": len(saved), "images": saved}

@app.get("/api/timeblocks/{timeblock_id}/images")
def get_timeblock_images(timeblock_id: str):
    """Return all images (owner photos + future clinical) for an appointment."""
    return db.get_images_for_timeblock(timeblock_id)
