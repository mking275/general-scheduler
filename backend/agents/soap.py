"""
T005 + T030 — SoapDraftAgent
Generates structured SOAP note drafts.
Uses Gemini LLM when GEMINI_API_KEY is configured, otherwise falls back to
procedure templates (deterministic).
"""
import os
import json
import logging
from typing import Optional
from ..models import SoapNote, PreExamBrief, Patient
from ..model_config import GEMINI_FLASH

log = logging.getLogger(__name__)

# ── LLM Configuration ────────────────────────────────────────────────────────

_gemini_client = None
_LLM_AVAILABLE = False

def _get_gemini():
    """Lazy-init Gemini client. Returns (client, model_name) or (None, None)."""
    global _gemini_client, _LLM_AVAILABLE
    if _gemini_client is not None:
        return _gemini_client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        _gemini_client = False  # sentinel: tried and failed
        _LLM_AVAILABLE = False
        return False
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        _LLM_AVAILABLE = True
        log.info("SOAP Agent: Gemini LLM initialized successfully")
        return _gemini_client
    except Exception as e:
        log.warning(f"SOAP Agent: Gemini init failed ({e}), falling back to templates")
        _gemini_client = False
        _LLM_AVAILABLE = False
        return False

# ── Template Fallback (original T030 logic) ──────────────────────────────────

SOAP_TEMPLATES = {
    "Wellness Exam": {
        "plan": (
            "Continue current nutrition and exercise regimen. Administer core vaccines if due. "
            "Schedule heartworm/flea/tick preventatives. Recheck in 12 months."
        ),
        "objective": {
            "vitals": {"temperature_c": None, "heart_rate": None, "resp_rate": None, "weight_kg": None},
            "exam_findings": {
                "general": None, "skin_coat": None, "eyes_ears": None,
                "cardiovascular": None, "respiratory": None, "gastrointestinal": None,
            },
        },
    },
    "Vaccination": {
        "plan": (
            "Administer scheduled vaccines. Monitor for 15 minutes post-vaccination. "
            "Provide vaccine certificate. Schedule booster in 12 months."
        ),
        "objective": {
            "vitals": {"temperature_c": None, "heart_rate": None, "resp_rate": None, "weight_kg": None},
            "exam_findings": {"general": None, "vaccination_site": None, "lymph_nodes": None},
        },
    },
    "Surgery": {
        "plan": (
            "Pre-operative blood panel. IV catheter and anesthesia per protocol. "
            "Post-op pain management: meloxicam 0.1 mg/kg SID x 5 days. "
            "E-collar for 10 days. Suture removal at 10–14 days. Recheck in 7 days."
        ),
        "objective": {
            "vitals": {"temperature_c": None, "heart_rate": None, "resp_rate": None, "weight_kg": None},
            "exam_findings": {
                "general": None, "surgical_site": None, "lymph_nodes": None,
                "cardiovascular": None, "pre_op_assessment": None,
            },
        },
    },
    "Dental Cleaning": {
        "plan": (
            "Dental radiographs under anesthesia. Scale and polish all teeth. "
            "Extract grade 3+ mobility teeth as needed. Chlorhexidine rinse. "
            "Soft food 7 days post-procedure. Recheck at 6 months."
        ),
        "objective": {
            "vitals": {"temperature_c": None, "heart_rate": None, "resp_rate": None, "weight_kg": None},
            "exam_findings": {
                "general": None, "oral_exam": None, "periodontal_score": None,
                "tooth_resorption": None,
            },
        },
    },
    "Grooming": {
        "plan": (
            "Full bath, blow-dry, and brush-out. Nail trim and ear cleaning. "
            "Breed-standard trim as requested by owner. "
            "Recommend professional grooming every 6–8 weeks."
        ),
        "objective": {
            "vitals": {"weight_kg": None},
            "exam_findings": {
                "skin_coat_condition": None, "matting_level": None,
                "ear_condition": None, "nail_condition": None,
            },
        },
    },
}

_DEFAULT_TEMPLATE = {
    "plan": "Examination complete. Follow-up as clinically indicated.",
    "objective": {
        "vitals": {"temperature_c": None, "heart_rate": None, "resp_rate": None, "weight_kg": None},
        "exam_findings": {"general": None, "cardiovascular": None, "gastrointestinal": None},
    },
}


def _procedure_to_template_key(procedure: str) -> str:
    p = (procedure or "").lower()
    if "wellness" in p or "check" in p or "annual" in p or "avian" in p or "exotic" in p:
        return "Wellness Exam"
    if "vaccination" in p or "vaccine" in p:
        return "Vaccination"
    if "surgery" in p or "surgical" in p or "emergency" in p:
        return "Surgery"
    if "dental" in p or "teeth" in p:
        return "Dental Cleaning"
    if "grooming" in p or "groom" in p:
        return "Grooming"
    return "Wellness Exam"


# ── LLM Prompt ───────────────────────────────────────────────────────────────

SOAP_SYSTEM_PROMPT = """You are an expert veterinary SOAP note assistant. Generate a professional SOAP note draft for a veterinarian to review and edit.

RULES:
- Use standard veterinary medical terminology
- Be specific to the patient's species, breed, age, and presenting complaint
- Include breed-specific considerations where relevant
- Subjective: Summarize owner-reported history and chief complaint
- Objective: Provide exam finding field names appropriate for this visit type (leave values as null for the vet to fill in). Include appropriate vitals fields.
- Assessment: Provide a differential diagnosis list or clinical assessment based on the presentation
- Plan: Provide detailed, actionable treatment/follow-up plan with specific medications, doses, and recheck intervals

Return ONLY valid JSON with this structure:
{
  "subjective": "string - narrative of owner history and chief complaint",
  "objective": {
    "vitals": {"temperature_c": null, "heart_rate": null, "resp_rate": null, "weight_kg": <number or null>},
    "exam_findings": {"field_name": null, ...}
  },
  "assessment": "string - differential diagnoses and clinical reasoning",
  "plan": "string - detailed treatment plan"
}"""


