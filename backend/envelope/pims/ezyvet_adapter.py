"""Feature 009 — T015 ezyVet adapter (the first and only adapter this cycle).

Behind ``PimsAdapterPort``: ``profile()`` + ``normalize()`` mapping the ezyVet
complete-export → the canonical practice model + lineage, driven by
``config/envelope/ezyvet_mapping.*.yaml`` (the ``migration_agent.py`` per-source
field-map precedent). Registers in the T007 registry so it resolves through the
port; the orchestration core calls it **only** via the port.

Every emitted ``CanonicalRecord`` carries a NON-NULLABLE ``entity_ref`` (seeded
via ``backend/relationship/entity_ref.py`` for client/patient/staff; synthesized
``{category}:ezyvet_{source_id}`` for the rest) + a ``source_id`` back to the
source export row. Entities/fields the mapping cannot map are **flagged**
(``unmapped_entities`` / ``unmapped_fields``), never silently dropped (FR-007;
T016/T020).
"""
from __future__ import annotations

import os
from typing import Any, Optional

import yaml

from backend.envelope.format_discovery import infer_referential_relationships
from backend.envelope.pims.port import NormalizeResult, register_adapter
from backend.models import CanonicalRecord, FormatProfile
from backend.relationship import entity_ref as eref

_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "config", "envelope",
)

_REF_BUILDERS = {
    "client": eref.client_ref,
    "patient": eref.patient_ref,
    "staff": eref.staff_ref,
}


def _mapping_path(variant: str) -> str:
    return os.path.join(_CONFIG_DIR, f"ezyvet_mapping.{variant}.yaml")


