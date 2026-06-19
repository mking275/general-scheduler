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


# ---------------------------------------------------------------------------
# Phase 3 (vpma-v1.1) — Clinical Operations Models (T003)
# ---------------------------------------------------------------------------

class BreedProtocol(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    breed_pattern: str
    flag_type: str  # brachycephalic | oncology | cardiac | ortho | renal
    title: str
    detail: str
    age_threshold_years: float = 0.0
    severity: str = "info"  # info | warning | critical


class WaitlistEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str
    clinic_id: str
    procedure_type: str
    preferred_vet_id: Optional[str] = None
    urgency: str = "flexible"   # flexible | within_week | asap
    offer_status: str = "waiting"  # waiting | offered | accepted | expired
    join_date: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CareProtocol(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    species: str   # dog | cat | all
    protocol_name: str
    interval_months: int


class CareEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str
    protocol_id: str
    timeblock_id: Optional[str] = None
    administered_date: str   # ISO date
    next_due_date: str       # ISO date; computed = administered_date + interval_months
    batch_number: str = ""
    administered_by: str = ""


class Prescription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str
    timeblock_id: Optional[str] = None
    drug_name: str
    dose: str           # e.g. "25mg"
    frequency: str      # e.g. "BID"
    duration_days: int
    refills_remaining: int = 0
    supply_ends_at: str  # ISO date; issued_date + duration_days
    issued_by: str
    issued_date: str    # ISO date


class RefillRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    prescription_id: str
    initiated_by: str   # "vet" | "front_desk"
    status: str = "pending"  # pending | auto_approved | vet_review | approved | declined
    requested_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


class ForecastWeek(BaseModel):
    week_label: str
    booked_slots: int
    projected_slots: int
    capacity_slots: int
    utilisation_pct: float
    projected_revenue: float


class ForecastResult(BaseModel):
    clinic_id: str
    clinic_name: str
    trend: str  # on_track | action_needed | strong_growth
    forecast_weeks: List[ForecastWeek]
    insight: str
    verbose_log: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Integration Batch 0 — T005 Models
# ---------------------------------------------------------------------------

class IntegrationDefinition(BaseModel):
    id: str
    name: str
    module: str = "core"
    tier: str = "standard"
    required_keys: List[str] = Field(default_factory=list)
    test_endpoint: str = ""


class IntegrationCredentialSave(BaseModel):
    credentials: Dict[str, str]  # key_name → raw value (will be encrypted)


class IntegrationStatus(BaseModel):
    id: Optional[str] = None
    clinic_id: str
    integration_id: str
    status: str = "unconfigured"   # connected | degraded | disconnected | unconfigured
    latency_ms: int = 0
    error_message: str = ""
    last_checked_at: Optional[str] = None


class LabAnalyte(BaseModel):
    name: str
    value: float
    unit: str = ""
    low: float = 0.0     # B-02 fix: field names are low/high
    high: float = 0.0
    flag: str = ""       # H | L | HH | LL | ""


class LabPanel(BaseModel):
    name: str
    analytes: List[LabAnalyte] = Field(default_factory=list)


class LabResultPayload(BaseModel):
    """Normalised inbound lab result from any provider webhook."""
    lab_order_id: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    owner_name: Optional[str] = None
    panel_name: str = "Lab Panel"
    provider: str = "manual"
    panels: List[LabPanel] = Field(default_factory=list)
    received_at: Optional[str] = None


class MigrationRun(BaseModel):
    id: Optional[str] = None
    clinic_id: str
    source_system: str  # avimark | cornerstone | ezyvet
    status: str = "pending"
    phase: str = ""
    imported_owners: int = 0
    imported_patients: int = 0
    imported_visits: int = 0
    imported_vaccines: int = 0
    imported_rx: int = 0
    flagged_count: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: str = ""


class MigrationFlag(BaseModel):
    id: Optional[str] = None
    migration_run_id: str
    record_type: str
    source_row: Dict[str, Any] = Field(default_factory=dict)
    reason: str


class ImagingWebhookPayload(BaseModel):
    """Inbound imaging result from DICOM/PACS system."""
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    owner_name: Optional[str] = None
    modality: str = "xray"          # xray | ultrasound | ct | mri
    report_text: Optional[str] = None
    dicom_study_uid: Optional[str] = None
    imaging_system: Optional[str] = None
    study_date: Optional[str] = None
    image_url: Optional[str] = None
    provider: str = "clinical"


class LabAcknowledgeRequest(BaseModel):
    vet_id: str


class LabAssignRequest(BaseModel):
    patient_id: str
    timeblock_id: Optional[str] = None


class VetscanCSVRow(BaseModel):
    """Single row from a Vetscan/Abaxis CSV export."""
    test_name: str
    value: str
    unit: str = ""
    reference_range: str = ""
    flag: str = ""

