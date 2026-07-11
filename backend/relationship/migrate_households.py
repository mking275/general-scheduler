"""Feature 011 — T008 flat ``owners`` -> household migration (SC-007).

One-time forward migration lifting the flat single-owner model into the
household / contact / identifier / patient-link model.

**Source (M1 / research D8)**: the production run reads the **platform Postgres
``owners`` table** (hydrated by VP-1/009 envelope ingestion from ezyVet). The
demo SQLite ``owners`` is demo-track only. The dev/test path reads a synthetic
flat-owner fixture through a small **SQLite -> PG hydration helper**
(``hydrate_sqlite_owners_to_pg``) so the *same* migration code runs over a
Postgres source in both paths — there is no divergent SQLite read path.

Per ``owners`` row -> one ``household`` (synthesized ``household:vah_*``) + one
``household_contact`` (``co_owner``) + ``contact_identifier`` rows for its phone
and email; per owner->patient link -> one ``patient_household_link``.

**Hard assertion gate**: post-migration link count must equal the prior
owner->patient link count and every source patient must be linked. A mismatch
raises ``MigrationError`` — the migration **fails loudly, never silently drops**
(SC-007 = 100% preservation).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.models import (
    ContactIdentifier, Household, HouseholdContact, HouseholdRole, PatientHouseholdLink,
)
from backend.relationship import entity_ref as er

# The Postgres staging table the migration reads (stands in for the platform
# ``owners`` table in the production path).
SOURCE_TABLE = "flat_owner_source"


class MigrationError(RuntimeError):
    """Raised when link preservation is violated — aborts loudly (SC-007)."""


@dataclass
class MigrationReport:
    households_created: int
    contacts_created: int
    identifiers_created: int
    patient_links_created: int
    prior_link_count: int
    distinct_source_patients: int
    ok: bool


def _normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


# --------------------------------------------------------------------------- #
#  SQLite -> PG hydration helper (dev/test): the same migration then reads PG.
# --------------------------------------------------------------------------- #
def hydrate_sqlite_owners_to_pg(pg_engine: Engine, owners: Iterable[dict],
                                clinic_id: str) -> int:
    """Load a synthetic flat-owner fixture into an in-memory SQLite ``owners``
    table, then copy it into the Postgres ``flat_owner_source`` staging table so
    the migration reads a Postgres source (research D8). Returns owner-row count.

    Each owner dict: ``{owner_id, name, phone, email, patient_ids: [...]}``.
    """
    import json
    import sqlite3

    # 1) stage in SQLite (the demo-track shape)
    lite = sqlite3.connect(":memory:")
    lite.execute(
        "CREATE TABLE owners (owner_id TEXT, name TEXT, phone TEXT, email TEXT, "
        "patient_ids TEXT)"
    )
    rows = list(owners)
    lite.executemany(
        "INSERT INTO owners VALUES (?,?,?,?,?)",
        [(o["owner_id"], o.get("name", ""), o.get("phone", ""), o.get("email", ""),
          json.dumps(o.get("patient_ids", []))) for o in rows],
    )
    lite.commit()

    # 2) copy SQLite -> Postgres staging table (idempotent for the clinic)
    with pg_engine.begin() as conn:
        conn.execute(text(
            f"CREATE TABLE IF NOT EXISTS {SOURCE_TABLE} ("
            "owner_id TEXT, clinic_id TEXT, name TEXT, phone TEXT, email TEXT, "
            "patient_ids JSONB)"
        ))
        conn.execute(text(f"DELETE FROM {SOURCE_TABLE} WHERE clinic_id = :c"),
                     {"c": clinic_id})
        for owner_id, name, phone, email, patient_ids in lite.execute(
                "SELECT owner_id, name, phone, email, patient_ids FROM owners"):
            conn.execute(
                text(f"INSERT INTO {SOURCE_TABLE} "
                     "(owner_id, clinic_id, name, phone, email, patient_ids) "
                     "VALUES (:o, :c, :n, :p, :e, CAST(:pi AS JSONB))"),
                {"o": owner_id, "c": clinic_id, "n": name, "p": phone, "e": email,
                 "pi": patient_ids},
            )
    lite.close()
    return len(rows)


def read_flat_owners(pg_engine: Engine, clinic_id: str) -> list[dict]:
    """Read the flat owner rows from the Postgres source table."""
    import json
    with pg_engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT owner_id, name, phone, email, patient_ids FROM {SOURCE_TABLE} "
                 "WHERE clinic_id = :c ORDER BY owner_id"),
            {"c": clinic_id},
        ).mappings().all()
    out = []
    for r in rows:
        pids = r["patient_ids"]
        if isinstance(pids, str):
            pids = json.loads(pids)
        out.append({"owner_id": r["owner_id"], "name": r["name"], "phone": r["phone"],
                    "email": r["email"], "patient_ids": list(pids or [])})
    return out


# --------------------------------------------------------------------------- #
#  The migration
# --------------------------------------------------------------------------- #
def migrate(repo, clinic_id: str, owners: Optional[list[dict]] = None) -> MigrationReport:
    """Lift the flat owners for ``clinic_id`` into the household model.

    ``owners`` may be passed directly (already read from the PG source); if None
    they are read from the ``flat_owner_source`` staging table.
    """
    if owners is None:
        owners = read_flat_owners(repo.engine, clinic_id)

    # Idempotent forward migration: clear any prior household model for this
    # clinic so a re-run over the persistent Postgres starts clean.
    with repo.engine.begin() as conn:
        for tbl in ("contact_identifier", "patient_household_link",
                    "household_contact", "household"):
            conn.execute(text(f"DELETE FROM {tbl} WHERE clinic_id = :c"), {"c": clinic_id})

    prior_link_count = sum(len(o["patient_ids"]) for o in owners)
    distinct_source_patients = len({pid for o in owners for pid in o["patient_ids"]})

    households = contacts = identifiers = links = 0
    for o in owners:
        owner_id = str(o["owner_id"])
        hh_ref = er.synth_household_ref(f"{clinic_id}:owner:{owner_id}")
        hh = Household(clinic_id=clinic_id, entity_ref=hh_ref,
                       display_name=f"{o.get('name', '')} household".strip(),
                       review_status="confirmed")
        repo.create_household(hh)
        households += 1

        contact = HouseholdContact(
            clinic_id=clinic_id, household_id=hh.id, pims_client_id=owner_id,
            entity_ref=er.client_ref(owner_id), display_name=o.get("name", ""),
            household_role=HouseholdRole.CO_OWNER, active=True,
        )
        repo.create_contact(contact)
        contacts += 1

        if o.get("phone"):
            repo.create_identifier(ContactIdentifier(
                party_id=contact.id, clinic_id=clinic_id, id_type="phone",
                value_normalized=_normalize_phone(o["phone"]), value_raw=str(o["phone"]),
                is_primary=True, source="pims",
            ))
            identifiers += 1
        if o.get("email"):
            repo.create_identifier(ContactIdentifier(
                party_id=contact.id, clinic_id=clinic_id, id_type="email",
                value_normalized=str(o["email"]).strip().lower(), value_raw=str(o["email"]),
                is_primary=True, source="pims",
            ))
            identifiers += 1

        for pid in o["patient_ids"]:
            repo.create_patient_link(PatientHouseholdLink(
                patient_id=str(pid), clinic_id=clinic_id, household_id=hh.id,
                pims_patient_id=str(pid), entity_ref=er.patient_ref(pid), status="active",
            ))
            links += 1

    # ---- hard assertion gate (SC-007: 100% link preservation) -----------
    post_link_count = repo.count_patient_links(clinic_id)
    post_distinct = repo.count_distinct_linked_patients(clinic_id)
    if post_link_count != prior_link_count:
        raise MigrationError(
            f"link-preservation FAILED: migrated {post_link_count} patient_household_link "
            f"rows but expected {prior_link_count} prior owner->patient links "
            f"(orphaned/lost pets — aborting, never silently dropping)."
        )
    if post_distinct != distinct_source_patients:
        raise MigrationError(
            f"patient-preservation FAILED: {post_distinct} distinct migrated patients "
            f"!= {distinct_source_patients} source patients."
        )

    return MigrationReport(
        households_created=households, contacts_created=contacts,
        identifiers_created=identifiers, patient_links_created=links,
        prior_link_count=prior_link_count, distinct_source_patients=distinct_source_patients,
        ok=True,
    )