class EzyVetAdapter:
    """PimsAdapterPort implementation for ezyVet complete-exports."""

    pims = "ezyvet"

    def __init__(self, clinic_id: str = "", practice_id: str = "",
                 practice_database_id: str = "", variant: str = "complete_v1",
                 extraction_port: Optional[Any] = None,
                 mapping_path: Optional[str] = None):
        self.clinic_id = clinic_id
        self.practice_id = practice_id
        self.practice_database_id = practice_database_id
        self.variant = variant
        path = mapping_path or _mapping_path(variant)
        if not os.path.exists(path):
            # an unrecognized variant of a known PIMS falls back to the group
            # prior (complete_v1) and is flagged in profile() rather than
            # force-fit with a wrong map (US7 edge case).
            path = _mapping_path("complete_v1")
        with open(path) as f:
            self.mapping = yaml.safe_load(f)
        self._entity_map: dict[str, dict] = self.mapping["entities"]
        # Real deliveries name files <Thing>Export; alias those onto the canonical
        # entity keys so a genuine export is recognised rather than flagged as an
        # unrecognised variant (verified against Coastal Creek, 2026-07-29).
        self._source_files: dict[str, str] = self.mapping.get("source_files", {}) or {}
        for canonical, filename in self._source_files.items():
            if canonical in self._entity_map:
                self._entity_map.setdefault(filename, self._entity_map[canonical])
        if extraction_port is None:
            from backend.envelope.sim import resolve_extraction_port
            extraction_port = resolve_extraction_port()
        self.extraction = extraction_port

    # ------------------------------------------------------------------ #
    #  profile() — the port's discovery half
    # ------------------------------------------------------------------ #
    def profile(self, raw_export: Any) -> FormatProfile:
        result = self.extraction.extract(raw_export)
        if result.corrupt:
            from backend.envelope.format_discovery import DiscoveryError
            raise DiscoveryError(f"ezyVet discovery failed: {result.error}")
        entities = {n: m["row_count"] for n, m in result.entities.items()}
        encodings = {n: m.get("encoding", "utf-8") for n, m in result.entities.items()}
        columns = {n: m.get("columns", []) for n, m in result.entities.items()}
        # entities the mapping cannot map are flagged for adapter work (FR-007)
        unmapped = sorted(n for n in entities if n not in self._entity_map)
        variant = result.variant_hint if result.variant_hint != "unknown" else "unrecognized_variant"
        return FormatProfile(
            clinic_id=self.clinic_id, practice_id=self.practice_id,
            practice_database_id=self.practice_database_id,
            entities=entities, encodings=encodings,
            referential_relationships=infer_referential_relationships(columns),
            export_variant=variant, unmapped_flags=unmapped,
        )

    # ------------------------------------------------------------------ #
    #  normalize() — the port's canonical-load half
    # ------------------------------------------------------------------ #
    def _entity_ref(self, spec: dict, category: str, source_id: str) -> str:
        builder = _REF_BUILDERS.get(spec.get("ref_builder"))
        if builder is not None:
            return builder(source_id)
        return f"{category}:{eref.PIMS_PREFIX}_{source_id}"

    def normalize(self, profile: FormatProfile, raw_export: Any) -> NormalizeResult:
        entities = self._entities(raw_export)
        records: list[CanonicalRecord] = []
        unmapped_fields: list[dict[str, Any]] = []
        _unmapped_agg: dict[tuple, dict[str, Any]] = {}
        unmapped_entities = sorted(n for n in entities if n not in self._entity_map)

        for src_entity, spec in self._entity_map.items():
            rows = entities.get(src_entity)
            if not rows:
                continue
            category = spec["canonical_category"]
            # id_field may be a single column or a LIST of candidates: the
            # synthetic fixture speaks canonical names (client_id) while a real
            # ezyVet delivery speaks its own ("Contact Id"). One mapping serves
            # both rather than forking the variant.
            id_field = spec["id_field"]
            id_candidates = id_field if isinstance(id_field, list) else [id_field]
            field_map: dict[str, str] = spec.get("fields", {})
            for row in rows:
                source_id = ""
                for _cand in id_candidates:
                    source_id = str(row.get(_cand, "") or "").strip()
                    if source_id:
                        break
                if not source_id:
                    # a row with no stable id cannot be lineage-keyed — flag it
                    unmapped_fields.append({"entity": src_entity, "row": row,
                                            "reason": "missing id_field"})
                    continue
                entity_ref = self._entity_ref(spec, category, source_id)
                payload: dict[str, Any] = {}
                rec_unmapped: dict[str, Any] = {}
                for col, val in row.items():
                    if col in field_map:
                        payload[field_map[col]] = val
                    else:
                        rec_unmapped[col] = val
                        # AGGREGATE per (entity, column) — never per row. FR-007
                        # requires knowing WHICH fields are unmapped, not carrying
                        # every row's copy: a real delivery has 74-column exports,
                        # so per-row accumulation built millions of dicts (each
                        # holding a raw value) before a single record was written.
                        # The per-record copy still rides on the record itself.
                        key = (src_entity, col)
                        agg = _unmapped_agg.get(key)
                        if agg is None:
                            _unmapped_agg[key] = {
                                "entity": src_entity, "source_field": col,
                                "row_count": 1, "entity_ref": entity_ref}   # an EXAMPLE ref, not per-row
                        else:
                            agg["row_count"] += 1
                records.append(CanonicalRecord(
                    practice_id=self.practice_id or profile.practice_id,
                    category=category, entity_ref=entity_ref, source_id=source_id,
                    payload=payload, unmapped_fields=rec_unmapped,
                ))
        unmapped_fields.extend(_unmapped_agg.values())
        return NormalizeResult(records=records, unmapped_entities=unmapped_entities,
                               unmapped_fields=unmapped_fields)

    # ------------------------------------------------------------------ #
    #  raw_export -> in-memory entity rows
    # ------------------------------------------------------------------ #
    @staticmethod
    def _entities(raw_export: Any) -> dict[str, list[dict]]:
        if hasattr(raw_export, "entities"):
            return raw_export.entities            # the sim SyntheticExport
        if isinstance(raw_export, dict):
            return raw_export
        # ZIP bytes → parse CSV members into row dicts
        import csv
        import io
        import sys
        import zipfile
        csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
        out: dict[str, list[dict]] = {}
        data = raw_export.raw_bytes() if hasattr(raw_export, "raw_bytes") else raw_export
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if not name.endswith(".csv"):
                    continue
                text = zf.read(name).decode("utf-8")
                # BASENAME, not the nested path: a real delivery ships
                # Contacts/ContactExport.csv while the entity map is keyed
                # by ContactExport. Keying by path silently matched nothing
                # and normalized ZERO records while reporting success.
                out[name.rsplit("/", 1)[-1][:-4]] = list(
                    csv.DictReader(io.StringIO(text)))
        return out


def _factory(**kwargs) -> EzyVetAdapter:
    # the registry passes only what a caller supplies; drop the resolver's
    # variant kwarg collision-safely (EzyVetAdapter accepts it directly)
    return EzyVetAdapter(**kwargs)


# self-register on import (a bootstrap / test imports this module to register it;
# the core never imports it — it resolves through the port registry, FR-027).
register_adapter("ezyvet", "complete_v1", _factory)
register_adapter("ezyvet", "*", _factory)  # unrecognized-variant fallback (US7 edge case)
