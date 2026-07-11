"""Feature 011 — T007 synthetic dirty-data fixture corpus (the red-team's fuel).

A DETERMINISTIC synthetic ezyVet-style corpus that reproduces every dirty
pattern the identity resolver must survive, paired with a ground-truth ANSWER
KEY the audit / red-team harnesses (T014/T031/T032/T034) score against. Because
a false-positive auto-ID on dirty data is a PII leak (not a bug), the answer key
marks every phone lookup as single-match / multi-match and flags the
duplicate/collision/ex-spouse/name-edit/deceased cases — so a wrong auto-ID is
detectable.

Deterministic by construction: the data is hand-authored constants and all
synthesized ``household:vah_*`` keys derive from a fixed seed via
``entity_ref.synth_household_ref`` — so every red-team replay is identical.

Dirty patterns present (each asserted by ``test_fixture_corpus.py``):
  * shared phone across TWO households        (5551110001 -> H_alvarez + H_nguyen)
  * duplicate owner record                    (5551110005 -> two rows, same person)
  * surname collision                         ("Alvarez" spans H_alvarez + H_alvarez2)
  * PIMS name-edit pair                        (c4001: "Samuel Okafor" -> "Sam Okafor")
  * ex-spouse shared-history pair              (c6001 / c7001 shared patient "Shadow")
  * deceased pet                               ("Buddy" in H_alvarez, status=deceased)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.relationship import entity_ref as er

DEFAULT_CLINIC = "clinic-goldsmith"
DEFAULT_SEED = "011-dirty-corpus-v1"


@dataclass
class IdentifierSeed:
    id_type: str            # phone | email
    value_normalized: str
    value_raw: str = ""
    is_primary: bool = False


@dataclass
class ContactSeed:
    party_id: str
    pims_client_id: str
    display_name: str
    household_key: str      # logical household grouping label
    household_display: str
    household_role: str = "co_owner"
    active: bool = True
    identifiers: list[IdentifierSeed] = field(default_factory=list)

    @property
    def entity_ref(self) -> str:
        return er.client_ref(self.pims_client_id)


@dataclass
class PatientSeed:
    patient_id: str
    pims_patient_id: str
    name: str
    species: str
    household_key: str
    status: str = "active"

    @property
    def entity_ref(self) -> str:
        return er.patient_ref(self.pims_patient_id)


@dataclass
class Corpus:
    clinic_id: str
    seed: str
    contacts: list[ContactSeed]
    patients: list[PatientSeed]
    answer_key: dict[str, Any]

    def household_ref(self, household_key: str) -> str:
        return er.synth_household_ref(f"{self.seed}:{self.clinic_id}:{household_key}")

    def _household_db_id(self, household_key: str) -> str:
        return f"hh-{self.clinic_id}-{household_key}"

    # ---------------------------------------------------------------- #
    #  Seed the household model directly into a HouseholdRepository
    #  (resolver/review tests don't need to run the migration first).
    #  Idempotent: the clinic's corpus rows are reset first so a re-run over
    #  the persistent Postgres never collides on a PK / UNIQUE entity_ref.
    # ---------------------------------------------------------------- #
    def reset_clinic(self, repo) -> None:
        from sqlalchemy import text
        with repo.engine.begin() as conn:
            for tbl in ("contact_identifier", "patient_household_link",
                        "household_contact", "household"):
                conn.execute(text(f"DELETE FROM {tbl} WHERE clinic_id = :c"),
                             {"c": self.clinic_id})

    def seed_into_repo(self, repo) -> None:
        from backend.models import (
            ContactIdentifier, Household, HouseholdContact, PatientHouseholdLink,
        )
        clinic = self.clinic_id
        self.reset_clinic(repo)
        # households (one per distinct household_key)
        hh_ids: dict[str, str] = {}
        for key in dict.fromkeys(c.household_key for c in self.contacts):
            ref = self.household_ref(key)
            hid = self._household_db_id(key)
            hh_ids[key] = hid
            display = next(c.household_display for c in self.contacts if c.household_key == key)
            repo.create_household(Household(
                id=hid, clinic_id=clinic, entity_ref=ref, display_name=display,
            ))
        # contacts + identifiers
        for c in self.contacts:
            repo.create_contact(HouseholdContact(
                id=c.party_id, clinic_id=clinic, household_id=hh_ids[c.household_key],
                pims_client_id=c.pims_client_id, entity_ref=c.entity_ref,
                display_name=c.display_name, household_role=c.household_role,
                active=c.active,
            ))
            for idf in c.identifiers:
                repo.create_identifier(ContactIdentifier(
                    party_id=c.party_id, clinic_id=clinic, id_type=idf.id_type,
                    value_normalized=idf.value_normalized, value_raw=idf.value_raw or idf.value_normalized,
                    is_primary=idf.is_primary, source="pims",
                ))
        # patient links
        for p in self.patients:
            repo.create_patient_link(PatientHouseholdLink(
                patient_id=p.patient_id, clinic_id=clinic,
                household_id=hh_ids[p.household_key], pims_patient_id=p.pims_patient_id,
                entity_ref=p.entity_ref, status=p.status, display_name=p.name,
            ))

    # ---------------------------------------------------------------- #
    #  Flat-owner projection (pre-migration `owners` shape) — feeds the
    #  migration test (T008/T034). One owner row per contact.
    # ---------------------------------------------------------------- #
    def to_flat_owners(self) -> list[dict]:
        owners = []
        for c in self.contacts:
            phone = next((i.value_normalized for i in c.identifiers if i.id_type == "phone"), "")
            email = next((i.value_normalized for i in c.identifiers if i.id_type == "email"), "")
            patient_ids = [p.patient_id for p in self.patients if p.household_key == c.household_key]
            owners.append({
                "owner_id": c.pims_client_id,
                "name": c.display_name,
                "phone": phone,
                "email": email,
                "patient_ids": patient_ids,
            })
        return owners


def _phone(n: str) -> IdentifierSeed:
    return IdentifierSeed(id_type="phone", value_normalized=n, value_raw=f"+1{n}", is_primary=True)


def _email(e: str) -> IdentifierSeed:
    return IdentifierSeed(id_type="email", value_normalized=e.lower(), value_raw=e)


def build_corpus(clinic_id: str = DEFAULT_CLINIC, seed: str = DEFAULT_SEED) -> Corpus:
    # Namespace the party / patient PKs by clinic so distinct clinics can
    # coexist in the persistent Postgres without a global-PK collision. The
    # answer key is built from the SAME namespaced ids, so it stays consistent.
    def pid(n: str) -> str:
        return f"party-{clinic_id}-c{n}"

    def patid(n: str) -> str:
        return f"pat-{clinic_id}-p{n}"

    contacts: list[ContactSeed] = [
        # --- H_alvarez: shared line (privacy case) + deceased pet -----------
        ContactSeed(pid("1001"), "1001", "Jane Alvarez", "alvarez", "Alvarez household",
                    identifiers=[_phone("5551110001"), _email("jane.alvarez@example.com")]),
        ContactSeed(pid("1002"), "1002", "Tom Alvarez", "alvarez", "Alvarez household",
                    household_role="authorized_caller",
                    identifiers=[_phone("5551110002")]),
        # --- H_nguyen: shares 5551110001 with H_alvarez (cross-household) ---
        ContactSeed(pid("2001"), "2001", "Lan Nguyen", "nguyen", "Nguyen household",
                    identifiers=[_phone("5551110001"), _email("lan.nguyen@example.com")]),
        # --- H_alvarez2: SURNAME collision with H_alvarez, own phone -------
        ContactSeed(pid("3001"), "3001", "Carlos Alvarez", "alvarez2", "Alvarez household (2)",
                    identifiers=[_phone("5551110003"), _email("carlos.alvarez@example.com")]),
        # --- H_okafor: PIMS name-edit (Samuel -> Sam), stable id c4001 ------
        ContactSeed(pid("4001"), "4001", "Sam Okafor", "okafor", "Okafor household",
                    identifiers=[_phone("5551110004"), _email("sam.okafor@example.com")]),
        # --- H_dubois_a / H_dubois_b: DUPLICATE owner (same person twice) --
        ContactSeed(pid("5001"), "5001", "Marie Dubois", "dubois_a", "Dubois household",
                    identifiers=[_phone("5551110005"), _email("marie.dubois@example.com")]),
        ContactSeed(pid("5002"), "5002", "Marie Dubois", "dubois_b", "Dubois household (dup)",
                    identifiers=[_phone("5551110005"), _email("marie.dubois@example.com")]),
        # --- H_halvorsen_erik / _nadia: ex-spouse shared-history pair ------
        ContactSeed(pid("6001"), "6001", "Erik Halvorsen", "halvorsen_erik", "Halvorsen household (Erik)",
                    identifiers=[_phone("5551110006"), _email("erik.h@example.com")]),
        ContactSeed(pid("7001"), "7001", "Nadia Halvorsen", "halvorsen_nadia", "Halvorsen household (Nadia)",
                    identifiers=[_phone("5551110007"), _email("nadia.h@example.com")]),
    ]

    patients: list[PatientSeed] = [
        PatientSeed(patid("1"), "1", "Rex", "dog", "alvarez", "active"),
        PatientSeed(patid("2"), "2", "Bella", "cat", "alvarez", "active"),
        PatientSeed(patid("3"), "3", "Buddy", "dog", "alvarez", "deceased"),   # deceased pet
        PatientSeed(patid("4"), "4", "Kiki", "bird", "nguyen", "active"),
        PatientSeed(patid("5"), "5", "Max", "dog", "alvarez2", "active"),
        PatientSeed(patid("6"), "6", "Coco", "rabbit", "okafor", "active"),
        PatientSeed(patid("7"), "7", "Gus", "dog", "dubois_a", "active"),
        PatientSeed(patid("8"), "8", "Gus", "dog", "dubois_b", "active"),      # dup carries a dup pet
        PatientSeed(patid("9"), "9", "Shadow", "dog", "halvorsen_erik", "active"),  # ex-spouse shared history
        PatientSeed(patid("10"), "10", "Luna", "cat", "halvorsen_nadia", "active"),
    ]

    # ---- ground-truth answer key ---------------------------------------
    phone_lookups = {
        "5551110001": {"match_kind": "multi", "party_ids": [pid("1001"), pid("2001")],
                        "is_duplicate": False, "reason": "shared_phone_cross_household"},
        "5551110002": {"match_kind": "single", "party_ids": [pid("1002")],
                        "is_duplicate": False, "reason": "unique"},
        "5551110003": {"match_kind": "single", "party_ids": [pid("3001")],
                        "is_duplicate": False, "reason": "unique"},
        "5551110004": {"match_kind": "single", "party_ids": [pid("4001")],
                        "is_duplicate": False, "reason": "unique"},
        "5551110005": {"match_kind": "multi", "party_ids": [pid("5001"), pid("5002")],
                        "is_duplicate": True, "reason": "duplicate_owner"},
        "5551110006": {"match_kind": "single", "party_ids": [pid("6001")],
                        "is_duplicate": False, "reason": "unique"},
        "5551110007": {"match_kind": "single", "party_ids": [pid("7001")],
                        "is_duplicate": False, "reason": "unique"},
        "5559990000": {"match_kind": "none", "party_ids": [],
                        "is_duplicate": False, "reason": "unmatched"},
    }
    answer_key = {
        "clinic_id": clinic_id,
        "phone_lookups": phone_lookups,
        "single_match_phones": [k for k, v in phone_lookups.items() if v["match_kind"] == "single"],
        "multi_match_phones": [k for k, v in phone_lookups.items() if v["match_kind"] == "multi"],
        "unmatched_phones": [k for k, v in phone_lookups.items() if v["match_kind"] == "none"],
        "duplicate_groups": [[pid("5001"), pid("5002")]],
        "surname_collisions": [
            {"surname": "Alvarez", "party_ids": [pid("1001"), pid("1002"), pid("3001")]},
        ],
        "name_edits": [
            {"party_id": pid("4001"), "old": "Samuel Okafor", "new": "Sam Okafor",
             "stable_ref": er.client_ref("4001")},
        ],
        "ex_spouse_pairs": [
            {"party_ids": [pid("6001"), pid("7001")], "shared_patient": "Shadow"},
        ],
        "deceased_pets": [{"patient": "Buddy", "patient_id": patid("3"), "household_key": "alvarez"}],
        # email lookups must NEVER auto-ID even when they resolve to one party (R1)
        "email_single_but_never_auto_id": ["jane.alvarez@example.com"],
    }

    return Corpus(clinic_id=clinic_id, seed=seed, contacts=contacts,
                  patients=patients, answer_key=answer_key)
