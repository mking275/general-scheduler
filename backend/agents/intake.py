import re
from datetime import datetime, date, time, timedelta
from ..models import Job

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

PROCEDURE_MAP = {
    "surgery": "Surgery",
    "checkup": "Check-up",
    "check-up": "Check-up",
    "check up": "Check-up",
    "vaccination": "Vaccination",
    "vaccine": "Vaccination",
    "dental": "Dental Cleaning",
    "teeth cleaning": "Dental Cleaning",
    "teeth clean": "Dental Cleaning",
    "tooth cleaning": "Dental Cleaning",
    "dental cleaning": "Dental Cleaning",
    "scale and polish": "Dental Cleaning",
    "tartar": "Dental Cleaning",
    "grooming": "Grooming",
    "xray": "X-Ray",
    "x-ray": "X-Ray",
    "ultrasound": "Ultrasound",
    "exam": "Examination",
    "examination": "Examination",
    "consultation": "Consultation",
    "emergency": "Emergency Visit",
}

SKILL_MAP = {
    "surgery": "Surgery",
    "dental": "Dental",
    "teeth cleaning": "Dental",
    "teeth clean": "Dental",
    "tooth cleaning": "Dental",
    "dental cleaning": "Dental",
    "scale and polish": "Dental",
    "tartar": "Dental",
    "checkup": "General Practice",
    "check-up": "General Practice",
    "check up": "General Practice",
    "vaccination": "General Practice",
    "vaccine": "General Practice",
    "grooming": "Grooming",
    "xray": "X-Ray",
    "x-ray": "X-Ray",
    "ultrasound": "Ultrasound",
    "exam": "General Practice",
    "examination": "General Practice",
    "consultation": "General Practice",
    "avian": "Avian",
    "bird": "Avian",
    "exotic": "Exotics",
    "reptile": "Exotics",
}

ANIMAL_KEYWORDS = [
    # Color + breed combos (must come before bare breed names)
    "black lab", "yellow lab", "chocolate lab", "golden lab",
    "black labrador", "yellow labrador", "chocolate labrador",
    "black cat", "white cat", "orange cat", "tabby cat",
    # Breeds — longer names first to avoid partial matches
    "golden retriever", "german shepherd", "australian shepherd",
    "border collie", "cocker spaniel", "springer spaniel",
    "jack russell", "shih tzu", "bichon frise",
    "labrador retriever", "labrador",
    "poodle", "bulldog", "beagle", "husky", "dachshund",
    "chihuahua", "pomeranian", "rottweiler", "doberman",
    "great dane", "saint bernard", "dalmatian",
    "maltese", "schnauzer", "weimaraner",
    # Common shorthand / abbrevs
    "lab", "retriever", "shepherd", "spaniel", "collie",
    "aussie", "staffie", "westie", "yorkie", "tabby",
    # Species
    "cat", "kitten", "dog", "puppy", "rabbit", "hamster",
    "parrot", "bird", "budgie", "cockatiel",
    "iguana", "snake", "turtle", "gecko",
    "ferret", "guinea pig", "chinchilla",
]

WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# ---------------------------------------------------------------------------
# Date/time parsing helpers
# ---------------------------------------------------------------------------

def _next_weekday(weekday: int, from_date: date) -> date:
    """Return the next occurrence of `weekday` (0=Mon…6=Sun) after from_date."""
    days_ahead = weekday - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

ORDINAL_MAP = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "last": -1,
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
}


def _first_weekday_of_month(year: int, month: int, weekday: int = 0) -> date:
    """Return the first occurrence of `weekday` (0=Mon) in the given month."""
    d = date(year, month, 1)
    days_ahead = (weekday - d.weekday()) % 7
    return d + timedelta(days=days_ahead)


def _nth_weekday_of_month(year: int, month: int, n: int, weekday: int = 0) -> date:
    """Return the nth occurrence (1-based, or -1 for last) of weekday in month."""
    if n == -1:
        # Last occurrence: go to end of month and work backwards
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)
    first = _first_weekday_of_month(year, month, weekday)
    return first + timedelta(weeks=n - 1)


