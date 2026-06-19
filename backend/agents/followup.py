"""
T005 + T026 — FollowUpDraftAgent
Generates post-appointment follow-up email drafts using tone templates.
"""
from typing import Optional
from ..models import FollowUpDraft, TimeBlock, Patient, Owner


# 3 tone templates per spec T026
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


class FollowUpDraftAgent:
    """
    Generates follow-up email drafts using 3 tone templates.
    Slots filled: patient_name, owner_name, vet_name, procedure, recheck_interval.
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
        # Determine tone from procedure if not explicitly specified
        effective_tone = tone or _tone_for_procedure(procedure)
        template = TEMPLATES.get(effective_tone, TEMPLATES["wellness"])

        patient_name = patient.name if patient else "your pet"
        owner_name = owner.name if owner else "Valued Client"
        proc_str = procedure or "General examination"
        recheck = RECHECK_INTERVALS.get(effective_tone, "as clinically indicated")

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
            tone=effective_tone,
            status="draft",
        )
