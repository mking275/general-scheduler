"""Feature 009 — T013 format discovery → FormatProfile.

Profiles each received database — entities, record counts, encodings, referential
relationships — and identifies the ezyVet export variant, emitting a
machine-readable ``FormatProfile`` per database (FR-005). Uses the T012
``ExtractionPort`` for parse/vision on unknown structure. It is PIMS-agnostic:
it works on an unknown format and names the variant so the orchestrator can
resolve the right adapter.

A corrupt/truncated/unreadable export fails **here** with a specific error and
**no** ``FormatProfile`` is written — so the profile-before-normalize guard keeps
it out of the canonical store (FR-033).
"""
from __future__ import annotations

from typing import Any, Optional

from backend.models import FormatProfile


class DiscoveryError(Exception):
    """Discovery failed on a corrupt/truncated/unreadable export. No
    FormatProfile is written; normalization stays blocked (FR-033)."""


def infer_referential_relationships(
    entity_columns: dict[str, list[str]],
) -> list[dict[str, str]]:
    """Infer FK edges from ``<base>_id`` columns that target another entity.
    A column is a FK when its ``<base>`` differs from the entity's own singular
    and a target entity (``<base>s`` or ``<base>``) exists."""
    rels: list[dict[str, str]] = []
    entities = set(entity_columns.keys())
    for entity, cols in entity_columns.items():
        singular = entity[:-1] if entity.endswith("s") else entity
        for col in cols:
            if not col.endswith("_id"):
                continue
            base = col[:-3]
            if base == singular:
                continue                     # the entity's own primary key
            target = None
            if f"{base}s" in entities:
                target = f"{base}s"
            elif base in entities:
                target = base
            if target and target != entity:
                rels.append({"from": entity, "column": col, "to": target})
    return sorted(rels, key=lambda r: (r["from"], r["column"]))


class FormatDiscovery:
    def __init__(self, repo, extraction_port: Optional[Any] = None):
        self.repo = repo
        if extraction_port is None:
            from backend.envelope.sim import resolve_extraction_port
            extraction_port = resolve_extraction_port()
        self.extraction = extraction_port

    def discover(self, clinic_id: str, practice_id: str, practice_database_id: str,
                 raw_export: Any, persist: bool = True) -> FormatProfile:
        result = self.extraction.extract(raw_export)
        if result.corrupt:
            raise DiscoveryError(
                f"discovery failed for {practice_id}: {result.error}"
            )
        entities = {name: meta["row_count"] for name, meta in result.entities.items()}
        encodings = {name: meta.get("encoding", "utf-8") for name, meta in result.entities.items()}
        entity_columns = {name: meta.get("columns", []) for name, meta in result.entities.items()}
        relationships = infer_referential_relationships(entity_columns)

        profile = FormatProfile(
            clinic_id=clinic_id, practice_id=practice_id,
            practice_database_id=practice_database_id,
            entities=entities, encodings=encodings,
            referential_relationships=relationships,
            export_variant=result.variant_hint,
            unmapped_flags=[],
        )
        if persist:
            self.repo.create_format_profile(profile)
        return profile
