"""Feature 009 — T034 partial-delivery detection + owner-facing GapNotice.

Partial-delivery detection against the §5 scope (the T010 ``ScopeCheck`` record):
any category the vendor was asked for but did **not** fully deliver
(``absent``/``short``) is a gap. On a detected gap the service produces an
owner-facing, **paper-trail-ready** ``GapNotice`` (the text of the reply to the
vendor), and the practice **proceeds on the delivered data** but is **not** marked
complete — it moves to the first-class ``partial`` state (never
``shadow_ready``-as-complete), and its reconciliation report lists the outstanding
gap (FR-030/031).

A later delta delivery closes the gap (``delta.py``, T035).
"""
from __future__ import annotations

import os
from typing import Optional

import yaml

from backend.envelope.state_machine import StateMachine
from backend.models import GapNotice, PracticeState

_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "envelope", "section5_scope.yaml",
)

_OFF_PATH = {PracticeState.PARTIAL.value, PracticeState.HELD.value,
             PracticeState.BLOCKED.value}


class GapNoticeService:
    def __init__(self, repo, config_path: Optional[str] = None):
        self.repo = repo
        with open(config_path or _CONFIG) as f:
            cfg = yaml.safe_load(f)
        self.labels: dict[str, str] = {c["key"]: c.get("label", c["key"])
                                       for c in cfg["categories"]}

    # ------------------------------------------------------------------ #
    #  detection — the §5 scope-vs-request diff (from the ScopeCheck record)
    # ------------------------------------------------------------------ #
    def detect(self, practice_id: str) -> list[str]:
        """Categories that are ``absent`` or ``short`` vs the §5 scope."""
        sc = self.repo.get_scope_check(practice_id)
        if not sc:
            return []
        dispositions = sc.get("dispositions") or {}
        return sorted(k for k, v in dispositions.items() if v in ("absent", "short"))

    # ------------------------------------------------------------------ #
    #  detect_and_notice — the owner-facing paper trail + partial hold
    # ------------------------------------------------------------------ #
    def detect_and_notice(self, clinic_id: str, practice_id: str,
                          state_machine: Optional[StateMachine] = None
                          ) -> Optional[GapNotice]:
        missing = self.detect(practice_id)
        if not missing:
            return None
        notice = GapNotice(
            clinic_id=clinic_id, practice_id=practice_id,
            missing_categories=missing, text=self._compose(practice_id, missing),
        )
        self.repo.append_gap_notice(notice)

        # proceed on delivered data, but NOT complete: hold at `partial`.
        sm = state_machine or StateMachine(self.repo)
        current = sm.current_state(practice_id)
        if current not in _OFF_PATH:
            sm.mark_partial(
                practice_id, clinic_id=clinic_id,
                reason=f"partial delivery: {', '.join(missing)} not fully delivered",
            )
        return notice

    # ------------------------------------------------------------------ #
    #  the paper-trail-ready vendor-reply text (owner-facing)
    # ------------------------------------------------------------------ #
    def _compose(self, practice_id: str, missing: list[str]) -> str:
        lines = [
            f"Re: §5 data-copy delivery for practice {practice_id}",
            "",
            "On reconciling the delivered export against the §5 requested scope, "
            "the following requested categories were not fully delivered:",
        ]
        for cat in missing:
            lines.append(f"  - {self.labels.get(cat, cat)} ({cat})")
        lines += [
            "",
            "We are proceeding on the data that WAS delivered; this practice is "
            "recorded as a PARTIAL delivery and is not marked complete until the "
            "outstanding categories arrive. Please deliver the missing categories "
            "at your earliest convenience so we can close the gap.",
        ]
        return "\n".join(lines)
