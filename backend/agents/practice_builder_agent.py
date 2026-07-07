"""
Feature 008 — Practice Builder Agent
Parses free-text descriptions and URLs to extract practice context.

VERA_PROFESSIONAL_BOUNDARIES:
    I am your Chief of Staff — not a veterinarian, not your attorney.
    Clinical decisions remain with your licensed DVMs.
    I parse what you give me — I do not fabricate clinical credentials.

Pure Python heuristics — no external LLM calls.
"""
import re
from typing import Optional
from urllib.parse import urlparse

VERA_PROFESSIONAL_BOUNDARIES = (
    "I am your Chief of Staff — not a veterinarian, not your attorney. "
    "I parse what you give me — I do not fabricate clinical credentials."
)

# Provider role keywords
_PROVIDER_ROLES = {"dvm", "dvm/phd", "phd", "dr", "doctor", "veterinarian",
                   "vet", "associate", "technician", "tech", "lvt", "cvt",
                   "receptionist", "manager", "assistant"}

# Days of week patterns
_DAYS_RE = re.compile(
    r"\b(mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|"
    r"sat(?:urday)?|sun(?:day)?)\b",
    re.IGNORECASE,
)

# Hours patterns (e.g. "8am-6pm", "8:00 AM to 5:00 PM")
_HOURS_RE = re.compile(
    r"\b(\d{1,2}(?::\d{2})?(?:\s*[ap]m)?)\s*(?:to|-|–)\s*(\d{1,2}(?::\d{2})?(?:\s*[ap]m)?)\b",
    re.IGNORECASE,
)

# Room keywords
_ROOM_KEYWORDS = {"room", "suite", "exam", "iso", "isolation", "surgical",
                  "surgery", "treatment", "radiology", "imaging", "ward",
                  "bay", "kennel", "dental"}

# Practice type keywords
_PRACTICE_TYPES = {
    "small animal": "small_animal",
    "large animal": "large_animal",
    "equine": "equine",
    "mixed": "mixed",
    "exotic": "exotic",
    "avian": "avian",
    "feline": "feline",
    "canine": "canine",
    "emergency": "emergency",
    "specialty": "specialty",
    "general": "general",
}

# Service keywords
_SERVICES = {
    "wellness", "vaccination", "vaccine", "dental", "surgery", "spay",
    "neuter", "radiograph", "xray", "x-ray", "ultrasound", "boarding",
    "grooming", "acupuncture", "laser", "telemedicine", "urgent", "emergency",
    "preventive", "orthopedic", "oncology", "dermatology", "cardiology",
}

# Normalize day abbreviations
_DAY_ABBREV = {
    "mon": "Mon", "monday": "Mon",
    "tue": "Tue", "tuesday": "Tue",
    "wed": "Wed", "wednesday": "Wed",
    "thu": "Thu", "thursday": "Thu",
    "fri": "Fri", "friday": "Fri",
    "sat": "Sat", "saturday": "Sat",
    "sun": "Sun", "sunday": "Sun",
}


def parse_free_text(text: str) -> dict:
    """
    Extract practice context from a free-text description.
    Returns dict with: practice_type, providers, rooms, hours, services.
    No LLM — pure regex + keyword matching.
    """
    result: dict = {
        "practice_type": None,
        "providers": [],
        "rooms": [],
        "hours": [],
        "services": [],
    }

    lower = text.lower()

    # Practice type
    for keyword, ptype in _PRACTICE_TYPES.items():
        if keyword in lower:
            result["practice_type"] = ptype
            break
    if not result["practice_type"]:
        # Default heuristic: any text mentioning dogs/cats → small animal
        if any(w in lower for w in ("dog", "cat", "puppy", "kitten", "feline", "canine")):
            result["practice_type"] = "small_animal"

    # Services
    found_services = []
    for svc in _SERVICES:
        if svc in lower:
            found_services.append(svc)
    result["services"] = list(set(found_services))

    # Hours
    hours_matches = _HOURS_RE.findall(text)
    for start, end in hours_matches:
        result["hours"].append(f"{start.strip()}–{end.strip()}")

    # Days
    days_found = [_DAY_ABBREV[m.lower()] for m in _DAYS_RE.findall(text)]
    days_found = list(dict.fromkeys(days_found))  # deduplicate, preserve order

    # Providers — look for Dr./DVM patterns
    providers = _extract_providers(text)
    result["providers"] = providers

    # Rooms — look for room-keyword phrases
    rooms = _extract_rooms(text)
    result["rooms"] = rooms

    # Attach days to first provider as working days if found
    if days_found and result["providers"]:
        result["providers"][0]["days"] = days_found

    return result


