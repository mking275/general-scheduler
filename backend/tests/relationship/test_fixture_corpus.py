"""T007 verify: the dirty corpus contains each pattern + a scoring answer key."""
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus


def test_t007_contains_each_dirty_pattern():
    c = build_corpus()
    ak = c.answer_key

    # >=1 phone shared across two households (cross-household multi-match)
    shared = [k for k, v in ak["phone_lookups"].items()
              if v["match_kind"] == "multi" and not v["is_duplicate"]]
    assert shared, "no cross-household shared phone"
    # the shared phone's two parties live in different households
    parties = {p.party_id: p for p in c.contacts}
    for ph in shared:
        hks = {parties[pid].household_key for pid in ak["phone_lookups"][ph]["party_ids"]}
        assert len(hks) >= 2

    # >=1 surname collision
    assert ak["surname_collisions"]
    coll = ak["surname_collisions"][0]
    hks = {parties[pid].household_key for pid in coll["party_ids"]}
    assert len(hks) >= 2, "surname collision must span >1 household"

    # >=1 PIMS name-edit pair (same stable id, changed display name)
    assert ak["name_edits"]
    ne = ak["name_edits"][0]
    assert ne["old"] != ne["new"] and ne["stable_ref"].startswith("client:ezyvet_c")

    # >=1 duplicate owner record
    assert ak["duplicate_groups"] and len(ak["duplicate_groups"][0]) == 2

    # ex-spouse shared-history pair
    assert ak["ex_spouse_pairs"] and ak["ex_spouse_pairs"][0]["shared_patient"] == "Shadow"

    # deceased pet
    dec = ak["deceased_pets"]
    assert dec
    deceased_ids = {d["patient_id"] for d in dec}
    assert all(p.status == "deceased" for p in c.patients if p.patient_id in deceased_ids)


def test_t007_answer_key_marks_single_vs_multi_vs_duplicate():
    ak = build_corpus().answer_key
    # every phone lookup is classified so a false-positive auto-ID is detectable
    for ph, v in ak["phone_lookups"].items():
        assert v["match_kind"] in ("single", "multi", "none")
    assert ak["single_match_phones"] and ak["multi_match_phones"]
    # the duplicate is BOTH multi-match AND flagged duplicate
    dup_group = set(ak["duplicate_groups"][0])
    dup_phone = [k for k, v in ak["phone_lookups"].items() if v["is_duplicate"]][0]
    assert set(ak["phone_lookups"][dup_phone]["party_ids"]) == dup_group


def test_t007_deterministic():
    a = build_corpus().household_ref("alvarez")
    b = build_corpus().household_ref("alvarez")
    assert a == b and a.startswith("household:vah_")


def test_t007_seed_into_repo(repo):
    c = build_corpus(clinic_id="clinic-t007")
    c.seed_into_repo(repo)
    # the shared phone returns the FULL candidate set from the index (no LIMIT 1)
    rows = repo.find_identifiers("clinic-t007", "phone", "5551110001")
    assert len(rows) == 2
    # a single-match phone returns exactly one
    assert len(repo.find_identifiers("clinic-t007", "phone", "5551110002")) == 1


def test_t007_flat_owner_projection():
    owners = build_corpus().to_flat_owners()
    assert len(owners) == 9                      # one per contact
    assert all("phone" in o and "patient_ids" in o for o in owners)
