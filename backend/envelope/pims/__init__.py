"""Feature 009 — pluggable per-PIMS ingest adapters behind ``PimsAdapterPort``.

ezyVet is the first and only adapter this cycle; the orchestration/verification/
reconciliation core imports ``pims.port`` only — never a concrete adapter
(PIMS-agnostic; FR-027). A bootstrap (batch orchestration, or a test) calls
``load_adapters()`` to register the shipped adapters; the concrete adapter module
is imported there, not by the core.
"""


def load_adapters() -> None:
    """Import + register every shipped adapter. Idempotent. Called by a
    bootstrap/orchestrator, never by the PIMS-agnostic core."""
    from backend.envelope.pims import ezyvet_adapter  # noqa: F401  (registers on import)
