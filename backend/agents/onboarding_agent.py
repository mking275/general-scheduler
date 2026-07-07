"""
Feature 008 — Vera Onboarding Agent
Chief of Staff onboarding orchestrator.

VERA_PROFESSIONAL_BOUNDARIES:
    I am your Chief of Staff — not a veterinarian, not your attorney.
    Clinical decisions remain with your licensed DVMs.
    Regulatory compliance determinations belong to you or your qualified legal counsel.
    I can brief, organize, surface, and schedule — I do not diagnose or prescribe.

All agent actions are logged in VERA (Onboarding): action format.
No direct DB writes — all state changes go through OnboardingRepository.
"""
import re
import json
from datetime import datetime
from typing import List, Optional
from uuid import uuid4


# Vera Constitution professional boundaries constant (mirrored from models.py
# to avoid circular import; agents/ must not import from models.py at module level)
VERA_PROFESSIONAL_BOUNDARIES = (
    "I am your Chief of Staff — not a veterinarian, not your attorney. "
    "Clinical decisions remain with your licensed DVMs. "
    "Regulatory compliance determinations belong to you or your qualified legal counsel. "
    "I can brief, organize, surface, and schedule — I do not diagnose or prescribe."
)

_FIRST_ACTION_TARGETS = {
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

# Regex to extract city/state from practice name input (FR-009)
_CITY_STATE_RE = re.compile(
    r",?\s*([\w\s]+),?\s*([A-Z]{2})\s*$",
    re.IGNORECASE,
)


class OnboardingAgent:
    """
    Orchestrates the six-phase Vera onboarding experience.

    VERA_PROFESSIONAL_BOUNDARIES:
        Every method that touches session state emits a VERA (Onboarding): log entry.
        No DB writes bypass the repository layer.
    """

    def _log(self, action: str) -> str:
        """Format a Verbose Log entry in the required VERA (Module): action format."""
        entry = f"VERA (Onboarding): {action}"
        print(f"[VERA LOG] {entry}")  # also printed to server console
        return entry

    def _get_first_action_targets(self, role: Optional[str]) -> List[str]:
        """Return role-appropriate first-action targets for post-Replace (FR-032)."""
        key = (role or "owner").lower()
        return _FIRST_ACTION_TARGETS.get(key, _FIRST_ACTION_TARGETS["owner"])

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def handle_session_create(self, device_fingerprint: Optional[str] = None) -> dict:
        """
        Create a new onboarding session (Phase 0 — WELCOME).
        Returns session dict + verbose_log.
        """
        from ..onboarding_repository import onboarding_repo
        session = onboarding_repo.create_session(device_fingerprint)
        log = self._log("Session created — welcome flow initiated")
        return {**session, "verbose_log": [log]}

    def handle_role_selection(self, session_id: str, role: str) -> dict:
        """
        Store persona role (FR-007b, FR-007c).
        Returns verbose_log with role-aware acknowledgment.
        """
        from ..onboarding_repository import onboarding_repo
        role = role.lower()
        valid_roles = {"owner", "manager", "associate", "proxy"}
        if role not in valid_roles:
            # Map free-text role to closest (edge case from spec)
            role = self._map_freetext_role(role)

        onboarding_repo.patch_session(session_id, persona_role=role)

        role_labels = {
            "owner": "Practice Owner",
            "manager": "Practice Manager",
            "associate": "Associate Vet",
            "proxy": "Practice Manager (setting up for someone else)",
        }
        label = role_labels.get(role, role.capitalize())
        log = self._log(f"Role set to {role} — first-action targets updated for {label}")
        return {"updated_at": datetime.utcnow().isoformat(), "verbose_log": [log]}

    def _map_freetext_role(self, text: str) -> str:
        """Map free-text role input to closest valid role."""
        text = text.lower()
        if any(w in text for w in ("owner", "founder", "principal")):
            return "owner"
        if any(w in text for w in ("manager", "admin", "director", "head")):
            return "manager"
        if any(w in text for w in ("vet", "dvm", "doctor", "associate")):
            return "associate"
        return "proxy"  # default: "setting this up for someone else"

    def handle_practice_name(self, session_id: str, raw_input: str) -> dict:
        """
        Parse practice name from Q1 input (FR-008, FR-009).
        Extracts city/state if present without asking separately.
        """
        from ..onboarding_repository import onboarding_repo
        logs = []

        raw = raw_input.strip()
        city = None
        state = None

        match = _CITY_STATE_RE.search(raw)
        if match:
            city = match.group(1).strip()
            state = match.group(2).upper()
            practice_name = raw[: match.start()].strip().rstrip(",").strip()
            logs.append(self._log(f"Practice name parsed — '{practice_name}' (city: {city}, state: {state})"))
        else:
            practice_name = raw
            logs.append(self._log(f"Practice name set — '{practice_name}'"))

        state_updates: dict = {"practice_name": practice_name}
        if city:
            state_updates["city"] = city
        if state:
            state_updates["state"] = state

        session = onboarding_repo.get_session_by_id(session_id)
        current_state = session.get("state_json", {}) if session else {}
        current_state.update(state_updates)

        onboarding_repo.patch_session(
            session_id,
            practice_name=practice_name,
            phase=3,  # advance to OPEN_PROMPT
            state_json=current_state,
        )

        return {
            "practice_name": practice_name,
            "city": city,
            "state": state,
            "verbose_log": logs,
        }

    def handle_magic_link_request(self, session_id: str, email: str) -> dict:
        """
        Issue a magic link for the session (FR-008b, FR-008c).
        Demo: returns raw token + prints to console.
        """
        from ..onboarding_repository import onboarding_repo
        link = onboarding_repo.create_magic_link(session_id, email)
        raw_token = link["raw_token"]
        expires_at = link["expires_at"]

        # Demo delivery: print to console
        print(
            f"\n[MAGIC LINK] Email: {email}\n"
            f"  Resume URL: /onboarding?magic_token={raw_token}\n"
            f"  Expires: {expires_at}\n"
        )

        log = self._log(f"Magic link issued to {email} — expires {expires_at[:10]}")
        return {
            "sent": True,
            "email": email,
            "expires_at": expires_at,
            "magic_token": raw_token,
            "verbose_log": [log],
        }

    def handle_open_prompt(self, session_id: str, text: str) -> dict:
        """
        Process the Q2 open prompt (FR-010 through FR-015).
        Routes to PracticeBuilderAgent for free-text or URL parsing.
        """
        from ..onboarding_repository import onboarding_repo
        from .practice_builder_agent import PracticeBuilderAgent

        logs = []
        builder = PracticeBuilderAgent()

        # Detect URL (FR-012)
        url_match = re.search(r"https?://\S+", text)
        if url_match:
            url = url_match.group(0)
            logs.append(self._log(f"URL detected in open prompt — routing to web scraper: {url[:60]}"))
            extracted = builder.parse_url(url)
        else:
            logs.append(self._log("Free-text open prompt received — parsing practice context"))
            extracted = builder.parse_free_text(text)

        # Merge extracted fields into session state
        session = onboarding_repo.get_session_by_id(session_id)
        current_state = session.get("state_json", {}) if session else {}
        current_state.update(extracted)

        onboarding_repo.patch_session(session_id, state_json=current_state)
        logs.append(self._log(f"Practice context updated — {len(extracted)} fields extracted"))

        return {"extracted_fields": extracted, "verbose_log": logs}

    def handle_go_live(self, session_id: str) -> dict:
        """
        Replace event: create live Clinic + Resource records from confirmed entities.
        Archive Harmony demo. Return role-appropriate first_action_targets (FR-028 to FR-033).
        """
        from ..onboarding_repository import onboarding_repo
        from ..repository import _get_conn

        logs = []
        session = onboarding_repo.get_session_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        practice_name = session.get("practice_name") or "New Practice"
        persona_role = session.get("persona_role") or "owner"

        logs.append(self._log("Replace triggered — archiving Harmony demo"))

        # Archive demo clinic
        try:
            with _get_conn() as conn:
                conn.execute(
                    "UPDATE clinics SET is_active=0 WHERE name LIKE '%Harmony%'"
                )
        except Exception as e:
            logs.append(self._log(f"Demo archive skipped — {e}"))

        # Create live Clinic record
        clinic_id = str(uuid4())
        state_json = session.get("state_json", {})

        try:
            with _get_conn() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO clinics
                       (id, name, address, phone, email, timezone, color_hex, is_active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        clinic_id,
                        practice_name,
                        state_json.get("address", ""),
                        state_json.get("phone", ""),
                        session.get("email_anchor", ""),
                        "America/Los_Angeles",
                        "#6C63FF",
                    ),
                )
        except Exception as e:
            logs.append(self._log(f"Clinic creation error — {e}"))

        logs.append(self._log(f"Clinic '{practice_name}' created — id={clinic_id[:8]}"))

        # Write confirmed entities to live resources
        confirmed = onboarding_repo.get_confirmed_entities(session_id)
        providers_written = 0
        rooms_written = 0

        for entity in confirmed:
            fields = entity.get("extracted_fields", {})
            entity_type = entity.get("entity_type", "")

            if entity_type == "provider":
                try:
                    resource_id = str(uuid4())
                    import json as _json
                    with _get_conn() as conn:
                        conn.execute(
                            """INSERT OR IGNORE INTO resources
                               (id, type, name, hard_skills, attributes, availability_windows, clinic_id)
                               VALUES (?, 'Vet', ?, ?, ?, '[]', ?)""",
                            (
                                resource_id,
                                fields.get("name", "Unknown Vet"),
                                _json.dumps(["general"]),
                                fields.get("role", "DVM"),
                                clinic_id,
                            ),
                        )
                    providers_written += 1
                except Exception:
                    pass

            elif entity_type == "room":
                try:
                    resource_id = str(uuid4())
                    with _get_conn() as conn:
                        conn.execute(
                            """INSERT OR IGNORE INTO resources
                               (id, type, name, hard_skills, attributes, availability_windows, clinic_id)
                               VALUES (?, 'Room', ?, '[]', ?, '[]', ?)""",
                            (
                                resource_id,
                                fields.get("name", "Exam Room"),
                                "exam_room",
                                clinic_id,
                            ),
                        )
                    rooms_written += 1
                except Exception:
                    pass

        if providers_written:
            logs.append(self._log(f"{providers_written} provider(s) written to live DB"))
        if rooms_written:
            logs.append(self._log(f"{rooms_written} room(s) written to live DB"))

        # Advance session to LIVE phase
        onboarding_repo.patch_session(session_id, phase=6)

        first_action_targets = self._get_first_action_targets(persona_role)
        logs.append(self._log(f"First-action targets set for role={persona_role}"))

        return {
            "clinic_id": clinic_id,
            "practice_name": practice_name,
            "first_action_targets": first_action_targets,
            "verbose_log": logs,
        }

    def handle_post_replace_intro(self, session_id: str, persona_role: str) -> dict:
        """
        Post-Replace boundary statement (FR-037).
        Proactively introduces Vera's professional identity before any operational description.
        """
        logs = []
        message = (
            f"I'm your Chief of Staff. Not a veterinarian. Not your attorney. "
            f"Clinical decisions stay with your licensed DVMs — that's non-negotiable and exactly as it should be. "
            f"What I will do is make sure your practice runs like it should: "
            f"schedules filled, follow-ups sent, nothing falling through the cracks. "
            f"Let's get {self._get_first_action_targets(persona_role)[0].lower()} taken care of first."
        )
        log = self._log("Post-Replace boundary statement delivered")
        logs.append(log)
        return {"message": message, "verbose_log": logs}

    def handle_activation(self, session_id: str, booking_id: str) -> dict:
        """
        Record activation event — first real client appointment booked (FR-033).
        """
        from ..onboarding_repository import onboarding_repo
        result = onboarding_repo.set_activation(session_id, booking_id)
        log = self._log(f"Activation recorded — first real appointment booked (booking={booking_id[:8]})")
        return {**result, "verbose_log": [log]}

    def handle_session_resume(self, raw_token: str) -> dict:
        """
        Resume session from magic link token (FR-035, FR-036).
        Returns session + human-readable summary.
        """
        from ..onboarding_repository import onboarding_repo
        session = onboarding_repo.consume_magic_link(raw_token)
        if session is None:
            return {"error": "invalid_or_expired"}

        # Build state summary for Vera's greeting
        state = session.get("state_json", {})
        practice_name = session.get("practice_name") or "your practice"
        phase_names = {0: "welcome", 1: "demo", 2: "pivot", 3: "open prompt",
                       4: "document upload", 5: "replace", 6: "live"}
        phase_label = phase_names.get(session.get("phase", 0), "onboarding")

        parts = [f"Practice: {practice_name}"]
        if state.get("providers"):
            parts.append(f"{len(state['providers'])} provider(s)")
        if state.get("rooms"):
            parts.append(f"{len(state['rooms'])} room(s)")

        state_summary = " · ".join(parts) + f" · Stopped at {phase_label}"

        # Issue new session token (new cookie)
        new_session = onboarding_repo.patch_session(session["id"], updated_at=datetime.utcnow().isoformat())

        log = self._log(f"Session resumed via magic link — {phase_label} restored for '{practice_name}'")
        return {
            **session,
            "state_summary": state_summary,
            "verbose_log": [log],
        }
