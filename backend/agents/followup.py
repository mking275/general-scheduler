"""
T005 + T026 — FollowUpDraftAgent
Generates post-appointment follow-up email drafts.
Uses Gemini LLM when GEMINI_API_KEY is configured, otherwise falls back to
tone templates (deterministic).
"""
import os
import json
import logging
from typing import Optional
from ..models import FollowUpDraft, TimeBlock, Patient, Owner

log = logging.getLogger(__name__)

# ── LLM Configuration ────────────────────────────────────────────────────────

_gemini_client = None
_LLM_AVAILABLE = False

def _get_gemini():
    """Lazy-init Gemini client. Returns client or False."""
    global _gemini_client, _LLM_AVAILABLE
    if _gemini_client is not None:
        return _gemini_client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        _gemini_client = False
        _LLM_AVAILABLE = False
        return False
    try:
        from google import genai
            from model_config import GEMINI_FLASH
        _gemini_client = genai.Client(api_key=api_key)
        _LLM_AVAILABLE = True
        log.info("FollowUp Agent: Gemini LLM initialized successfully")
        return _gemini_client
    except Exception as e:
        log.warning(f"FollowUp Agent: Gemini init failed ({e}), falling back to templates")
        _gemini_client = False
        _LLM_AVAILABLE = False
        return False


# ── Template Fallback (original T026 logic) ──────────────────────────────────

TEMPLATES = {
    "wellness": {
        "subject": "{patient_name}'s Wellness Visit Summary — {vet_name}",
        "body": (
            "Hi {owner_name},\n\n"
            "Thank you for bringing {patient_name} in today! It was wonderful to see them.\n\n"
            "Today's visit covered: {procedure}. Everything looked great overall, and we've updated "
            "{patient_name}'s records accordingly.\n\n"
            "Recommended follow-up: {recheck_interval}.\n\n"
            "If you have any questions or notice any changes in {patient_name}'s health, please don't "
            "hesitate to call us. We're always happy to help!\n\n"
            "Warm regards,\n{vet_name}\nVet Clinic"
        ),
    },
    "surgery": {
        "subject": "{patient_name}'s Post-Surgery Care Instructions — {vet_name}",
        "body": (
            "Hi {owner_name},\n\n"
            "Thank you for entrusting us with {patient_name}'s care today. The procedure ({procedure}) "
            "went well, and {patient_name} is recovering as expected.\n\n"
            "POST-OPERATIVE CARE INSTRUCTIONS:\n"
            "• Keep the surgical site clean and dry\n"
            "• Use the e-collar at all times until the recheck appointment\n"
            "• Restrict activity — no jumping or running for 10–14 days\n"
            "• Administer all prescribed medications as directed\n"
            "• Monitor for swelling, discharge, or excessive licking\n\n"
            "Please schedule a recheck: {recheck_interval}.\n\n"
            "Contact us immediately if you notice any concerns.\n\n"
            "Best,\n{vet_name}\nVet Clinic"
        ),
    },
    "emergency": {
        "subject": "IMPORTANT: {patient_name}'s Emergency Visit Follow-Up — {vet_name}",
        "body": (
            "Hi {owner_name},\n\n"
            "We wanted to follow up on {patient_name}'s emergency visit today. Our team worked hard "
            "to stabilize and evaluate {patient_name}, and we appreciate your trust in us during a "
            "stressful time.\n\n"
            "Procedure performed: {procedure}.\n\n"
            "CRITICAL FOLLOW-UP STEPS:\n"
            "• Monitor {patient_name} closely over the next 24–48 hours\n"
            "• Administer medications exactly as prescribed\n"
            "• Bring {patient_name} back immediately if symptoms worsen\n"
            "• Scheduled recheck: {recheck_interval}\n\n"
            "Do not hesitate to call our emergency line if you have any concerns.\n\n"
            "With care,\n{vet_name}\nVet Clinic"
        ),
    },
}

RECHECK_INTERVALS = {
    "wellness": "12 months (annual wellness exam)",
    "surgery": "10–14 days (suture removal and wound check)",
    "emergency": "48–72 hours (urgent recheck)",
}


def _tone_for_procedure(procedure: Optional[str]) -> str:
    p = (procedure or "").lower()
    if "emergency" in p:
        return "emergency"
    if any(w in p for w in ["surgery", "surgical", "dental", "operation"]):
        return "surgery"
    return "wellness"


