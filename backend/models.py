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


# ---------------------------------------------------------------------------
# spec-007 — Platform Account & Subscription Models
# ---------------------------------------------------------------------------

class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    contact_name: str
    contact_email: str
    contact_phone: str = ""
    address: str = ""
    plan_tier: str = "starter"       # starter | professional | enterprise
    status: str = "trial"            # trial | active | past_due | suspended | cancelled
    trial_ends_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""


class ModuleLicense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    module_id: str                   # MOD-FIN | MOD-COM | etc.
    status: str = "active"           # active | suspended | cancelled
    billing_interval: str = "monthly"
    price_cents: int = 0
    purchased_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    stripe_subscription_item_id: str = ""


class AccountInvoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    invoice_number: str
    period_start: str
    period_end: str
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    subtotal_cents: int = 0
    total_cents: int = 0
    status: str = "pending"          # pending | paid | failed | void
    stripe_invoice_id: str = ""
    paid_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AccountUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    name: str
    email: str
    role: str = "admin"              # admin | member
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AccountUpdateRequest(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


class ModuleSubscribeRequest(BaseModel):
    billing_interval: str = "monthly"  # monthly | annual  (W-05 fix: default makes body fully optional)


class PlanUpgradeRequest(BaseModel):
    plan_tier: str   # starter | professional | enterprise


# ---------------------------------------------------------------------------
# S07 — Online Booking Portal Models
# ---------------------------------------------------------------------------

class BookableAppointmentType(BaseModel):
    id: str                                    # e.g. "wellness", "sick", "vaccines"
    name: str                                  # Display name: "Annual Wellness Exam"
    slug: str = ""                             # URL-safe slug
    duration_minutes: int = 30                 # Default duration for this type
    intake_question_set: str = "wellness"      # Key into INTAKE_QUESTION_SETS dict
    description: str = ""                      # Optional client-facing description
    enabled: bool = True                       # Whether online booking is active for this type
    breed_duration_overrides: dict = {}        # e.g. {"Persian": 60, "Maine Coon": 60}


class ClinicBookingConfig(BaseModel):
    """Full booking config for a clinic. Used for GET /api/.../booking-config response."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    online_booking_enabled: bool = False
    same_day_booking_enabled: bool = False
    waitlist_enabled: bool = True
    auto_confirm: bool = True
    require_deposit: bool = False              # Phase 3 / MOD-FIN
    deposit_amount_cents: int = 0
    advance_booking_days: int = 60
    same_day_cutoff_hour: int = 14             # 0-23; local to clinic timezone
    min_booking_notice_hours: int = 2
    buffer_minutes: int = 10
    show_vet_names: bool = True
    show_vet_photos: bool = False
    bookable_appointment_types: List[BookableAppointmentType] = Field(default_factory=list)
    booking_confirmation_msg: str = ""
    cancellation_policy: str = "Cancellations within 24 hours may incur a fee."
    intake_sms_template: str = ""
    hidden_resource_ids: List[str] = Field(default_factory=list)
    emergency_phone: str = ""
    emergency_message: str = ""
    brand_color_primary: str = "#6C63FF"
    brand_color_accent: str = "#F0A500"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ClinicBookingConfigUpdate(BaseModel):
    """Request body for PUT /api/clinics/{clinic_id}/booking-config."""
    online_booking_enabled: Optional[bool] = None
    same_day_booking_enabled: Optional[bool] = None
    waitlist_enabled: Optional[bool] = None
    auto_confirm: Optional[bool] = None
    advance_booking_days: Optional[int] = None  # 7-90 range enforced in route handler
    same_day_cutoff_hour: Optional[int] = None  # 0-23
    min_booking_notice_hours: Optional[int] = None
    buffer_minutes: Optional[int] = None        # 0-60
    show_vet_names: Optional[bool] = None
    bookable_appointment_types: Optional[List[BookableAppointmentType]] = None
    booking_confirmation_msg: Optional[str] = None
    cancellation_policy: Optional[str] = None
    hidden_resource_ids: Optional[List[str]] = None
    emergency_phone: Optional[str] = None
    emergency_message: Optional[str] = None
    brand_color_primary: Optional[str] = None   # Must be valid hex: #RRGGBB
    brand_color_accent: Optional[str] = None


class OwnerLookupRequest(BaseModel):
    clinic_id: str
    phone: Optional[str] = None                # 10-digit US number (formatting stripped)
    email: Optional[str] = None                # at least one of phone/email required


class PetSummary(BaseModel):
    """Minimal pet info returned at lookup time. No medical history."""
    id: str
    name: str
    species: str
    breed: str
    age_years: Optional[float] = None          # Calculated from dob; null if dob unknown
    last_visit_label: Optional[str] = None     # e.g. "14 months ago"; null if never visited
    care_due: bool = False                     # Phase 2: populated from care_protocols
    care_due_reason: Optional[str] = None


class OwnerLookupResponse(BaseModel):
    found: bool
    owner_id: Optional[str] = None
    display_name: Optional[str] = None         # First name only; never full name at lookup
    pets: List[PetSummary] = Field(default_factory=list)


class NewPetRequest(BaseModel):
    name: str                                  # 1-100 chars
    species: str                               # dog|cat|bird|rabbit|reptile|other
    breed: str = ""                            # Optional; empty string allowed
    dob_approx: Optional[str] = None           # ISO date YYYY-MM-DD; past dates only
    sex: Optional[str] = None                  # male|female|unknown
    neutered: Optional[bool] = None


class OwnerRegisterRequest(BaseModel):
    clinic_id: str
    first_name: str                            # 1-100 chars
    last_name: str                             # 1-100 chars
    phone: str                                 # 10-digit US number; required
    email: str                                 # Valid email; required
    sms_consent: bool = False
    pet: NewPetRequest


class SlotAvailabilityItem(BaseModel):
    """A single available appointment slot returned by GET /public/clinics/.../availability."""
    slot_id: str                               # Deterministic UUID5 from (resource_id, start_datetime)
    resource_id: str                           # Vet resource UUID
    vet_name: str                              # e.g. "Dr. Emily Chen"; masked if show_vet_names=False
    vet_display_name: str                      # Shorter form: "Dr. Chen"
    start_datetime: str                        # ISO datetime in clinic's local timezone
    end_datetime: str
    duration_minutes: int
    rank: int                                  # 1=first; Phase 1 is chronological only
    rank_label: str                            # "Soonest Available"; Phase 2: "Best Match"
    rank_explanation: str                      # Human-readable rationale; Phase 2: AI-generated
    no_show_risk_label: Optional[str] = None   # Phase 2: "Low" | "Medium" | "High"


class BookingHoldRequest(BaseModel):
    clinic_id: str
    resource_id: str
    start_datetime: str                        # ISO datetime
    end_datetime: str                          # ISO datetime
    appointment_type_id: str
    patient_id: str


class BookingHoldResponse(BaseModel):
    hold_id: str
    slot_id: str
    expires_at: str                            # ISO datetime; 10 minutes from now
    resource_id: str
    vet_name: str
    start_datetime: str
    end_datetime: str


class BookingConfirmRequest(BaseModel):
    hold_id: str
    patient_id: str
    appointment_type_id: str
    urgency: str = "routine"                   # wellness|routine|urgent|emergency
    notes: Optional[str] = None               # Max 300 chars
    sms_consent: bool = False
    cancellation_policy_accepted: bool         # Must be True


class BookingConfirmResponse(BaseModel):
    booking_id: str
    booking_token: str
    status: str                                # "booked"
    status_url: str
    intake_url: str
    appointment: dict                          # {date, time, duration_minutes, vet_name, clinic_name, address}


class LifecycleStep(BaseModel):
    state: str
    label: str
    completed: bool
    completed_at: Optional[str] = None


class BookingStatusResponse(BaseModel):
    """Response for GET /public/status/{booking_token}."""
    booking_id: str
    booking_token: str
    status: str                                # booking_tokens.status
    clinic_name: str
    clinic_phone: str
    clinic_address: str
    pet_name: str
    owner_display_name: str
    appointment_type: str
    vet_name: str
    start_datetime: str
    duration_minutes: int
    lifecycle: List[LifecycleStep]
    intake_token: Optional[str] = None
    intake_status: Optional[str] = None
    intake_url: Optional[str] = None
    cancellable: bool
    reschedulable: bool = False                # Phase 2
    calendar_url: str


class IntakeAnswer(BaseModel):
    question_id: str
    answer: Optional[str] = None              # None only if skipped=True
    skipped: bool = False


class IntakeSubmitRequest(BaseModel):
    answers: List[IntakeAnswer]
    submitted_at: str                          # ISO datetime from client


class WaitlistJoinRequest(BaseModel):
    clinic_id: str
    patient_id: str
    owner_id: str
    appointment_type_id: str
    urgency: str = "routine"                   # wellness|routine|urgent
    time_preferences: List[str] = Field(default_factory=list)
    min_notice_hours: int = 3                  # 1 | 3 | 24
    phone: str
    sms_consent: bool = False


# ---------------------------------------------------------------------------
# Feature 008 — Vera Onboarding Models
# ---------------------------------------------------------------------------

# Vera Constitution: professional boundaries fragment.
# MUST be included in the docstring/system prompt of every onboarding agent.
VERA_PROFESSIONAL_BOUNDARIES = """
I am your Chief of Staff — not a veterinarian, not your attorney.
Clinical decisions remain with your licensed DVMs.
Regulatory compliance determinations belong to you or your qualified legal counsel.
I can brief, organize, surface, and schedule — I do not diagnose or prescribe.
""".strip()

# Role-appropriate first-action targets post-Replace
ONBOARDING_FIRST_ACTION_TARGETS = {
    "owner": [
        "Share your booking link with clients",
        "Set your availability",
        "Configure online booking",
    ],
    "manager": [
        "Invite the vets to their accounts",
        "Set room schedules",
        "Configure notifications",
    ],
    "associate": [
        "Book a test appointment to see how it feels",
        "Review your schedule",
        "Set your availability",
    ],
    "proxy": [
        "Send the practice owner a link to review and activate",
        "Preview the booking portal",
    ],
}


class OnboardingPersonaRole(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    ASSOCIATE = "associate"
    PROXY = "proxy"


class OnboardingPhase(int, Enum):
    WELCOME = 0
    DEMO = 1
    PIVOT = 2
    OPEN_PROMPT = 3
    DOCUMENT = 4
    REPLACE = 5
    LIVE = 6


class OnboardingSessionCreate(BaseModel):
    device_fingerprint: Optional[str] = None


class OnboardingSessionResponse(BaseModel):
    session_id: str
    session_token: str
    phase: int = 0
    persona_role: Optional[str] = None
    practice_name: Optional[str] = None
    track: str = "greenfield"
    state_json: Dict[str, Any] = Field(default_factory=dict)
    email_anchor: Optional[str] = None
    created_at: str
    updated_at: str
    verbose_log: List[str] = Field(default_factory=list)


class OnboardingSessionPatch(BaseModel):
    phase: Optional[int] = None
    persona_role: Optional[str] = None
    practice_name: Optional[str] = None
    track: Optional[str] = None
    state_json: Optional[Dict[str, Any]] = None


class MagicLinkCreate(BaseModel):
    session_id: str
    email: str


class MagicLinkResponse(BaseModel):
    sent: bool
    email: str
    expires_at: str
    magic_token: str  # raw token — demo: returned in response + console
    verbose_log: List[str] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    document_id: str
    mime_type: str
    file_size_bytes: int
    classified_type: Optional[str] = None
    streaming_status: str
    verbose_log: List[str] = Field(default_factory=list)


class EntityConfirmRequest(BaseModel):
    confirmed: bool = True
    correction: Optional[Dict[str, str]] = None  # {field_name, correct_value}


class EntityConfirmResponse(BaseModel):
    entity_id: str
    confirmed: bool
    corrected: bool
    verbose_log: List[str] = Field(default_factory=list)


class LogoScrapeRequest(BaseModel):
    session_id: str
    url: str


class LogoScrapeResponse(BaseModel):
    logo_asset_id: str
    source_type: str
    image_url: Optional[str] = None
    fallback_type: str  # image | monogram
    initials: Optional[str] = None
    verbose_log: List[str] = Field(default_factory=list)


class LogoConfirmRequest(BaseModel):
    action: str  # confirm | try_next | upload
    uploaded_file_path: Optional[str] = None


class LogoConfirmResponse(BaseModel):
    logo_asset_id: str
    confirmed: bool
    source_type: str
    verbose_log: List[str] = Field(default_factory=list)


class GoLiveRequest(BaseModel):
    session_id: str


class GoLiveResponse(BaseModel):
    clinic_id: str
    practice_name: str
    first_action_targets: List[str]
    boundary_statement: str
    verbose_log: List[str] = Field(default_factory=list)


class ActivationRequest(BaseModel):
    session_id: str
    booking_id: str


class ActivationResponse(BaseModel):
    activated_at: str
    session_id: str
    verbose_log: List[str] = Field(default_factory=list)
