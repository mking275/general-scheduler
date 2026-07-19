"""Feature 009 — T022 per-practice quality assessment + T023 quality-floor block.

Quantifies dirty-data signals (shared phones, duplicate owners, deceased pets,
malformed/orphaned records) into a **usable-record share** (FR-014), driven by
``config/envelope/quality_thresholds.yaml``. Rules flagged ``unusable: true``
count a record against the usable share; rules flagged ``unusable: false`` are
quantified/itemized but do not by themselves make a record unusable.

T023 — the **>20% quality-floor block**: a practice whose unusable share exceeds
``unusable_floor`` (0.20) is ``below_floor`` and is moved to ``held`` out of
shadow-mode with the gap itemized (FR-015; the strategy-board kill-criterion),
enforced as the state-machine ``quality_floor`` guard. ``enforce_floor`` is the
one call that holds a below-floor practice; a practice under the floor is not
blocked on this criterion.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import yaml

from backend.models import QualityAssessment

_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "envelope", "quality_thresholds.yaml",
)


def _norm_name(first: Any, last: Any) -> str:
    s = f"{first or ''} {last or ''}".lower()
    return "".join(ch for ch in s if ch.isalnum() or ch.isspace()).strip()


class QualityAssessor:
    def __init__(self, repo, config_path: Optional[str] = None):
        self.repo = repo
        with open(config_path or _CONFIG) as f:
            self.cfg = yaml.safe_load(f)
        self.floor: float = float(self.cfg.get("unusable_floor", 0.20))
        self.rules: dict[str, dict] = self.cfg.get("dirty_data_rules", {})

    def _unusable(self, rule: str) -> bool:
        return bool(self.rules.get(rule, {}).get("unusable", False))

    # ------------------------------------------------------------------ #
    def assess(self, clinic_id: str, practice_id: str) -> QualityAssessment:
        clients = self.repo.list_canonical_records(practice_id, category="client")
        patients = self.repo.list_canonical_records(practice_id, category="patient")

        # index client source-ids for the orphan check
        client_ids = {str(c["payload"].get("source_id", c["source_id"])) for c in clients}

        # ---- duplicate owners + shared phones -------------------------- #
        # group clients by (normalized name, phone): a group >1 with a real name
        # is a duplicate set (the extras are unusable copies); a shared phone
        # across DISTINCT names is a collision (a signal, not unusable).
        by_name_phone: dict[tuple, list[str]] = {}
        by_phone_names: dict[str, set] = {}
        unusable: set[str] = set()
        for c in clients:
            payload = c["payload"]
            name = _norm_name(payload.get("first_name"), payload.get("last_name"))
            phone = str(payload.get("phone") or "").strip()
            if phone:
                by_phone_names.setdefault(phone, set()).add(name)
            if name and phone:
                by_name_phone.setdefault((name, phone), []).append(c["entity_ref"])

        duplicate_owners = 0
        for (_name, _phone), refs in by_name_phone.items():
            if len(refs) > 1:
                duplicate_owners += len(refs) - 1
                if self._unusable("duplicate_owners"):
                    unusable.update(refs[1:])          # keep the first, drop copies

        shared_phones = sum(1 for phone, names in by_phone_names.items()
                            if len({n for n in names if n}) > 1)

        # ---- malformed clients (blank required name) ------------------- #
        malformed = 0
        for c in clients:
            payload = c["payload"]
            if not _norm_name(payload.get("first_name"), payload.get("last_name")):
                malformed += 1
                if self._unusable("malformed"):
                    unusable.add(c["entity_ref"])

        # ---- deceased pets + orphaned refs ----------------------------- #
        deceased_pets = 0
        orphaned_refs = 0
        for p in patients:
            payload = p["payload"]
            if str(payload.get("status", "")).lower() == "deceased":
                deceased_pets += 1
                if self._unusable("deceased_pets"):
                    unusable.add(p["entity_ref"])
            owner = payload.get("client_source_id")
            if owner is not None and str(owner) not in client_ids:
                orphaned_refs += 1
                if self._unusable("orphaned_refs"):
                    unusable.add(p["entity_ref"])

        total_sampled = len(clients) + len(patients)
        usable_share = round(1.0 - len(unusable) / max(total_sampled, 1), 4)
        below_floor = (1.0 - usable_share) > self.floor

        itemized_gap = [
            {"pattern": "duplicate_owners", "count": duplicate_owners,
             "unusable": self._unusable("duplicate_owners")},
            {"pattern": "shared_phones", "count": shared_phones,
             "unusable": self._unusable("shared_phones")},
            {"pattern": "deceased_pets", "count": deceased_pets,
             "unusable": self._unusable("deceased_pets")},
            {"pattern": "orphaned_refs", "count": orphaned_refs,
             "unusable": self._unusable("orphaned_refs")},
            {"pattern": "malformed", "count": malformed,
             "unusable": self._unusable("malformed")},
        ]

        qa = QualityAssessment(
            clinic_id=clinic_id, practice_id=practice_id,
            shared_phones=shared_phones, duplicate_owners=duplicate_owners,
            deceased_pets=deceased_pets, orphaned_refs=orphaned_refs,
            malformed=malformed, usable_record_share=usable_share,
            below_floor=below_floor, itemized_gap=itemized_gap,
        )
        self.repo.create_quality_assessment(qa)
        return qa


def enforce_floor(state_machine, practice_id: str, assessment: QualityAssessment,
                  clinic_id: Optional[str] = None) -> bool:
    """T023 — a below-floor practice is moved to ``held`` out of shadow-mode with
    its gap itemized (the state-machine ``quality_floor`` guard independently
    blocks any advance past ``normalized``). Returns True iff the practice was
    held. A practice under the floor is untouched here."""
    if not assessment.below_floor:
        return False
    if state_machine.current_state(practice_id) != "held":
        state_machine.hold(
            practice_id,
            reason=f"quality floor breached (usable={assessment.usable_record_share})",
            clinic_id=clinic_id,
        )
    return True
