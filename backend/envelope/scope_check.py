"""Feature 009 — T010 scope-vs-request against the §5 category list.

On receipt, produce a record comparing delivered contents against the six §5
enumerated categories (``config/envelope/section5_scope.yaml``) — patient/client,
scheduling, invoicing/billing/payments, communications, attachments/imaging,
configuration — enumerating which are ``present`` / ``absent`` / ``short``. This
is a **manifest** read (entity names + row counts, like a shipping label), not
normalization; it runs *before* the counsel gate and feeds partial-delivery
detection (US8/T034).

Disposition per category:
  * ``present`` — at least one of the category's source entities arrived with rows;
  * ``short``   — some source entities arrived with rows but others arrived empty
                  (a partial-within-category signal);
  * ``absent``  — none of the category's source entities arrived with rows.
"""
from __future__ import annotations

import io
import os
import zipfile
from typing import Any, Optional

import yaml

from backend.models import ScopeCheck

_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "envelope", "section5_scope.yaml",
)


def manifest_from_zip(data: bytes) -> dict[str, int]:
    """Read the delivery manifest — entity name -> row count — from the ZIP
    member headers. A manifest read, NOT a parse/normalization."""
    manifest: dict[str, int] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if not name.endswith(".csv"):
                continue
            text = zf.read(name).decode("utf-8", errors="ignore")
            lines = [ln for ln in text.splitlines() if ln != ""]
            manifest[name[:-4]] = max(len(lines) - 1, 0)
    return manifest


def manifest_from_export(export: Any) -> dict[str, int]:
    """Entity -> row count from an in-memory export (the sim fixture)."""
    return {name: len(rows) for name, rows in export.entities.items()}


class ScopeChecker:
    def __init__(self, repo, config_path: Optional[str] = None):
        self.repo = repo
        with open(config_path or _CONFIG) as f:
            cfg = yaml.safe_load(f)
        self.categories = cfg["categories"]

    def _disposition(self, source_entities: list[str], manifest: dict[str, int]) -> str:
        nonempty = [e for e in source_entities if manifest.get(e, 0) > 0]
        empty = [e for e in source_entities if e in manifest and manifest[e] == 0]
        if nonempty and empty:
            return "short"
        if nonempty:
            return "present"
        return "absent"

    def check(self, clinic_id: str, practice_id: str, practice_database_id: str,
              manifest: dict[str, int]) -> ScopeCheck:
        """Compute + persist the scope-vs-request record for one database."""
        dispositions = {
            cat["key"]: self._disposition(cat["source_entities"], manifest)
            for cat in self.categories
        }
        sc = ScopeCheck(clinic_id=clinic_id, practice_id=practice_id,
                        practice_database_id=practice_database_id,
                        dispositions=dispositions)
        self.repo.create_scope_check(sc)
        return sc

    def absent_categories(self, dispositions: dict[str, str]) -> list[str]:
        return sorted(k for k, v in dispositions.items() if v == "absent")

    def short_categories(self, dispositions: dict[str, str]) -> list[str]:
        return sorted(k for k, v in dispositions.items() if v == "short")
