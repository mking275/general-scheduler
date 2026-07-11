"""T034 — migration verification harness (SC-007 = 100% link preservation).

Re-runs the T008 migration over a flat-owner set derived from the T007 dirty
corpus, through the SQLite->PG hydration path, and asserts link preservation:
zero orphaned pets, zero lost contacts. A seeded broken-link case must make the
migration abort LOUDLY (MigrationError), never drop silently.
"""
import pytest

from backend.relationship import migrate_households as mh
from backend.relationship.migrate_households import MigrationError
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-t034-migration"


def _flat(clinic):
    return build_corpus(clinic_id=clinic).to_flat_owners()


# --------------------------------------------------------------------------- #
#  100% link preservation over the hydration path
# --------------------------------------------------------------------------- #
def test_t034_hydration_path_preserves_all_links(repo):
    owners = _flat(CLINIC)
    # hydration: SQLite staging -> Postgres flat_owner_source; migration reads PG
    n = mh.hydrate_sqlite_owners_to_pg(repo.engine, owners, CLINIC)
    assert n == len(owners)

    read_back = mh.read_flat_owners(repo.engine, CLINIC)
    prior_links = sum(len(o["patient_ids"]) for o in read_back)
    distinct_patients = len({p for o in read_back for p in o["patient_ids"]})

    report = mh.migrate(repo, CLINIC)                          # reads the PG source
    assert report.ok
    # SC-007: link count and distinct-patient count both preserved exactly
    assert repo.count_patient_links(CLINIC) == prior_links
    assert repo.count_distinct_linked_patients(CLINIC) == distinct_patients
    assert report.patient_links_created == prior_links
    assert report.households_created == len(owners)
    assert report.contacts_created == len(owners)


def test_t034_every_source_patient_is_linked(repo):
    owners = _flat(CLINIC + "-p")
    mh.hydrate_sqlite_owners_to_pg(repo.engine, owners, CLINIC + "-p")
    report = mh.migrate(repo, CLINIC + "-p")
    source_patients = {p for o in owners for p in o["patient_ids"]}
    assert report.distinct_source_patients == len(source_patients)
    assert repo.count_distinct_linked_patients(CLINIC + "-p") == len(source_patients)


# --------------------------------------------------------------------------- #
#  Seeded broken link -> loud abort (never silent drop)
# --------------------------------------------------------------------------- #
def test_t034_broken_link_aborts_loudly(repo, monkeypatch):
    clinic = CLINIC + "-broken"
    owners = _flat(clinic)

    real = repo.create_patient_link
    state = {"dropped": False}

    def flaky(model):
        if not state["dropped"]:
            state["dropped"] = True            # silently "lose" the first link
            return {}
        return real(model)

    monkeypatch.setattr(repo, "create_patient_link", flaky)
    with pytest.raises(MigrationError) as exc:
        mh.migrate(repo, clinic, owners=owners)
    assert "link-preservation FAILED" in str(exc.value)
    # the migration raised — it did NOT silently under-link
