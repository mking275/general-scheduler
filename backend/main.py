from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .repository import db
from .models import ResourceType
from .agents.intake import IntakeAgent
from .agents.matcher import SemanticMatcher
from .solver import HeuristicSolver
from .agents.dispatch import DispatchAgent
from fastapi.middleware.cors import CORSMiddleware
import uuid as _uuid

app = FastAPI(title="General Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unique ID for this server process — changes on every restart
SESSION_ID = str(_uuid.uuid4())

@app.get("/api/session")
def get_session():
    return {"session_id": SESSION_ID}

@app.get("/api/resources")
def get_resources():
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

class ScheduleRequest(BaseModel):
    request_id: str
    text: str

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
                logs.append(f"SOLVE: {top_vet.name} + {top_room.name} available. Constraints passed.")
                break
            except ValueError as e:
                logs.append(f"SOLVE: {vet.name} unavailable — {e}. Trying next vet...")
                last_error = str(e)

        if tb is None or top_vet is None:
            raise ValueError(last_error)

        db.save_timeblock(tb)
        logs.append("DISPATCH: Confirmed and saved to Repository.")
        dispatch = DispatchAgent()
        return dispatch.format_response(tb, job, [top_vet, top_room], logs)
        
    except ValueError as e:
        logs.append(f"SOLVE ERROR: {str(e)}")
        raise HTTPException(status_code=400, detail={"error": str(e), "logs": logs})