def _extract_providers(text: str) -> list:
    """Extract provider names and roles from text."""
    providers = []

    # Pattern: "Dr. FirstName LastName" or "FirstName LastName, DVM"
    dr_pattern = re.compile(
        r"Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    )
    dvm_pattern = re.compile(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*(DVM|D\.V\.M\.|DVM/PhD|LVT|CVT)",
        re.IGNORECASE,
    )
    # Count pattern: "3 vets", "2 veterinarians", "a team of 4"
    count_pattern = re.compile(
        r"(\d+|one|two|three|four|five|six|seven|eight)\s+(?:full[- ]time\s+)?(?:vet(?:erinarian)?s?|DVM|doctor)",
        re.IGNORECASE,
    )

    seen_names = set()

    for m in dr_pattern.finditer(text):
        name = f"Dr. {m.group(1)}"
        if name not in seen_names:
            seen_names.add(name)
            providers.append({"name": name, "role": "DVM", "days": []})

    for m in dvm_pattern.finditer(text):
        name = m.group(1).strip()
        role = m.group(2).upper()
        full = f"Dr. {name}" if not name.startswith("Dr") else name
        if full not in seen_names:
            seen_names.add(full)
            providers.append({"name": full, "role": role, "days": []})

    # If no named providers but count found, create placeholders
    if not providers:
        for m in count_pattern.finditer(text):
            count_str = m.group(1).lower()
            word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4,
                           "five": 5, "six": 6, "seven": 7, "eight": 8}
            count = word_to_num.get(count_str, None) or int(count_str)
            for i in range(min(count, 8)):
                label = f"Vet {i + 1}"
                if label not in seen_names:
                    seen_names.add(label)
                    providers.append({"name": label, "role": "DVM", "days": []})
            break  # only use first count match

    return providers


def _extract_rooms(text: str) -> list:
    """Extract room names from text."""
    rooms = []
    seen = set()

    # Named rooms: "Exam Room 1", "Surgical Suite", "Iso Ward", etc.
    room_pattern = re.compile(
        r"\b((?:" + "|".join(_ROOM_KEYWORDS) + r")[\w\s]*\d*)\b",
        re.IGNORECASE,
    )
    for m in room_pattern.finditer(text):
        name = m.group(1).strip().title()
        if name.lower() not in seen and len(name) < 40:
            seen.add(name.lower())
            rooms.append({"name": name})

    # Count pattern: "4 exam rooms", "2 surgical suites"
    count_room_pattern = re.compile(
        r"(\d+|one|two|three|four|five|six)\s+(exam\s+rooms?|suites?|treatment\s+rooms?|surgical\s+rooms?)",
        re.IGNORECASE,
    )
    word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    for m in count_room_pattern.finditer(text):
        count_str = m.group(1).lower()
        count = word_to_num.get(count_str, None) or int(count_str)
        label_base = m.group(2).strip().title()
        for i in range(min(count, 8)):
            name = f"{label_base} {i + 1}"
            if name.lower() not in seen:
                seen.add(name.lower())
                rooms.append({"name": name})

    return rooms


