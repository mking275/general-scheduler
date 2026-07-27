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


# ===========================================================================
# Feature 010 — Vera Voice (VP-3): 8 voice entities + enums (data-model.md)
# All external paths run sim/dual-mode. Rows are tenant/party-scoped via
# clinic_id / party_id (app-level scoping standing in for RLS in the pilot).
# ===========================================================================

from typing import Literal as _Literal


class CallOutcome(str, Enum):
    """Descriptive outcome label — NOT the containment metric (F2)."""
    CONTAINED = "contained"
    BOOKED = "booked"          # booked is a contained outcome
    ESCALATED = "escalated"
    DEFLECTED = "deflected"


class VerificationState(str, Enum):
    UNVERIFIED = "unverified"
    SOFT_CONFIRMED = "soft_confirmed"


class GateDecision(str, Enum):
    """C4 autonomy-gate verbs. Only do|reject|escalate act on a live voice
    turn; advise/propose defer to post-call artifacts (B3 / D6a)."""
    ADVISE = "advise"
    PROPOSE = "propose"
    DO = "do"
    REJECT = "reject"
    ESCALATE = "escalate"


class EscalationTrigger(str, Enum):
    EXPLICIT_EMERGENCY = "explicit_emergency"
    PROTOCOL_KEYWORD = "protocol_keyword"
    LOW_CONFIDENCE = "low_confidence"      # < clinic_voice_config.low_confidence_threshold
    HUMAN_REQUEST = "human_request"
    SLO_BREACH = "slo_breach"              # > clinic_voice_config.slo_latency_ms


class TransferOutcome(str, Enum):
    ANSWERED = "answered"
    NO_ANSWER = "no_answer"
    FALLBACK_ER_DIRECTORY = "fallback_er_directory"
    VOICEMAIL_CALLBACK = "voicemail_callback"


class ModelProvider(str, Enum):
    GEMINI_LIVE = "gemini_live"
    OPENAI_REALTIME = "openai_realtime"


class TurnRole(str, Enum):
    CALLER = "caller"
    VERA = "vera"
    SYSTEM = "system"


# --- Table 1: call_session -------------------------------------------------
class CallSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    inbound_number: str                       # E.164
    party_id: Optional[str] = None            # NULL = unverified/ephemeral
    verification_state: VerificationState = VerificationState.UNVERIFIED
    channel_binding_id: Optional[str] = None
    started_at: Optional[str] = None
    answered_at: Optional[str] = None          # proves first-ring answer
    ended_at: Optional[str] = None
    call_outcome: Optional[CallOutcome] = None
    containment_flag: bool = False             # single source of containment metric
    model_provider: Optional[ModelProvider] = None
    degraded_mode: bool = False
    session_resume_count: int = 0
    cost_usd: Optional[float] = None
    consent_recorded_at: Optional[str] = None  # = time disclosure delivered
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 2: call_turn (append-only) --------------------------------------
class CallTurn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    call_session_id: str
    seq: int                                   # monotonic within call
    role: TurnRole
    text: str = ""
    is_final: bool = True
    started_at: Optional[str] = None
    latency_ms: Optional[int] = None
    barge_in: bool = False
    protocol_flag: Optional[str] = None
    gate_decision: Optional[GateDecision] = None
    tool_calls_json: Dict[str, Any] = Field(default_factory=dict)


