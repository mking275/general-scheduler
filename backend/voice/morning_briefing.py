"""Feature 010 — Vera Voice: T034 morning-briefing overnight rollup (FR-025).

A **derived view** (not a table; data-model "Morning Briefing Entry") over
``call_session`` joined to ``escalation_event`` + ``refill_request_draft`` for
the overnight window. Each row projects the call outcome + flagged follow-ups
(callbacks owed, pending refill drafts awaiting vet action, escalations) into the
clinic's existing briefing surface, delivered via the **reused ``sms_gateway``
outbound leg** (same seam warm-transfer's callback promise uses).

This is the owner/staff-facing surface where recovered after-hours call value —
and anything needing human follow-up the next morning — becomes visible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

# Escalation outcomes that still owe the caller a human call-back the next morning.
_CALLBACK_OUTCOMES = {"no_answer", "fallback_er_directory", "voicemail_callback"}


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _enum_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _parse_ts(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(str(ts))
    except ValueError:
        return None


@dataclass
class BriefingRow:
    call_session_id: str
    inbound_number: Optional[str]
    call_outcome: Optional[str]           # descriptive label
    containment_flag: bool                # the containment metric source
    cost_usd: Optional[float]
    escalations: int = 0                  # count of escalation_events
    escalation_triggers: list = field(default_factory=list)
    callback_owed: bool = False           # a human still owes the caller a call-back
    refill_drafts_pending: int = 0        # draft_vet_review awaiting the vet

    @property
    def needs_follow_up(self) -> bool:
        return self.callback_owed or self.refill_drafts_pending > 0 or self.escalations > 0


@dataclass
class Briefing:
    clinic_id: str
    rows: list[BriefingRow] = field(default_factory=list)

    @property
    def total_calls(self) -> int:
        return len(self.rows)

    @property
    def contained(self) -> int:
        return sum(1 for r in self.rows if r.containment_flag)

    @property
    def escalations(self) -> int:
        return sum(r.escalations for r in self.rows)

    @property
    def pending_refills(self) -> int:
        return sum(r.refill_drafts_pending for r in self.rows)

    @property
    def callbacks_owed(self) -> int:
        return sum(1 for r in self.rows if r.callback_owed)


class MorningBriefing:
    def __init__(self, repo, sms_gateway=None):
        self.repo = repo
        self.sms_gateway = sms_gateway

    # --- the rollup query ---------------------------------------------- #
    def build(self, clinic_id: str, since: Any = None, until: Any = None) -> Briefing:
        """Project the overnight window into briefing rows. ``since``/``until``
        may be ISO strings or datetimes; both are optional (default: all)."""
        since_dt, until_dt = _parse_ts(since), _parse_ts(until)
        briefing = Briefing(clinic_id=clinic_id)

        for sess in self.repo.list_call_sessions(clinic_id):
            started = _parse_ts(_get(sess, "started_at"))
            if since_dt and started and started < since_dt:
                continue
            if until_dt and started and started > until_dt:
                continue

            sid = _get(sess, "id")
            escalations = self.repo.get_escalation_events(sid)
            refills = self.repo.get_refill_drafts(sid)
            pending = sum(1 for r in refills
                          if _get(r, "status") == "draft_vet_review")
            callback = any(_enum_str(_get(e, "transfer_outcome")) in _CALLBACK_OUTCOMES
                           for e in escalations)

            briefing.rows.append(BriefingRow(
                call_session_id=sid,
                inbound_number=_get(sess, "inbound_number"),
                call_outcome=_enum_str(_get(sess, "call_outcome")),
                containment_flag=bool(_get(sess, "containment_flag", False)),
                cost_usd=_get(sess, "cost_usd"),
                escalations=len(escalations),
                escalation_triggers=[_enum_str(_get(e, "trigger")) for e in escalations],
                callback_owed=callback,
                refill_drafts_pending=pending,
            ))
        return briefing

    # --- render + deliver (reused sms_gateway outbound leg) ------------- #
    @staticmethod
    def render(briefing: Briefing) -> str:
        lines = [
            f"Goldsmith after-hours briefing — {briefing.total_calls} call(s) overnight.",
            f"Contained without a person: {briefing.contained}/{briefing.total_calls}. "
            f"Escalations: {briefing.escalations}. "
            f"Call-backs owed: {briefing.callbacks_owed}. "
            f"Refill drafts awaiting your review: {briefing.pending_refills}.",
        ]
        for r in briefing.rows:
            tags = []
            if r.escalations:
                tags.append(f"escalated({','.join(t for t in r.escalation_triggers if t)})")
            if r.callback_owed:
                tags.append("call-back owed")
            if r.refill_drafts_pending:
                tags.append(f"{r.refill_drafts_pending} refill draft(s)")
            cost = f"${r.cost_usd}" if r.cost_usd is not None else "$-"
            suffix = f" — {'; '.join(tags)}" if tags else ""
            lines.append(f"  • {r.inbound_number or '?'}: {r.call_outcome or 'in-progress'} "
                         f"({cost}){suffix}")
        return "\n".join(lines)

    def deliver(self, clinic_id: str, to: str, since: Any = None,
                until: Any = None) -> dict:
        """Build + render + push to the briefing surface via the sms_gateway seam."""
        briefing = self.build(clinic_id, since=since, until=until)
        body = self.render(briefing)
        result = None
        if self.sms_gateway is not None:
            result = self.sms_gateway.send_sms(to, body)
        return {"briefing": briefing, "body": body, "delivery": result}
