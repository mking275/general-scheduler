"""Phase A verification — T008 migration (SC-007) + T009 household read path."""
import pytest

from backend.models import ContactIdentifier, HouseholdContact
from backend.relationship import migrate_households as mh
from backend.relationship.migrate_households import MigrationError
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC_MIG = "clinic-mig-a"
CLINIC_READ = "clinic-read-a"


# --------------------------------------------------------------------------- #
#  T008 — migration: 100% link preservation, loud abort on a broken link
# --------------------------------------------------------------------------- #
def test_t008_migration_preserves_all_links(repo):
    corpus = build_corpus(clinic_id=CLINIC_MIG)
    owners = corpus.to_flat_owners()

    # SQLite -> PG hydration helper: the migration then reads a Postgres source.
    n = mh.hydrate_sqlite_owners_to_pg(repo.engine, owners, CLINIC_MIG)
    assert n == len(owners)
    read_back = mh.read_flat_owners(repo.engine, CLINIC_MIG)
    prior_links = sum(len(o["patient_ids"]) for o in read_back)
    distinct_patients = len({p for o in read_back for p in o["patient_ids"]})

    report = mh.migrate(repo, CLINIC_MIG)
    assert report.ok
    # SC-007: zero orphaned pets, zero lost contacts
    assert repo.count_patient_links(CLINIC_MIG) == prior_links
    assert repo.count_distinct_linked_patients(CLINIC_MIG) == distinct_patients
    assert report.patient_links_created == prior_links
    assert report.contacts_created == len(owners)


def test_t008_broken_link_aborts_loudly(repo, monkeypatch):
    corpus = build_corpus(clinic_id=CLINIC_MIG + "-broken")
    clinic = CLINIC_MIG + "-broken"
    owners = corpus.to_flat_owners()

    # Deliberately drop one patient link mid-migration -> post < prior.
    real = repo.create_patient_link
    state = {"dropped": False}

    def flaky(model):
        if not state["dropped"]:
            state["dropped"] = True     # silently "lose" the first link
            return {}
        return real(model)

    monkeypatch.setattr(repo, "create_patient_link", flaky)
    with pytest.raises(MigrationError) as exc:
        mh.migrate(repo, clinic, owners=owners)
    assert "link-preservation FAILED" in str(exc.value)


# --------------------------------------------------------------------------- #
#  T009 — household read path (identity structure only, NO medical)
# --------------------------------------------------------------------------- #
def test_t009_two_coowners_resolve_same_household_all_pets(repo):
    corpus = build_corpus(clinic_id=CLINIC_READ)
    corpus.seed_into_repo(repo)

    # Alvarez: Jane (5551110001) + Tom (5551110002), 3 pets (Rex, Bella, Buddy).
    from_jane = repo.resolve_household_by_identifier(CLINIC_READ, "phone", "5551110002")
    # (5551110002 is Tom's own line -> single household)
    assert len(from_jane) == 1
    hh_id = from_jane[0]["household_id"]

    # Jane's shared line reaches >1 household (privacy case) — never collapsed.
    shared = repo.resolve_household_by_identifier(CLINIC_READ, "phone", "5551110001")
    assert len(shared) == 2
    alvarez = next(h for h in shared if h["household_id"] == hh_id)
    # both co-owners + all three pets visible from the household
    assert {c["display_name"] for c in alvarez["contacts"]} == {"Jane Alvarez", "Tom Alvarez"}
    assert {p["name"] for p in alvarez["patients"]} == {"Rex", "Bella", "Buddy"}


def test_t009_add_authorized_contact_no_duplicate_household(repo):
    corpus = build_corpus(clinic_id=CLINIC_READ + "-add")
    clinic = CLINIC_READ + "-add"
    corpus.seed_into_repo(repo)
    proj = repo.resolve_household_by_identifier(clinic, "phone", "5551110002")[0]
    hh_id = proj["household_id"]
    before = len(repo.get_contacts_for_household(hh_id))

    # add an authorized caller to the SAME household
    repo.create_contact(HouseholdContact(
        clinic_id=clinic, household_id=hh_id, pims_client_id="9999",
        entity_ref="client:ezyvet_c9999", display_name="Aunt May",
        household_role="authorized_caller",
    ))
    repo.create_identifier(ContactIdentifier(
        party_id=repo.get_contacts_for_household(hh_id)[-1]["id"], clinic_id=clinic,
        id_type="phone", value_normalized="5558887777", value_raw="+15558887777",
    ))
    proj2 = repo.resolve_household_by_identifier(clinic, "phone", "5558887777")[0]
    assert proj2["household_id"] == hh_id                 # same household, no new one
    assert len(repo.get_contacts_for_household(hh_id)) == before + 1


def test_t009_no_clinical_field_at_resolution(repo):
    corpus = build_corpus(clinic_id=CLINIC_READ + "-clin")
    clinic = CLINIC_READ + "-clin"
    corpus.seed_into_repo(repo)
    proj = repo.resolve_household_by_identifier(clinic, "phone", "5551110004")[0]
    # only identity-structure keys are present — no clinical/financial payload
    allowed_patient_keys = {"patient_id", "entity_ref", "name", "status"}
    for p in proj["patients"]:
        assert set(p.keys()) <= allowed_patient_keys
    blob = str(proj).lower()
    for banned in ("diagnos", "medication", "vaccin", "invoice", "balance", "lab_result"):
        assert banned not in blob
