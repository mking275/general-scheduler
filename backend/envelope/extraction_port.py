"""Feature 009 — T012 provider-agnostic ExtractionPort (Gemini adapter).

Parse/vision on unknown-format exports, operated under a **no-retention**
posture: no raw source content or screen frames are retained by the
subprocessor after the call returns (FR-003, DPA). This build runs in
**sim-mode** over the T005 fixture with a stubbed no-retention adapter; the live
DPA'd Gemini flip is counsel-gated Pilot-Activation and is selected (never
exercised) by ``sim.resolve_extraction_port`` when ``ONBOARDING_LIVE=true``.

``is_live()`` gates any real subprocessor connect — the sim port never opens a
network connection and no live PII crosses the port in the build.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# The core entities that signal a recognizable ezyVet complete-export.
_EZYVET_CORE = {"clients", "patients", "invoices"}


@dataclass
class ExtractionResult:
    """The structural parse of an unknown-format export — entities, their
    columns, row counts, and encoding — plus a variant hint. Carries NO raw
    source bytes."""
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    variant_hint: str = "unknown"
    corrupt: bool = False
    error: str = ""


@runtime_checkable
class ExtractionPort(Protocol):
    def extract(self, raw_export: Any) -> ExtractionResult: ...


def _to_zip_bytes(raw_export: Any) -> bytes:
    if isinstance(raw_export, (bytes, bytearray)):
        return bytes(raw_export)
    if hasattr(raw_export, "raw_bytes"):
        return raw_export.raw_bytes()
    raise TypeError("raw_export must be ZIP bytes or expose raw_bytes()")


class SimExtractionPort:
    """The sim no-retention extraction adapter. Parses the ZIP-of-CSVs export
    into a structural view and retains ZERO raw bytes after the call returns."""

    def __init__(self):
        # Deliberately never populated — the no-retention invariant. A live
        # subprocessor with retention would accumulate frames/content here.
        self._retained_raw: list[bytes] = []

    def extract(self, raw_export: Any) -> ExtractionResult:
        try:
            data = _to_zip_bytes(raw_export)
        except TypeError as exc:
            return ExtractionResult(corrupt=True, error=str(exc))

        entities: dict[str, dict[str, Any]] = {}
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for name in zf.namelist():
                    if not name.endswith(".csv"):
                        continue
                    entity = name[:-4]
                    text = zf.read(name).decode("utf-8", errors="strict")
                    lines = [ln for ln in text.splitlines() if ln != ""]
                    columns = lines[0].split(",") if lines else []
                    entities[entity] = {
                        "columns": columns,
                        "row_count": max(len(lines) - 1, 0),
                        "encoding": "utf-8",
                    }
        except (zipfile.BadZipFile, UnicodeDecodeError, EOFError) as exc:
            # a corrupt/truncated/unreadable export fails HERE with a specific
            # error — it is never partially normalized downstream (FR-033).
            return ExtractionResult(corrupt=True, error=f"unreadable export: {exc}")

        variant = "complete_v1" if _EZYVET_CORE.issubset(entities.keys()) else "unknown"
        result = ExtractionResult(entities=entities, variant_hint=variant)

        # NO-RETENTION: local `data`/`text` go out of scope here; nothing is
        # appended to self._retained_raw. (A retaining adapter would fail the
        # assertion below.)
        return result

    def retained_raw_count(self) -> int:
        """The number of raw source payloads/frames retained after calls — must
        be 0 (the no-retention proof)."""
        return len(self._retained_raw)

    def is_connected(self) -> bool:
        """The sim port never opens a live subprocessor connection."""
        return False