def parse_url(url: str) -> dict:
    """
    Detect URL type (Google Maps vs website) and extract practice context.
    Returns dict compatible with parse_free_text output.
    No LLM — scraping via httpx + BeautifulSoup4.
    """
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    result: dict = {
        "practice_type": None,
        "providers": [],
        "rooms": [],
        "hours": [],
        "services": [],
        "address": None,
        "phone": None,
        "website_url": url,
        "source": "url_scrape",
    }

    if "google.com/maps" in url or "maps.google" in hostname or "maps.app.goo.gl" in url:
        result["source"] = "google_maps"
        result.update(_scrape_google_maps(url))
    else:
        result["source"] = "website"
        result.update(_scrape_website(url))

    return result


def _scrape_google_maps(url: str) -> dict:
    """
    Scrape Google Maps listing. Best-effort; degrades gracefully.
    Returns partial dict to merge into result.
    """
    data: dict = {}
    try:
        import httpx
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; VetAgent/1.0; "
                "+https://vetagent.app/bot)"
            )
        }
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract structured data if present
        import json as _json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = _json.loads(script.string or "")
                if isinstance(ld, list):
                    ld = ld[0]
                if ld.get("@type") in ("LocalBusiness", "VeterinaryCare", "AnimalShelter"):
                    if ld.get("name"):
                        data["maps_name"] = ld["name"]
                    if ld.get("telephone"):
                        data["phone"] = ld["telephone"]
                    if ld.get("address"):
                        addr = ld["address"]
                        if isinstance(addr, dict):
                            data["address"] = (
                                f"{addr.get('streetAddress', '')} "
                                f"{addr.get('addressLocality', '')} "
                                f"{addr.get('addressRegion', '')} "
                                f"{addr.get('postalCode', '')}"
                            ).strip()
                    if ld.get("openingHours"):
                        data["hours"] = ld["openingHours"] if isinstance(ld["openingHours"], list) else [ld["openingHours"]]
                    if ld.get("hasOfferCatalog"):
                        services = []
                        catalog = ld["hasOfferCatalog"]
                        if isinstance(catalog, dict) and catalog.get("itemListElement"):
                            for item in catalog["itemListElement"]:
                                if isinstance(item, dict) and item.get("name"):
                                    services.append(item["name"])
                        data["services"] = services
                    break
            except Exception:
                continue

    except Exception as e:
        data["scrape_error"] = str(e)

    return data


def _scrape_website(url: str) -> dict:
    """
    Scrape a practice website for name, address, hours, services, team.
    Returns partial dict to merge into result.
    """
    data: dict = {}
    try:
        import httpx
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; VetAgent/1.0; "
                "+https://vetagent.app/bot)"
            )
        }
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Structured data first
        import json as _json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = _json.loads(script.string or "")
                if isinstance(ld, list):
                    ld = ld[0]
                if ld.get("telephone"):
                    data["phone"] = ld["telephone"]
                if ld.get("address") and isinstance(ld["address"], dict):
                    addr = ld["address"]
                    data["address"] = (
                        f"{addr.get('streetAddress', '')} "
                        f"{addr.get('addressLocality', '')} "
                        f"{addr.get('addressRegion', '')} "
                        f"{addr.get('postalCode', '')}"
                    ).strip()
                if ld.get("openingHours"):
                    oh = ld["openingHours"]
                    data["hours"] = oh if isinstance(oh, list) else [oh]
                break
            except Exception:
                continue

        # Extract team members from page text
        page_text = soup.get_text(separator=" ", strip=True)
        providers = _extract_providers(page_text)
        if providers:
            data["providers"] = providers

        # Extract services from navigation or page headings
        services = []
        for tag in soup.find_all(["h1", "h2", "h3", "li"]):
            text = tag.get_text(strip=True).lower()
            for svc in _SERVICES:
                if svc in text and svc not in services:
                    services.append(svc)
        if services:
            data["services"] = services[:10]  # cap at 10

    except Exception as e:
        data["scrape_error"] = str(e)

    return data