def _parse_date(text: str) -> date | None:
    """
    Extract a target *date* from natural language.
    Returns None if no date expression found (caller defaults to today).
    """
    lower = text.lower()
    today = date.today()

    # --- Simple relative phrases ---
    if "next week" in lower and not re.search(r"next week of", lower):
        return _next_weekday(0, today)           # next Monday
    if "tomorrow" in lower:
        return today + timedelta(days=1)
    if "day after tomorrow" in lower:
        return today + timedelta(days=2)
    if "today" in lower or "right now" in lower:
        return today

    # --- "in X days/weeks" ---
    m = re.search(r"in\s+(\d+)\s+days?", lower)
    if m:
        return today + timedelta(days=int(m.group(1)))
    m = re.search(r"in\s+(\d+)\s+weeks?", lower)
    if m:
        return today + timedelta(weeks=int(m.group(1)))

    # --- "(first|second|...|last) week of <month>" ---
    month_names = "|".join(MONTH_MAP.keys())
    ordinal_names = "|".join(ORDINAL_MAP.keys())
    m = re.search(
        rf"({ordinal_names})\s+week\s+of\s+({month_names})",
        lower,
    )
    if m:
        ordinal_word, month_word = m.group(1), m.group(2)
        n = ORDINAL_MAP[ordinal_word]
        month_num = MONTH_MAP[month_word]
        year = today.year if month_num >= today.month else today.year + 1
        # "first week of July" → first Monday of July
        return _nth_weekday_of_month(year, month_num, n, weekday=0)

    # --- "early/mid/late <month>" ---
    m = re.search(rf"(early|mid|late)\s+({month_names})", lower)
    if m:
        part, month_word = m.group(1), m.group(2)
        month_num = MONTH_MAP[month_word]
        year = today.year if month_num >= today.month else today.year + 1
        day = {"early": 3, "mid": 15, "late": 25}[part]
        return date(year, month_num, day)

    # --- "<month> <ordinal/day>" e.g. "July 4th", "July 4", "Jul 15" ---
    m = re.search(
        rf"({month_names})\s+(\d{{1,2}})(st|nd|rd|th)?",
        lower,
    )
    if m:
        month_num = MONTH_MAP[m.group(1)]
        day = int(m.group(2))
        year = today.year if (month_num > today.month or (month_num == today.month and day >= today.day)) else today.year + 1
        try:
            return date(year, month_num, day)
        except ValueError:
            pass

    # --- "<ordinal> of <month>" e.g. "4th of July" ---
    m = re.search(
        rf"(\d{{1,2}})(st|nd|rd|th)?\s+of\s+({month_names})",
        lower,
    )
    if m:
        day = int(m.group(1))
        month_num = MONTH_MAP[m.group(3)]
        year = today.year if (month_num > today.month or (month_num == today.month and day >= today.day)) else today.year + 1
        try:
            return date(year, month_num, day)
        except ValueError:
            pass

    # --- "next <weekday>" ---
    m = re.search(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", lower)
    if m:
        return _next_weekday(WEEKDAY_MAP[m.group(1)], today)

    # --- bare weekday name → nearest future occurrence ---
    for day_name, day_num in WEEKDAY_MAP.items():
        if re.search(rf"\b{day_name}\b", lower):
            return _next_weekday(day_num, today)

    # --- MM/DD or MM-DD or MM/DD/YYYY ---
    m = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", text)
    if m:
        month_num, day = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            return date(year, month_num, day)
        except ValueError:
            pass

    return None



def _parse_time(text: str) -> time | None:
    """
    Extract a target *time* from natural language.
    Returns None if no time expression found.
    """
    lower = text.lower()

    # "at Xam" / "at X:MMpm"
    m = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lower)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        meridiem = m.group(3)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return time(hour % 24, minute)

    # "X o'clock"
    m = re.search(r"(\d{1,2})\s*o'?clock", lower)
    if m:
        return time(int(m.group(1)) % 24, 0)

    # "morning" → 9am, "afternoon" → 2pm, "evening" → 5pm
    if "morning" in lower:
        return time(9, 0)
    if "afternoon" in lower:
        return time(14, 0)
    if "evening" in lower:
        return time(17, 0)

    return None


# ---------------------------------------------------------------------------
# IntakeAgent
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# T021 — Symptom extraction helpers
# ---------------------------------------------------------------------------

SYMPTOM_KEYWORDS = [
    "lethargy", "vomiting", "diarrhea", "anorexia", "coughing",
    "limping", "scratching", "seizure", "collapse", "bleeding",
    "drinking", "urinating", "sneezing", "wheezing", "discharge",
    "swelling", "lameness", "trembling", "shaking",
]

SYMPTOM_FOCUS_MAP = {
    "lethargy":   ["Metabolic", "GI", "hematology"],
    "vomiting":   ["GI", "metabolic panel"],
    "diarrhea":   ["GI", "parasitology"],
    "anorexia":   ["GI", "metabolic panel"],
    "coughing":   ["Respiratory", "cardiovascular"],
    "limping":    ["Orthopedic", "pain management"],
    "scratching": ["Dermatology", "allergy panel"],
    "seizure":    ["Neurology", "brain imaging"],
    "collapse":   ["Cardiovascular", "emergency triage"],
    "bleeding":   ["Hematology", "coagulation panel"],
    "drinking":   ["Endocrinology", "renal panel"],
    "urinating":  ["Renal panel", "urinalysis"],
    "sneezing":   ["Respiratory", "upper respiratory"],
    "wheezing":   ["Respiratory", "bronchoscopy"],
    "discharge":  ["Infection panel", "cytology"],
    "swelling":   ["Orthopedic", "inflammation"],
    "lameness":   ["Orthopedic", "radiography"],
    "trembling":  ["Neurology", "pain assessment"],
    "shaking":    ["Neurology", "ear exam"],
}

