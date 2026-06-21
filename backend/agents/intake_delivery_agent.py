"""
intake_delivery_agent.py — Intake form question sets and delivery simulation.

Responsibilities:
  - Define static question sets per appointment type (wellness, sick, vaccines,
    dental, follow-up).
  - schedule_delivery: compute send delay and log simulated email/SMS dispatch.
  - run_flag_logic: evaluate answers against flag rules and return raised flags.

Does NOT do: real email/SMS sending (Phase 1 = simulated/logged only),
AI risk scoring (Phase 2).

Logging prefix: VERA (Intake):
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# ── Static Intake Question Sets ────────────────────────────────────────────
# Key = appointment_type slug; value = ordered list of question dicts.
# {pet_name} and {vet_name} are interpolated at serve time.
INTAKE_QUESTION_SETS: dict[str, list[dict]] = {
    "wellness": [
        {
            "id": "q_appetite",
            "order": 1,
            "text": "How has {pet_name}'s appetite been over the past month?",
            "type": "single_choice",
            "options": ["Great", "Normal", "Reduced", "Not eating"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_water",
            "order": 2,
            "text": "How is {pet_name}'s water intake?",
            "type": "single_choice",
            "options": ["Normal", "Drinking more than usual", "Drinking less than usual"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_weight",
            "order": 3,
            "text": "Has {pet_name}'s weight changed recently?",
            "type": "single_choice",
            "options": ["Seems heavier", "Seems the same", "Seems lighter"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_energy",
            "order": 4,
            "text": "How is {pet_name}'s energy level?",
            "type": "single_choice",
            "options": ["Very active", "Normal", "Less active", "Lethargic"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_stool",
            "order": 5,
            "text": "How are {pet_name}'s stools?",
            "type": "single_choice",
            "options": ["Normal", "Loose/diarrhea", "Constipated", "Blood noticed"],
            "required": False,
            "skippable": True,
        },
        {
            "id": "q_vomiting",
            "order": 6,
            "text": "Has {pet_name} been vomiting?",
            "type": "single_choice",
            "options": ["No", "Once or twice", "Frequently (3+ times)"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_medications",
            "order": 7,
            "text": "Is {pet_name} currently on any medications or supplements?",
            "type": "free_text",
            "options": [],
            "required": False,
            "skippable": True,
        },
        {
            "id": "q_concerns",
            "order": 8,
            "text": "Are there any other concerns you'd like {vet_name} to know about?",
            "type": "free_text",
            "options": [],
            "required": False,
            "skippable": True,
        },
    ],
    "sick-visit": [
        {
            "id": "q_main_concern",
            "order": 1,
            "text": "What is your main concern about {pet_name} today?",
            "type": "free_text",
            "options": [],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_eating",
            "order": 2,
            "text": "Is {pet_name} eating?",
            "type": "single_choice",
            "options": ["Yes, normal", "Less than usual", "No"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_ingested",
            "order": 3,
            "text": "Has {pet_name} ingested anything unusual, toxic, or foreign?",
            "type": "single_choice",
            "options": ["No", "Possibly", "Yes — bring list"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_duration",
            "order": 4,
            "text": "How long has {pet_name} been showing these symptoms?",
            "type": "single_choice",
            "options": ["Less than 24 hours", "1–3 days", "4–7 days", "More than a week"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_severity",
            "order": 5,
            "text": "How would you rate the severity right now?",
            "type": "single_choice",
            "options": ["Mild", "Moderate", "Severe", "Emergency — worsening rapidly"],
            "required": True,
            "skippable": False,
        },
    ],
    "vaccines": [
        {
            "id": "q_vaccine_reaction",
            "order": 1,
            "text": "Has {pet_name} ever had a reaction to a vaccine before?",
            "type": "single_choice",
            "options": ["No", "Yes — mild (lethargy, soreness)", "Yes — severe (swelling, vomiting)"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_current_health",
            "order": 2,
            "text": "Is {pet_name} showing any signs of illness today?",
            "type": "single_choice",
            "options": ["No, healthy", "Mild sneezing/cough", "Yes — I have concerns"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_medications_vax",
            "order": 3,
            "text": "Is {pet_name} currently on steroids or immunosuppressants?",
            "type": "single_choice",
            "options": ["No", "Yes"],
            "required": True,
            "skippable": False,
        },
    ],
    "dental": [
        {
            "id": "q_dental_symptoms",
            "order": 1,
            "text": "Have you noticed any of the following in {pet_name}?",
            "type": "multi_choice",
            "options": ["Bad breath", "Difficulty eating", "Pawing at mouth",
                        "Visible tartar", "Red/bleeding gums", "None"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_cardiac_meds",
            "order": 2,
            "text": "Is {pet_name} currently on any heart or blood pressure medications?",
            "type": "free_text",
            "options": [],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_anesthesia_history",
            "order": 3,
            "text": "Has {pet_name} had anesthesia before? Any complications?",
            "type": "free_text",
            "options": [],
            "required": False,
            "skippable": True,
        },
        {
            "id": "q_dental_fasting",
            "order": 4,
            "text": "Have you been instructed to withhold food and water before the procedure?",
            "type": "single_choice",
            "options": ["Yes, understood", "Not sure — please advise"],
            "required": True,
            "skippable": False,
        },
    ],
    "follow-up": [
        {
            "id": "q_improvement",
            "order": 1,
            "text": "How is {pet_name} doing since your last visit?",
            "type": "single_choice",
            "options": ["Much better", "Slightly better", "About the same", "Worse"],
            "required": True,
            "skippable": False,
        },
        {
            "id": "q_medication_compliance",
            "order": 2,
            "text": "Has {pet_name} been taking all prescribed medications as directed?",
            "type": "single_choice",
            "options": ["Yes, fully", "Mostly", "Had difficulty giving them", "No"],
            "required": False,
            "skippable": True,
        },
        {
            "id": "q_new_concerns",
            "order": 3,
            "text": "Have any new concerns come up since the last visit?",
            "type": "free_text",
            "options": [],
            "required": False,
            "skippable": True,
        },
    ],
}


# ── Flag Logic ─────────────────────────────────────────────────────────────

def run_flag_logic(appointment_type: str, answers: dict[str, str]) -> list[str]:
    """
    Evaluate submitted intake answers against flag rules.

    Args:
        appointment_type: e.g. "wellness", "sick-visit", "dental", "vaccines".
        answers:          dict of {question_id: answer_str}.

    Returns:
        List of flag name strings (empty list if no flags raised).
    """
    flags: list[str] = []

    # flag_weight_loss_energy
    if (answers.get("q_weight") == "Seems lighter"
            and answers.get("q_energy") in ("Less active", "Lethargic")):
        flags.append("flag_weight_loss_energy")

    # flag_monitor_appetite
    if answers.get("q_appetite") in ("Reduced", "Not eating"):
        flags.append("flag_monitor_appetite")

    # flag_anesthesia_risk (dental)
    if appointment_type == "dental":
        cardiac = answers.get("q_cardiac_meds", "").strip()
        if cardiac and cardiac.lower() not in ("no", "none", ""):
            flags.append("flag_anesthesia_risk")

    # flag_potential_toxin (sick-visit)
    if appointment_type == "sick-visit":
        ingested = answers.get("q_ingested", "No")
        if ingested != "No":
            flags.append("flag_potential_toxin")

    # flag_no_food_water (sick-visit)
    if appointment_type == "sick-visit":
        eating = answers.get("q_eating", "Yes, normal")
        if eating == "No":
            flags.append("flag_no_food_water")

    # flag_vaccine_reaction (vaccines)
    if appointment_type == "vaccines":
        reaction = answers.get("q_vaccine_reaction", "No")
        if reaction != "No":
            flags.append("flag_vaccine_reaction")

    return flags


# ── Delivery Agent ─────────────────────────────────────────────────────────

class IntakeDeliveryAgent:
    """
    Simulate intake form delivery scheduling.

    Phase 1: All delivery is simulated — writes a log entry instead of
    sending a real email or SMS.
    """

    def __init__(self, db, log_fn=None):
        """
        Args:
            db:     Repository instance.
            log_fn: Optional callable(str) for verbose agent log entries.
        """
        self._db = db
        self._log = log_fn or (lambda msg: None)

    def schedule_delivery(
        self,
        intake_token_id: str,
        appointment_datetime: datetime,
    ) -> None:
        """
        Compute intake form send time and log simulated delivery.

        Send time rules (Phase 1):
          - If appointment is > 48 hours away: send 48 hours before.
          - If 24–48 hours away: send immediately.
          - If < 24 hours: send immediately.

        Args:
            intake_token_id:      Token UUID string.
            appointment_datetime: Appointment start datetime (UTC naive).
        """
        now = datetime.utcnow()
        hours_until = (appointment_datetime - now).total_seconds() / 3600.0

        if hours_until > 48:
            send_at = appointment_datetime - timedelta(hours=48)
            delay_label = "T-48h"
        else:
            send_at = now
            delay_label = "immediate"

        # Fetch token info for logging
        token_row = self._db.get_intake_token(intake_token_id)
        owner_id = token_row.get("owner_id", "?") if token_row else "?"
        appt_type = token_row.get("appointment_type", "?") if token_row else "?"

        # Phase 1: simulate delivery (log only)
        self._log(
            f"VERA (Intake): [SIMULATED] intake form scheduled "
            f"token={intake_token_id[:8]} owner={owner_id[:8] if len(owner_id) >= 8 else owner_id} "
            f"type={appt_type} send_at={send_at.isoformat()} delay={delay_label}"
        )

    def get_questions(
        self,
        appointment_type: str,
        pet_name: str = "your pet",
        vet_name: str = "your vet",
    ) -> list[dict]:
        """
        Return the question list for an appointment type with name interpolation.

        Args:
            appointment_type: Key into INTAKE_QUESTION_SETS.
            pet_name:         Pet's name for text substitution.
            vet_name:         Vet's name for text substitution.

        Returns:
            List of question dicts with 'text' interpolated.
        """
        question_set = INTAKE_QUESTION_SETS.get(
            appointment_type,
            INTAKE_QUESTION_SETS["wellness"]
        )
        result = []
        for q in question_set:
            q_copy = q.copy()
            q_copy["text"] = (
                q_copy["text"]
                .replace("{pet_name}", pet_name)
                .replace("{vet_name}", vet_name)
            )
            q_copy["answer"] = None  # populated by route handler from intake_responses
            result.append(q_copy)
        return result

    def validate_answers(
        self,
        appointment_type: str,
        answers: list[dict],
    ) -> tuple[bool, list[str], str]:
        """
        Validate submitted answers against the question set.

        Returns:
            (valid: bool, missing_ids: list[str], error_msg: str)
        """
        question_set = INTAKE_QUESTION_SETS.get(
            appointment_type,
            INTAKE_QUESTION_SETS["wellness"]
        )
        question_map = {q["id"]: q for q in question_set}
        answer_map = {a["question_id"]: a for a in answers}
        missing: list[str] = []

        for q_id, q in question_map.items():
            if not q.get("required", False):
                continue
            ans = answer_map.get(q_id)
            if ans is None:
                missing.append(q_id)
                continue
            if ans.get("skipped") and not q.get("skippable", True):
                missing.append(q_id)
                continue
            if not ans.get("skipped") and not ans.get("answer"):
                missing.append(q_id)

        if missing:
            return False, missing, f"Missing required answers for: {', '.join(missing)}"
        return True, [], ""
