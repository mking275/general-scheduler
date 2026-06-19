from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from uuid import UUID, uuid4
from enum import Enum

class ResourceType(str, Enum):
    VET = "Vet"
    ROOM = "Room"
    EQUIPMENT = "Equipment"

class TimeRange(BaseModel):
    start_time: datetime
    end_time: datetime

class Job(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    required_skills: List[str]
    estimated_duration: int # minutes
    patient_name: Optional[str] = None
    procedure: Optional[str] = None
    soft_requirements: Optional[str] = None
    scheduled_date: Optional[date] = None   # parsed target date (None = today)
    scheduled_time: Optional[time] = None   # parsed target time (None = next free slot)

class Resource(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: ResourceType
    name: str
    hard_skills: List[str]
    attributes: str
    availability_windows: List[TimeRange]

class TimeBlock(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    resource_ids: List[UUID]
    start_time: datetime
    end_time: datetime
    # Phase 2 extensions
    patient_id: Optional[str] = None
    intake_status: str = "not_started"   # not_started / pending / received
    followup_status: str = "not_started" # not_started / draft / sent
    risk_level: Optional[str] = None     # low / medium / high
    status: str = "scheduled"            # scheduled / complete
    # Phase 3 (F007) extensions
    clinic_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 2 — New Entities
# ---------------------------------------------------------------------------

class OwnerSummary(BaseModel):
    id: str
    name: str
    phone: str

class Patient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    species: str  # dog / cat / bird / exotic
    breed: str
    dob: str      # ISO date string
    weight_kg: float
    flags: List[str] = Field(default_factory=list)  # alert / chronic / first_visit
    flag_notes: str = ""
    owner_id: str
    visit_count: int = 0
    last_visit_date: Optional[str] = None
    last_visit_procedure: Optional[str] = None
    # Phase 3 (F007) extension
    home_clinic_id: Optional[str] = None

class PatientWithOwner(Patient):
    owner: Optional[OwnerSummary] = None

class Owner(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    phone: str
    email: str
    patient_ids: List[str] = Field(default_factory=list)

class SymptomItem(BaseModel):
    name: str
    duration_days: int
    severity: str  # low / mild / high

class PreExamBrief(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timeblock_id: str
    chief_complaint: str = ""
    symptoms: List[Dict[str, Any]] = Field(default_factory=list)
    owner_verbatim: str = ""
    suggested_focus: List[str] = Field(default_factory=list)
    status: str = "not_started"  # not_started / pending / received
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class RiskScore(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timeblock_id: str
    risk_level: str   # low / medium / high
    score: int        # 0-100
    factors: List[str] = Field(default_factory=list)
    calculated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class SoapNote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timeblock_id: str
    subjective: str = ""
    objective: Dict[str, Any] = Field(default_factory=dict)
    assessment: str = ""
    plan: str = ""
    signed: bool = False
    signed_at: Optional[str] = None
    signed_by: Optional[str] = None

class FollowUpDraft(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timeblock_id: str
    subject: str = ""
    body: str = ""
    tone: str = "wellness"   # wellness / surgery / emergency
    status: str = "draft"    # not_started / draft / approved / sent
    generated_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_at: Optional[str] = None

class RoomStatusUpdate(BaseModel):
    status: str  # available / prep / occupied / cleaning
    timeblock_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 3 (F007) — Multi-Clinic Models
# ---------------------------------------------------------------------------

class Clinic(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    address: str = ""
    phone: str = ""
    email: str = ""
    timezone: str = "America/Los_Angeles"
    color_hex: str = "#6C63FF"
    is_active: bool = True


class VetClinicAssignment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    vet_id: str
    clinic_id: str
    schedule_days: List[str] = Field(default_factory=list)
    is_primary: bool = False
