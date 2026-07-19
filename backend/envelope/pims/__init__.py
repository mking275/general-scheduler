"""Feature 009 — pluggable per-PIMS ingest adapters behind ``PimsAdapterPort``.

ezyVet is the first and only adapter this cycle; the orchestration/verification/
reconciliation core imports ``pims.port`` only — never a concrete adapter
(PIMS-agnostic; FR-027).
"""