# --- Table 3: call_transcript (append-only) --------------------------------
class CallTranscript(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    call_session_id: str
    full_text: str = ""
    audio_ref: Optional[str] = None
    consent_record: Dict[str, Any] = Field(default_factory=dict)   # disclosure text + ts
    vendor_no_training_attestation: Optional[str] = None
    retained_until: Optional[str] = None       # >= 6mo for protocol-flagged calls
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 4: escalation_event ---------------------------------------------
class EscalationEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    call_session_id: str
    trigger: EscalationTrigger
    protocol_state: Optional[str] = None
    triggered_at: Optional[str] = None
    transfer_target_id: Optional[str] = None
    whisper_summary: Optional[str] = None
    transfer_outcome: Optional[TransferOutcome] = None
    fallback_path: Optional[str] = None
    watchdog_fired: bool = False               # escalation forced by adapter watchdog
    resolved_at: Optional[str] = None
    audit_retained_until: Optional[str] = None


# --- Table 5: refill_request_draft -----------------------------------------
class RefillRequestDraft(BaseModel):
    """Never auto-approved; never touches prescriptions.py::request_refill.
    ``status`` admits ONLY ``draft_vet_review`` (Literal + DB CHECK)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    call_session_id: str
    party_id: str                              # verified caller only
    patient_ref: str
    drug_name_asserted: str
    status: _Literal["draft_vet_review"] = "draft_vet_review"
    refills_remaining_at_capture: Optional[int] = None   # recorded; does NOT gate approval
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 6: clinic_voice_config ------------------------------------------
class ClinicVoiceConfig(BaseModel):
    clinic_id: str
    after_hours_window: Dict[str, Any] = Field(default_factory=dict)
    disclosure_script: Dict[str, Any] = Field(default_factory=dict)
    triage_protocol_id: Optional[str] = None
    er_directory_ref: Optional[str] = None
    voice_params: Dict[str, Any] = Field(default_factory=dict)
    model_provider_pref: ModelProvider = ModelProvider.GEMINI_LIVE
    max_hold_ms: int = 8000
    filler_script: str = ""
    low_confidence_threshold: float = 0.6
    slo_latency_ms: int = 3000
    vendor_no_training_attestation: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 7: on_call_target -----------------------------------------------
class OnCallTarget(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    label: str
    phone: str                                 # E.164
    type: _Literal["on_call_vet", "er_partner", "overflow"] = "on_call_vet"
    priority: int = 0                          # transfer attempt order
    active_window: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 8: triage_protocol ----------------------------------------------
class TriageProtocol(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    version: str = "0.0.0"
    config_yaml: str = ""
    signed_by: Optional[str] = None            # licensed vet — gates live emergency
    signed_at: Optional[str] = None
    active: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    verbose_log: List[str] = Field(default_factory=list)


# ===========================================================================
# Feature 011 — Relationship Memory & Consent (VP-4a): 13 net-new entities +
# enums (data-model.md). Party-scoped tables key on ``party_id`` (M4). All
# ``entity_ref`` values are STABLE-ID keys ``{type}:{stable_id}`` — never names
# (research D2). Resolution / verification / reveal / consent-event / inbound
# tables are the append-only audit spine (Constitution I).
# ===========================================================================


class HouseholdRole(str, Enum):
    CO_OWNER = "co_owner"
    AUTHORIZED_CALLER = "authorized_caller"
    EMERGENCY_CONTACT = "emergency_contact"


class ResolutionOutcome(str, Enum):
    """Resolver return outcome (R1). Admits ONLY these three — a multi-match can
    never collapse to a single record. ``soft_confirmed`` is a downstream
    *event-log* state after neutral disambiguation, not a resolver outcome."""
    RESOLVED_SINGLE = "resolved_single"
    AMBIGUOUS_MULTI = "ambiguous_multi"
    UNMATCHED = "unmatched"


class SensitivityTier(str, Enum):
    LOW = "low"
    HIGH = "high"


class RevealDecision(str, Enum):
    REVEALED = "revealed"
    WITHHELD = "withheld"


class ConsentAction(str, Enum):
    OPT_OUT = "opt_out"
    OPT_IN = "opt_in"


class InboundAction(str, Enum):
    OPT_OUT_RECORDED = "opt_out_recorded"
    OPT_IN_RECORDED = "opt_in_recorded"
    ROUTED_TO_STAFF = "routed_to_staff"
    NONE = "none"


class StaffRole(str, Enum):
    """Source of the owner/manager/staff reveal audience (M5, FR-012)."""
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


# --- Table 1: household ----------------------------------------------------
class Household(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    entity_ref: str                                # synthesized household:vah_*
    display_name: str = ""                         # payload, never a key
    review_status: _Literal["confirmed", "proposed"] = "confirmed"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 2: household_contact (Party) ------------------------------------
class HouseholdContact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    household_id: str
    pims_client_id: Optional[str] = None           # ezyVet stable id
    entity_ref: str                                # client:ezyvet_c*
    display_name: str = ""                         # matching/greeting only
    household_role: HouseholdRole = HouseholdRole.CO_OWNER
    active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 3: contact_identifier -------------------------------------------
class ContactIdentifier(BaseModel):
    """The lookup index. A lookup returns ALL matching rows (candidate set),
    never LIMIT 1 — this table removes the single-phone-per-owner assumption
    the LIMIT 1 bug lived on."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    party_id: str
    clinic_id: str
    id_type: _Literal["phone", "email"]
    value_normalized: str                          # 10-digit phone / lowercased email
    value_raw: str = ""
    is_primary: bool = False
    source: _Literal["pims", "inbound"] = "pims"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 4: patient_household_link ---------------------------------------
class PatientHouseholdLink(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str
    household_id: str
    clinic_id: str
    pims_patient_id: Optional[str] = None
    entity_ref: str                                # patient:ezyvet_p*
    status: _Literal["active", "deceased", "rehomed"] = "active"
    display_name: str = ""                         # pet name — payload, for factor match
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 5: identity_resolution_event (append-only) ----------------------
class IdentityResolutionEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    channel: str = "voice"
    inbound_identifier_normalized: str
    identifier_type: _Literal["phone", "email", "name"]
    candidate_set_json: List[Dict[str, Any]] = Field(default_factory=list)  # FULL set
    match_count: int = 0
    # Stored value may also be "soft_confirmed" after neutral disambiguation;
    # the resolver itself only ever emits a ResolutionOutcome value.
    outcome: str = ResolutionOutcome.UNMATCHED.value
    confirmed_party_id: Optional[str] = None
    resolved_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 6: household_review_queue ---------------------------------------
class HouseholdReviewQueue(BaseModel):
    """Never-auto-merge staff queue for probable duplicates / collisions."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    proposal_type: _Literal["probable_duplicate", "collision", "merge_candidate"]
    subject_refs_json: List[Any] = Field(default_factory=list)
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    status: _Literal["pending", "approved", "rejected", "deferred"] = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 7: verification_challenge (append-only) -------------------------
class VerificationChallenge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    call_session_id: Optional[str] = None          # -> 010 call_session
    party_id: Optional[str] = None
    action_requested: _Literal["reschedule", "cancel", "contact_edit", "refill_request"]
    sensitivity_tier: SensitivityTier
    factors_required: int = 1
    factors_presented_json: List[Dict[str, Any]] = Field(default_factory=list)  # no raw secrets
    outcome: _Literal["passed", "failed", "deferred_staff_callback"]
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 8: memory_scoping_policy ----------------------------------------
class MemoryScopingPolicy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    version: str = "0.0.0"
    policy_yaml: str = ""                           # three-field shape (contract C, H1)
    signed_by: Optional[str] = None                 # VP-9 policy owner (unsigned in 4a)
    active: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 9: reveal_decision_log (append-only) ----------------------------
class RevealDecisionLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    interaction_ref: str = ""                        # call_session:* / thread:*
    audience: _Literal["owner", "manager", "staff", "client_verified", "caller_unverified"]
    fact_kind: str                                   # raw Thoth kind requested
    fact_class: Optional[str] = None                 # NULL when kind unmapped (H1)
    entity_ref: Optional[str] = None
    decision: RevealDecision
    rule_matched: Optional[str] = None
    reason: _Literal["explicit_allow", "default_deny_no_rule", "wrong_household",
                     "unmapped_kind", "unrecognized_predicate"]
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 10: contact_consent ---------------------------------------------
class ContactConsent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    party_id: str
    channel: _Literal["voice", "sms", "email", "portal"]
    ai_contact_allowed: bool = True                  # current state (default true)
    source: _Literal["inbound_stop", "staff", "portal"] = "staff"
    changed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    changed_by: str = "system"


# --- Table 11: consent_event (append-only) ---------------------------------
class ConsentEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    party_id: str
    clinic_id: str
    channel: _Literal["voice", "sms", "email", "portal"]
    action: ConsentAction
    keyword: Optional[str] = None                    # STOP / START / ...
    inbound_message_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Table 12: inbound_message (append-only) -------------------------------
class InboundMessage(BaseModel):
    """The net-new inbound intake path (sms_gateway.py is outbound-only)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    channel: _Literal["sms", "voice_dtmf", "voice", "portal"] = "sms"
    from_identifier_normalized: str
    body: str = ""
    matched_keyword: Optional[str] = None            # STOP | START | HELP | None
    action_taken: InboundAction = InboundAction.NONE
    received_at: str = Field(default_factory=lambda: datetime.now().isoformat())  # SC-006 clock start


# --- Table 13: clinic_staff_role -------------------------------------------
class ClinicStaffRole(BaseModel):
    """Per-user staff role — source of owner/manager/staff audience (M5)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    staff_user_id: str                               # -> staff:* entity_ref
    role: StaffRole
    active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ===========================================================================
# Feature 009 — Vera Envelope Onboarding (VP-1): net-new onboarding-control
# entities + net-new canonical financial/AR/ledger/payment + inventory
# entities + enums (data-model.md — the T002 entity source of truth).
#
# Practice-scoped tables key on practice_id (+ clinic_id tenant scope);
# Delivery / BatchRollup are group-scoped. Every canonical record carries a
# NON-NULLABLE entity_ref (seeded via backend/relationship/entity_ref.py) +
# source_id lineage. NO net-new ReviewItem model is defined — the spec's
# "ReviewItem" Key Entity IS the reused HouseholdReviewQueue (011 T012, above);
# 009 writes to it via relationship/review_queue.py verbatim (finding F7).
# ===========================================================================

class PracticeState(str, Enum):
    """The per-practice pipeline state. The linear happy path is
    received -> profiled -> normalized -> verified -> reconciled ->
    identity_bootstrapped -> shadow_ready; blocked/partial/held/delta are
    FIRST-CLASS off-path states (a practice may sit at any without stalling
    the batch and never auto-advances to shadow_ready)."""
    RECEIVED = "received"
    PROFILED = "profiled"
    NORMALIZED = "normalized"
    VERIFIED = "verified"
    RECONCILED = "reconciled"
    IDENTITY_BOOTSTRAPPED = "identity_bootstrapped"
    SHADOW_READY = "shadow_ready"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    HELD = "held"
    DELTA = "delta"


class ScopeCategory(str, Enum):
    """The §5 letter's enumerated data-copy categories (config/envelope/
    section5_scope.yaml is the source of truth)."""
    PATIENT_CLIENT = "patient_client"
    SCHEDULING = "scheduling"
    INVOICING_BILLING_PAYMENTS = "invoicing_billing_payments"
    COMMUNICATIONS = "communications"
    ATTACHMENTS_IMAGING = "attachments_imaging"
    CONFIGURATION = "configuration"


class VarianceDisposition(str, Enum):
    EXPLAINED = "explained"
    BLOCKING = "blocking"


class ReadinessCriterion(str, Enum):
    """The six criteria that ALL must be met for shadow_ready (FR-022)."""
    COUNSEL_CLEARED = "counsel_cleared"
    FORMAT_DISCOVERED = "format_discovered"
    NORMALIZATION_IDEMPOTENT = "normalization_idempotent"
    COMPLETENESS_QUALITY_ABOVE_FLOOR = "completeness_quality_above_floor"
    RECONCILIATION_ACKNOWLEDGED = "reconciliation_acknowledged"
    IDENTITY_CORPUS_PRODUCED = "identity_corpus_produced"


# --------------------------------------------------------------------------- #
#  Onboarding-control tables
# --------------------------------------------------------------------------- #

# --- Delivery — chain-of-custody anchor (group-scoped; append-only) --------
class Delivery(BaseModel):
    """One received export bundle. The §6.3 backup-compliance artifact."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    source: str                                      # secure-transfer origin
    delivery_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    byte_count: int = 0
    checksum: str = ""                               # sha256 of the bundle
    practice_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- PracticeDatabase — one practice's export within a delivery -------------
class PracticeDatabase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    delivery_id: str
    receipt_state: _Literal["received", "superseded"] = "received"
    state: PracticeState = PracticeState.RECEIVED
    vault_object_ref: Optional[str] = None
    checksum: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- ChainOfCustody (append-only) ------------------------------------------
class ChainOfCustody(BaseModel):
    """Proof of 'captured before touched' — parsed MUST be false at write."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    practice_database_id: str
    source: str
    delivery_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    byte_count: int = 0
    checksum: str = ""
    vault_written_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    parsed: bool = False                             # must be false at write time
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- CounselSignoff (append-only) — the hard pre-normalization gate row -----
class CounselSignoff(BaseModel):
    """Its PRESENCE is the guard received -> profiled/normalized checks
    (FR-004, §3.2(h)). No engineering bypass by design."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    signed_by: str
    signed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    structure_version: str = "v1"
    scope: str = ""                                  # the clinic-owned-data structure signed
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- ScopeCheck — scope-vs-request against §5 categories --------------------
class ScopeCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    practice_database_id: str
    # scope_category value -> "present" | "absent" | "short"
    dispositions: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- FormatProfile — machine-readable discovery result ---------------------
class FormatProfile(BaseModel):
    """Normalization is BLOCKED without this row (FR-005/006)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    practice_database_id: str
    entities: Dict[str, int] = Field(default_factory=dict)     # entity name -> record_count
    encodings: Dict[str, str] = Field(default_factory=dict)    # entity -> encoding
    referential_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    export_variant: str = ""                          # the identified ezyVet variant
    unmapped_flags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- StateTransition (append-only) — the single write path -----------------
class StateTransition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    from_state: Optional[str] = None                 # None for the initial receipt row
    to_state: PracticeState
    reason: str = ""
    at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- CompletenessResult ----------------------------------------------------
class CompletenessResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    # scope_category value -> {"present": bool, "ingested": int, "profiled": int, "short": bool}
    category_coverage: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    referential_integrity_findings: List[Dict[str, Any]] = Field(default_factory=list)
    # financial block (FR-013)
    ar_balance_total: float = 0.0
    invoice_count: int = 0
    payment_total: float = 0.0
    missing_or_short: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- QualityAssessment -----------------------------------------------------
class QualityAssessment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    shared_phones: int = 0
    duplicate_owners: int = 0
    deceased_pets: int = 0
    orphaned_refs: int = 0
    malformed: int = 0
    usable_record_share: float = 1.0
    below_floor: bool = False                         # > 0.20 unusable -> true
    itemized_gap: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- FinancialVariance — a reconciliation variance line --------------------
class FinancialVariance(BaseModel):
    amount: float = 0.0                               # ingested - reported
    disposition: VarianceDisposition = VarianceDisposition.EXPLAINED
    attributed_cause: Optional[str] = None


# --- ReconciliationReport (append-only; owner-facing) ----------------------
class ReconciliationReport(BaseModel):
    """Zero AR tolerance: any unexplained ar_variance -> blocking. Owner/
    manager audience only (FR-016/017/018)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    # scope_category value -> {"requested": int, "delivered": int, "ingested": int}
    category_counts: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    ar_variance: Optional[FinancialVariance] = None
    invoice_variance: Optional[FinancialVariance] = None
    payment_variance: Optional[FinancialVariance] = None
    outstanding_gap: List[str] = Field(default_factory=list)   # scope_category values
    blocking: bool = False                            # any blocking financial variance
    owner_acknowledged: bool = False                  # group-level ack
    audience: _Literal["owner", "manager"] = "owner"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- IdentityAuditCorpus (append-only) — the 009-defined 011 seam ----------
class IdentityAuditCorpus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    proposals: List[Dict[str, Any]] = Field(default_factory=list)   # each w/ entity_ref lineage
    collisions: List[Dict[str, Any]] = Field(default_factory=list)
    answer_key_scored_precision: Dict[str, Any] = Field(default_factory=dict)  # single vs multi-match
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- GapNotice (append-only; owner-facing) ---------------------------------
class GapNotice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    missing_categories: List[str] = Field(default_factory=list)     # scope_category values
    text: str = ""                                    # paper-trail-ready vendor-reply text
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- PracticeReadiness ------------------------------------------------------
class PracticeReadiness(BaseModel):
    """shadow_ready true ONLY when all six criteria met (FR-022/023/028)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    # readiness_criterion value -> satisfied bool
    criteria: Dict[str, bool] = Field(default_factory=dict)
    shadow_ready: bool = False
    invisible_adoption_asserted: bool = False          # no staff artifact emitted
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- BatchRollup (group-scoped; computed view) -----------------------------
class BatchRollup(BaseModel):
    """Group-level view over the per-practice rows; a blocked practice is
    visible but never stalls the batch (FR-024)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    delivery_id: Optional[str] = None
    # practice_id -> {"state": str, "shadow_ready": bool, ...}
    per_practice: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --------------------------------------------------------------------------- #
#  Net-new canonical practice-model entities (financial/AR/ledger/payment +
#  inventory). Every row carries a NON-NULLABLE entity_ref + source_id lineage
#  (FR-008/009). The clinical/scheduling canonical entities already exist on
#  the platform practice model; 009 hydrates them.
# --------------------------------------------------------------------------- #

class CanonicalRecord(BaseModel):
    """The generic canonical-entity envelope an adapter emits from normalize()
    — a uniform shape (category + payload) the normalizer (T018) persists. Every
    record carries lineage back to a specific source export row."""
    practice_id: str
    category: str                                    # provider|client|household|patient|
    #                                                  appointment|invoice|ledger|payment|
    #                                                  ar_balance|inventory|communication|
    #                                                  attachment|product_service
    entity_ref: str                                  # NON-NULLABLE lineage key
    source_id: str                                   # NON-NULLABLE source-row key
    payload: Dict[str, Any] = Field(default_factory=dict)
    unmapped_fields: Dict[str, Any] = Field(default_factory=dict)


class LedgerEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    entity_ref: str                                  # NON-NULLABLE
    source_id: str
    account_ref: str = ""
    amount: float = 0.0
    entry_type: str = ""                             # invoice | adjustment | credit
    posted_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class InvoiceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    entity_ref: str                                  # NON-NULLABLE
    source_id: str
    client_ref: str = ""
    total: float = 0.0
    status: str = ""
    issued_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class PaymentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    entity_ref: str                                  # NON-NULLABLE
    source_id: str
    client_ref: str = ""
    amount: float = 0.0
    method: str = ""
    received_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ARBalance(BaseModel):
    """Open client balances — the zero-tolerance reconciliation target."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    entity_ref: str                                  # NON-NULLABLE
    source_id: str
    client_ref: str = ""
    balance: float = 0.0
    as_of: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class InventoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    entity_ref: str                                  # NON-NULLABLE
    source_id: str
    product_ref: str = ""
    qty_on_hand: float = 0.0
    unit: str = ""
    last_counted_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class UnmappedFieldSidecar(BaseModel):
    """Preserves source fields with no canonical mapping — never silently
    dropped (FR-008 US3-scenario-3; T020)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    practice_id: str
    entity_ref: str                                  # owning canonical record
    source_field: str = ""
    raw_value: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
