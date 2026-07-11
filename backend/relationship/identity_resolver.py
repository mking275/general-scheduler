"""Feature 011 — T010/T011/T013 identity resolver (contract R1/R2).

**The `LIMIT 1` kill.** ``resolve()`` returns the FULL candidate set for a
normalized identifier and persists an append-only ``identity_resolution_event``
carrying the complete ``candidate_set_json``. ``resolved_single`` — the ONLY
state that permits auto-ID + soft-confirm — is returned **only** on an exact
normalized-phone match to exactly one contact. There is no code path that
reduces a multi-match to a single record (SC-003).

Identity-safe disambiguation (R2): an open "name on the account" answer is
matched against the candidate set; it resolves only on exactly one match, and
**candidate names are never read back to the caller**.

Auto-ID gating (T013, US2): auto-greet by name only on ``resolved_single``;
``audit_only`` disabled-safe mode records the event but always returns the
neutral prompt (used until the real ezyVet-export identity audit clears); an
``ambiguous_multi`` / ``unmatched`` result yields the neutral
"May I get the name on the account?".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from backend.models import IdentityResolutionEvent, ResolutionOutcome

IdType = Literal["phone", "email", "name"]

# Exact-match confidence by identifier type. Only an exact phone match (1.0) can
# ever auto-ID; email/name are surfaced for staff-reviewed disambiguation only.
_SCORE = {"phone": 1.0, "email": 0.9, "name": 0.5}


@dataclass
class Candidate:
    party_id: str
    household_id: str
    entity_ref: str            # client:ezyvet_c*
    display_name: str          # MATCHING only — never spoken until confirmed
    score: float               # exact-phone == 1.0

    def to_audit(self) -> dict:
        # Persisted candidate set carries STABLE IDs only — no name in the log.
        return {"party_id": self.party_id, "household_id": self.household_id,
                "entity_ref": self.entity_ref, "score": self.score}


@dataclass
class ResolutionResult:
    candidates: list[Candidate]                 # FULL set — 0..n, never reduced
    outcome: ResolutionOutcome
    id_type: IdType = "phone"
    identifier_normalized: str = ""
    confirmed_party_id: Optional[str] = None
    event_id: Optional[str] = None

    @property
    def match_count(self) -> int:
        return len(self.candidates)

    @property
    def is_shared_line(self) -> bool:
        return self.match_count > 1


def normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_email(raw: str) -> str:
    return str(raw).strip().lower()


def _normalize_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum() or ch.isspace()).strip()


class IdentityResolver:
    def __init__(self, repo, audit_only: bool = False):
        self.repo = repo
        # Disabled-safe: until the real ezyVet-export identity audit clears,
        # auto-ID stays off and every caller gets the neutral prompt (US2
        # degrades, never breaks).
        self.audit_only = audit_only

    # ------------------------------------------------------------------ #
    #  R1 — resolve (full candidate set, never LIMIT 1)
    # ------------------------------------------------------------------ #
    def resolve(self, clinic_id: str, identifier: str, id_type: IdType = "phone",
                channel: str = "voice") -> ResolutionResult:
        if id_type == "phone":
            norm = normalize_phone(identifier)
            candidates = self._candidates_from_identifier(clinic_id, "phone", norm)
        elif id_type == "email":
            norm = normalize_email(identifier)
            candidates = self._candidates_from_identifier(clinic_id, "email", norm)
        else:  # name — never a lookup index; surfaced for disambiguation only
            norm = _normalize_name(identifier)
            candidates = self._candidates_from_name(clinic_id, norm)

        match_count = len(candidates)
        # resolved_single is reserved for an EXACT normalized-phone single match.
        # Any email/name/fuzzy or multi match -> ambiguous_multi (neutral prompt);
        # zero -> unmatched. A multi-match can NEVER collapse to one record.
        if match_count == 0:
            outcome = ResolutionOutcome.UNMATCHED
        elif id_type == "phone" and match_count == 1:
            outcome = ResolutionOutcome.RESOLVED_SINGLE
        else:
            outcome = ResolutionOutcome.AMBIGUOUS_MULTI

        event = IdentityResolutionEvent(
            clinic_id=clinic_id, channel=channel,
            inbound_identifier_normalized=norm, identifier_type=id_type,
            candidate_set_json=[c.to_audit() for c in candidates],
            match_count=match_count, outcome=outcome.value,
        )
        self.repo.append_resolution_event(event)

        return ResolutionResult(candidates=candidates, outcome=outcome,
                                id_type=id_type, identifier_normalized=norm,
                                event_id=event.id)

    def _candidates_from_identifier(self, clinic_id: str, id_type: str,
                                    value_normalized: str) -> list[Candidate]:
        rows = self.repo.find_identifiers(clinic_id, id_type, value_normalized)
        out: dict[str, Candidate] = {}
        for row in rows:
            contact = self.repo.get_contact(row["party_id"])
            if not contact:
                continue
            pid = contact["id"]
            if pid in out:
                continue
            out[pid] = Candidate(
                party_id=pid, household_id=contact["household_id"],
                entity_ref=contact["entity_ref"], display_name=contact["display_name"],
                score=_SCORE[id_type],
            )
        return list(out.values())

    def _candidates_from_name(self, clinic_id: str, norm_name: str) -> list[Candidate]:
        if not norm_name:
            return []
        toks = set(norm_name.split())
        out: list[Candidate] = []
        for contact in self.repo.list_contacts(clinic_id):
            cand_name = _normalize_name(contact["display_name"])
            if norm_name == cand_name or (toks & set(cand_name.split())):
                out.append(Candidate(
                    party_id=contact["id"], household_id=contact["household_id"],
                    entity_ref=contact["entity_ref"], display_name=contact["display_name"],
                    score=_SCORE["name"],
                ))
        return out

    # ------------------------------------------------------------------ #
    #  R2 — disambiguate (open name; never enumerate candidate names)
    # ------------------------------------------------------------------ #
    def disambiguate(self, result: ResolutionResult, spoken_name: str,
                     clinic_id: str, channel: str = "voice") -> ResolutionResult:
        answer = _normalize_name(spoken_name)
        matches: list[Candidate] = []
        if answer:
            ans_tokens = set(answer.split())
            for c in result.candidates:
                cand = _normalize_name(c.display_name)
                if not cand:
                    continue
                if answer == cand or answer in cand or (ans_tokens & set(cand.split())):
                    matches.append(c)

        if len(matches) == 1:
            confirmed = matches[0]
            outcome = ResolutionOutcome.RESOLVED_SINGLE
            confirmed_party = confirmed.party_id
        else:
            # 0 or >1 matches -> stays unresolved; no names ever read back.
            outcome = (ResolutionOutcome.UNMATCHED if not result.candidates
                       else ResolutionOutcome.AMBIGUOUS_MULTI)
            confirmed_party = None

        # append-only: every resolution step is logged (audit spine)
        event = IdentityResolutionEvent(
            clinic_id=clinic_id, channel=channel,
            inbound_identifier_normalized=result.identifier_normalized,
            identifier_type=result.id_type,
            candidate_set_json=[c.to_audit() for c in result.candidates],
            match_count=result.match_count,
            outcome=("soft_confirmed" if confirmed_party else outcome.value),
            confirmed_party_id=confirmed_party,
        )
        self.repo.append_resolution_event(event)

        return ResolutionResult(candidates=result.candidates, outcome=outcome,
                                id_type=result.id_type,
                                identifier_normalized=result.identifier_normalized,
                                confirmed_party_id=confirmed_party, event_id=event.id)

    # ------------------------------------------------------------------ #
    #  T013 — auto-ID + soft-confirm gating (US2)
    # ------------------------------------------------------------------ #
    NEUTRAL_PROMPT = "May I get the name on the account?"

    def auto_id_response(self, result: ResolutionResult) -> dict:
        """Render the caller-facing opening. Auto-greet by name ONLY on an
        (non-audit-only) ``resolved_single``; everything else is neutral and
        reveals no name."""
        if result.outcome == ResolutionOutcome.RESOLVED_SINGLE and not self.audit_only:
            party_id = result.confirmed_party_id or result.candidates[0].party_id
            name = next((c.display_name for c in result.candidates
                         if c.party_id == party_id), "")
            return {"mode": "soft_confirm_by_name", "party_id": party_id,
                    "display_name": name, "authorizes_change": False}
        return {"mode": "neutral_prompt", "prompt": self.NEUTRAL_PROMPT,
                "authorizes_change": False}

    def neutral_reopen(self) -> dict:
        """A rejected soft-confirm re-opens neutrally, revealing nothing tied to
        the dropped identity (FR-007/009)."""
        return {"mode": "neutral_prompt", "prompt": self.NEUTRAL_PROMPT,
                "authorizes_change": False}