def _build_llm_prompt(procedure: Optional[str], patient: Optional[Patient],
                       brief: Optional[PreExamBrief]) -> str:
    """Build the user prompt with all available clinical context."""
    parts = []

    if patient:
        parts.append(f"Patient: {patient.name}")
        parts.append(f"Species: {patient.species or 'Unknown'}")
        if patient.breed:
            parts.append(f"Breed: {patient.breed}")
        if patient.age:
            parts.append(f"Age: {patient.age}")
        if patient.sex:
            parts.append(f"Sex: {patient.sex}")
        if patient.weight_kg:
            parts.append(f"Weight: {patient.weight_kg} kg")
        if patient.flags:
            parts.append(f"Patient flags: {', '.join(patient.flags)}")

    if procedure:
        parts.append(f"\nScheduled procedure: {procedure}")

    if brief and brief.status == "received":
        if brief.chief_complaint:
            parts.append(f"\nChief complaint (from owner intake form): {brief.chief_complaint}")
        if brief.owner_verbatim:
            parts.append(f"Owner's words: \"{brief.owner_verbatim}\"")
        if brief.symptoms:
            sym_lines = []
            for s in brief.symptoms:
                sym_lines.append(f"  - {s['name']} (duration: {s.get('duration_days', '?')}d, severity: {s.get('severity', 'unknown')})")
            parts.append("Presenting symptoms:\n" + "\n".join(sym_lines))

    parts.append("\nGenerate a SOAP note draft for this visit.")
    return "\n".join(parts)


class SoapDraftAgent:
    """
    Generates a procedure-specific SOAP note draft.
    Uses Gemini LLM when available, falls back to deterministic templates.
    """

    def generate(
        self,
        timeblock_id: str,
        procedure: Optional[str],
        patient: Optional[Patient],
        brief: Optional[PreExamBrief],
    ) -> SoapNote:
        # Try LLM first
        client = _get_gemini()
        if client and client is not False:
            try:
                return self._generate_llm(client, timeblock_id, procedure, patient, brief)
            except Exception as e:
                log.warning(f"SOAP Agent: LLM generation failed ({e}), falling back to template")

        # Fallback to template
        return self._generate_template(timeblock_id, procedure, patient, brief)

    def _generate_llm(
        self,
        client,
        timeblock_id: str,
        procedure: Optional[str],
        patient: Optional[Patient],
        brief: Optional[PreExamBrief],
    ) -> SoapNote:
        """Generate SOAP note using Gemini LLM."""
        user_prompt = _build_llm_prompt(procedure, patient, brief)

        response = client.models.generate_content(
            model=GEMINI_FLASH,
            contents=[
                {"role": "user", "parts": [{"text": SOAP_SYSTEM_PROMPT + "\n\n" + user_prompt}]}
            ],
        )

        # Parse the JSON response
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        data = json.loads(text)

        # Merge weight from patient if available
        import copy
        objective = data.get("objective", {})
        if patient and patient.weight_kg:
            if "vitals" in objective:
                objective["vitals"]["weight_kg"] = patient.weight_kg

        log.info(f"SOAP Agent: LLM-generated note for {patient.name if patient else 'unknown'} ({procedure})")

        return SoapNote(
            timeblock_id=timeblock_id,
            subjective=data.get("subjective", ""),
            objective=objective,
            assessment=data.get("assessment", ""),
            plan=data.get("plan", ""),
            signed=False,
        )

    def _generate_template(
        self,
        timeblock_id: str,
        procedure: Optional[str],
        patient: Optional[Patient],
        brief: Optional[PreExamBrief],
    ) -> SoapNote:
        """Fallback: Generate SOAP note from procedure templates."""
        template_key = _procedure_to_template_key(procedure or "")
        template = SOAP_TEMPLATES.get(template_key, _DEFAULT_TEMPLATE)

        # Build subjective from intake brief
        if brief and brief.status == "received" and brief.chief_complaint:
            subjective_parts = [f"Owner reports: {brief.chief_complaint}."]
            if brief.owner_verbatim:
                subjective_parts.append(f'In owner\'s words: "{brief.owner_verbatim}"')
            if brief.symptoms:
                sym_str = ", ".join(
                    f"{s['name']} ({s.get('duration_days', '?')}d, {s.get('severity', 'mild')})"
                    for s in brief.symptoms
                )
                subjective_parts.append(f"Presenting symptoms: {sym_str}.")
            subjective = " ".join(subjective_parts)
        else:
            patient_name = patient.name if patient else "patient"
            subjective = (
                f"Owner presenting {patient_name} for {procedure or 'examination'}. "
                "Pre-visit intake not completed — subjective history to be obtained verbally at appointment."
            )

        # Set weight in objective if we have patient data
        import copy
        objective = copy.deepcopy(template["objective"])
        if patient and "weight_kg" in objective.get("vitals", {}):
            objective["vitals"]["weight_kg"] = patient.weight_kg

        return SoapNote(
            timeblock_id=timeblock_id,
            subjective=subjective,
            objective=objective,
            assessment="",
            plan=template["plan"],
            signed=False,
        )