# ── LLM Prompt ───────────────────────────────────────────────────────────────

FOLLOWUP_SYSTEM_PROMPT = """You are a veterinary follow-up email writer. Generate a warm, professional post-visit follow-up email from a veterinarian to a pet owner.

RULES:
- Match the tone to the visit type (wellness = warm/friendly, surgery = caring/instructive, emergency = urgent/reassuring)
- Include specific care instructions relevant to the procedure performed
- Reference the patient by name throughout
- Include appropriate recheck timing
- Keep the email concise but thorough (150-250 words for the body)
- Sign off with the vet's name

Return ONLY valid JSON with this structure:
{
  "subject": "email subject line",
  "body": "full email body text with line breaks as \\n"
}"""


class FollowUpDraftAgent:
    """
    Generates follow-up email drafts.
    Uses Gemini LLM when available, falls back to tone templates.
    """

    def generate(
        self,
        timeblock: TimeBlock,
        patient: Optional[Patient],
        owner: Optional[Owner],
        vet_name: str,
        procedure: Optional[str],
        tone: Optional[str] = None,
    ) -> FollowUpDraft:
        effective_tone = tone or _tone_for_procedure(procedure)

        # Try LLM first
        client = _get_gemini()
        if client and client is not False:
            try:
                return self._generate_llm(client, timeblock, patient, owner, vet_name, procedure, effective_tone)
            except Exception as e:
                log.warning(f"FollowUp Agent: LLM generation failed ({e}), falling back to template")

        # Fallback to template
        return self._generate_template(timeblock, patient, owner, vet_name, procedure, effective_tone)

    def _generate_llm(
        self,
        client,
        timeblock: TimeBlock,
        patient: Optional[Patient],
        owner: Optional[Owner],
        vet_name: str,
        procedure: Optional[str],
        tone: str,
    ) -> FollowUpDraft:
        """Generate follow-up email using Gemini LLM."""
        patient_name = patient.name if patient else "your pet"
        owner_name = owner.name if owner else "Valued Client"
        proc_str = procedure or "General examination"

        parts = [
            f"Patient: {patient_name}",
            f"Owner: {owner_name}",
            f"Veterinarian: {vet_name}",
            f"Procedure: {proc_str}",
            f"Visit type/tone: {tone}",
        ]
        if patient:
            if patient.species:
                parts.append(f"Species: {patient.species}")
            if patient.breed:
                parts.append(f"Breed: {patient.breed}")
            if patient.age:
                parts.append(f"Age: {patient.age}")

        user_prompt = "\n".join(parts) + "\n\nWrite the follow-up email."

        response = client.models.generate_content(
            model=GEMINI_FLASH,
            contents=[
                {"role": "user", "parts": [{"text": FOLLOWUP_SYSTEM_PROMPT + "\n\n" + user_prompt}]}
            ],
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        data = json.loads(text)
        log.info(f"FollowUp Agent: LLM-generated email for {patient_name} ({proc_str})")

        return FollowUpDraft(
            timeblock_id=str(timeblock.id),
            subject=data.get("subject", f"{patient_name}'s Visit Follow-Up"),
            body=data.get("body", ""),
            tone=tone,
            status="draft",
        )

    def _generate_template(
        self,
        timeblock: TimeBlock,
        patient: Optional[Patient],
        owner: Optional[Owner],
        vet_name: str,
        procedure: Optional[str],
        tone: str,
    ) -> FollowUpDraft:
        """Fallback: Generate follow-up from tone templates."""
        template = TEMPLATES.get(tone, TEMPLATES["wellness"])

        patient_name = patient.name if patient else "your pet"
        owner_name = owner.name if owner else "Valued Client"
        proc_str = procedure or "General examination"
        recheck = RECHECK_INTERVALS.get(tone, "as clinically indicated")

        slots = {
            "patient_name": patient_name,
            "owner_name": owner_name,
            "vet_name": vet_name,
            "procedure": proc_str,
            "recheck_interval": recheck,
        }

        subject = template["subject"].format(**slots)
        body = template["body"].format(**slots)

        return FollowUpDraft(
            timeblock_id=str(timeblock.id),
            subject=subject,
            body=body,
            tone=tone,
            status="draft",
        )