_DURATION_RE = re.compile(
    r"(\d+)\s*(day|week|hour)s?\s*(ago|since)?",
    re.IGNORECASE,
)

_SEVERITY_HIGH = {"severe", "emergency", "critical", "extreme", "urgent", "very bad", "terrible"}
_SEVERITY_LOW  = {"little", "mild", "slight", "minor", "barely", "bit", "somewhat"}


def _extract_duration_days(text: str, symptom: str) -> int:
    """Attempt to find duration near the symptom mention."""
    lower = text.lower()
    idx = lower.find(symptom)
    context = lower[max(0, idx - 40): idx + 80]
    m = _DURATION_RE.search(context)
    if not m:
        return 1  # default 1 day
    amount = int(m.group(1))
    unit = m.group(2).lower()
    if unit == "week":
        return amount * 7
    if unit == "hour":
        return max(1, amount // 24)
    return amount


def _extract_severity(text: str, symptom: str) -> str:
    lower = text.lower()
    idx = lower.find(symptom)
    context = lower[max(0, idx - 30): idx + 60]
    for word in _SEVERITY_HIGH:
        if word in context:
            return "high"
    for word in _SEVERITY_LOW:
        if word in context:
            return "low"
    return "mild"


class IntakeAgent:
    def extract_symptoms(self, text: str):
        """
        T021: Extract structured symptoms from owner free-text response.
        Returns a PreExamBrief-compatible dict.
        """
        from ..models import PreExamBrief
        lower = text.lower()
        found_symptoms = []
        focus_set: set = set()

        for sym in SYMPTOM_KEYWORDS:
            if sym in lower:
                duration = _extract_duration_days(text, sym)
                severity = _extract_severity(text, sym)
                found_symptoms.append({
                    "name": sym,
                    "duration_days": duration,
                    "severity": severity,
                })
                for area in SYMPTOM_FOCUS_MAP.get(sym, []):
                    focus_set.add(area)

        # Build chief complaint
        if found_symptoms:
            symptom_names = [s["name"].capitalize() for s in found_symptoms]
            if len(symptom_names) == 1:
                chief = symptom_names[0]
            elif len(symptom_names) == 2:
                chief = f"{symptom_names[0]} and {symptom_names[1]}"
            else:
                chief = ", ".join(symptom_names[:-1]) + f", and {symptom_names[-1]}"
        else:
            chief = "General complaint — no specific symptoms identified"

        return {
            "chief_complaint": chief,
            "symptoms": found_symptoms,
            "owner_verbatim": text.strip(),
            "suggested_focus": sorted(focus_set),
        }

    def parse_request(self, text: str) -> Job:
        lower = text.lower()

        # --- Skills & Procedure (match longest phrase first to avoid shadowing) ---
        procedure = "General Visit"
        skills = ["General Practice"]
        for keyword in sorted(PROCEDURE_MAP, key=len, reverse=True):
            if keyword in lower:
                procedure = PROCEDURE_MAP[keyword]
                break
        for keyword in sorted(SKILL_MAP, key=len, reverse=True):
            if keyword in lower:
                skills = [SKILL_MAP[keyword]]
                break
        if "surgery" in lower:
            skills = ["Surgery"]

        # --- Patient name ---
        patient_name = None
        # Match longest animal keywords first (multi-word before single-word)
        for animal in sorted(ANIMAL_KEYWORDS, key=len, reverse=True):
            if animal in lower:
                patient_name = animal.title()
                break
        if not patient_name:
            # Fallback regex — stop at time/urgency phrases too
            m = re.search(
                r"\bfor\s+(a\s+|an\s+)?([A-Za-z][\w\s]{0,30}?)"
                r"(?:\s+(?:at|with|on|as soon|asap|immediately|now|next|tomorrow|today)\b|$)",
                text,
                re.IGNORECASE,
            )
            if m:
                candidate = m.group(2).strip()
                words = candidate.split()
                if 1 <= len(words) <= 4 and candidate.lower() not in {"the", "a", "an", "my"}:
                    patient_name = candidate.title()

        # --- Date & Time ---
        scheduled_date = _parse_date(text)
        scheduled_time = _parse_time(text)

        return Job(
            required_skills=skills,
            estimated_duration=60,
            patient_name=patient_name,
            procedure=procedure,
            soft_requirements=text,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
        )
