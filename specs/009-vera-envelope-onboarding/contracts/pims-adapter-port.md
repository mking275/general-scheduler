# Contract — `PimsAdapterPort` (the second-adapter seam)

**Feature**: 009 Vera Envelope Onboarding · **Task**: T017 · **Status**: frozen
**Module**: `backend/envelope/pims/port.py` · **First implementer**: `backend/envelope/pims/ezyvet_adapter.py` (T015)

This freezes the stable ingest port a per-PIMS adapter implements so a future
PIMS plugs in **without a core fork** (FR-027). The orchestration / verification
/ reconciliation core depends on **this port only** — never a concrete adapter.

---

## 1. The port

```python
@runtime_checkable
class PimsAdapterPort(Protocol):
    pims: str                     # e.g. "ezyvet"
    variant: str                  # e.g. "complete_v1"

    def profile(self, raw_export: Any) -> FormatProfile: ...
    def normalize(self, profile: FormatProfile, raw_export: Any) -> NormalizeResult: ...
```

`raw_export` is opaque to the core: ZIP-of-CSVs bytes, an object exposing
`raw_bytes()`, or (sim) an in-memory export with an `.entities` mapping. Each
adapter knows how to read its own PIMS export; the core passes it through.

---

## 2. `profile(raw_export) -> FormatProfile`

Discovery. MUST enumerate what arrived and identify the variant, and MUST NOT
normalize. Returns a `FormatProfile` (`backend/models.py`) with:

| Field | Meaning |
|---|---|
| `entities` | `{entity_name: record_count}` |
| `encodings` | `{entity_name: encoding}` (e.g. `"utf-8"`) |
| `referential_relationships` | `[{"from": entity, "column": fk_col, "to": entity}]` |
| `export_variant` | the identified variant, or `"unrecognized_variant"` |
| `unmapped_flags` | source entities the adapter's map cannot map (flagged, not dropped — FR-007) |

A corrupt/truncated/unreadable export MUST raise `DiscoveryError` and write **no**
profile (FR-033) — the profile-before-normalize guard then keeps it out of the
canonical store.

---

## 3. `normalize(profile, raw_export) -> NormalizeResult`

Canonical load. Returns:

```python
@dataclass
class NormalizeResult:
    records: list[CanonicalRecord]          # canonical entities + lineage
    unmapped_entities: list[str]            # source entities with no mapping
    unmapped_fields: list[dict]             # source fields with no canonical target
```

Each `CanonicalRecord` (`backend/models.py`) carries:

| Field | Contract |
|---|---|
| `practice_id` | the practice being loaded |
| `category` | canonical category — one of `provider, client, household, patient, appointment, invoice, ledger, payment, ar_balance, inventory, communication, attachment, product_service` |
| `entity_ref` | **NON-NULLABLE** lineage key, `{type}:{stable_id}` (see §4) |
| `source_id` | **NON-NULLABLE** stable key back to the source export row |
| `payload` | mapped canonical fields |
| `unmapped_fields` | per-record source fields with no canonical target (never dropped — FR-008/T020) |

Normalization MUST be **deterministic**: the same `raw_export` yields the same
`source_id`/`entity_ref` keys every run (idempotency spine, FR-010).

---

## 4. `entity_ref` lineage keys (reuse `backend/relationship/entity_ref.py` verbatim)

`{type}:{stable_id}` — **names never in the key**. The client/patient/staff keys
are the byte-identical handoff to 011:

| Category | Builder | Shape |
|---|---|---|
| `client` | `client_ref(id)` | `client:ezyvet_c{digits}` |
| `patient` | `patient_ref(id)` | `patient:ezyvet_p{digits}` |
| `provider` | `staff_ref(id)` | `staff:{id}` |
| financial / other | synthesized | `{category}:ezyvet_{source_id}` |

`household:vah_*` keys are synthesized downstream by identity bootstrap (T028),
not by the adapter.

---

## 5. Registry

```python
register_adapter(pims: str, variant: str, factory: Callable[..., PimsAdapterPort]) -> None
resolve_adapter(pims: str, variant: str, **kwargs) -> PimsAdapterPort
```

- Keyed by `(pims.lower(), variant.lower())`.
- `resolve_adapter` falls back to the `(pims, "*")` wildcard when no exact-variant
  adapter is registered — a known PIMS whose delivered variant is unrecognized
  resolves to the base adapter, which flags the variant for adapter work rather
  than force-fitting (US7 edge case).
- Adapters self-register on import; a bootstrap (`pims.load_adapters()`) imports
  them. The core never imports a concrete adapter module.

---

## 6. Conformance

The T015 ezyVet adapter conforms to exactly this shape:
`isinstance(EzyVetAdapter(...), PimsAdapterPort)` is true, it registers under
`("ezyvet", "complete_v1")` and `("ezyvet", "*")`, and it is reachable from the
orchestration core **only** through `resolve_adapter`.
