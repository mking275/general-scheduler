"""
T005 + T030 — SoapDraftAgent
Generates structured SOAP note drafts from procedure templates + PreExamBrief.
"""
from typing import Optional
from ..models import SoapNote, PreExamBrief, Patient


# 5 procedure templates per spec T030
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

# Fallback template
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


class SoapDraftAgent:
    """
    Generates a procedure-specific SOAP note draft.
    Subjective is pre-filled from PreExamBrief if available.
    Objective schema is procedure-specific.
    Plan is the template standard text.
    """

    def generate(
        self,
        timeblock_id: str,
        procedure: Optional[str],
        patient: Optional[Patient],
        brief: Optional[PreExamBrief],
    ) -> SoapNote:
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
