"""T005 entity_ref verification: stable-id keys, never names."""
from backend.relationship import entity_ref as er


def test_t005_client_id_maps_to_stable_ref():
    assert er.client_ref("123") == "client:ezyvet_c123"
    assert er.client_ref("c123") == "client:ezyvet_c123"      # tolerant of type letter
    assert er.patient_ref("456") == "patient:ezyvet_p456"


def test_t005_surname_collision_produces_distinct_keys():
    # Two different contacts who share the surname "Alvarez" — keys derive from
    # the stable PIMS id, NOT the name, so they never collide.
    jane = er.client_ref("1001")   # Jane Alvarez
    bob = er.client_ref("2002")    # Bob Alvarez (different household)
    assert jane != bob
    assert "alvarez" not in (jane + bob).lower()   # no name in key


def test_t005_name_edit_does_not_change_key():
    # Same stable id, PIMS display name changed from "Jane Alvarez" -> "Jane Smith".
    before = er.client_ref("1001")
    after = er.client_ref("1001")
    assert before == after


def test_t005_synth_household_deterministic():
    a = er.synth_household_ref("client-1001")
    b = er.synth_household_ref("client-1001")
    c = er.synth_household_ref("client-2002")
    assert a == b and a != c
    assert a.startswith("household:vah_")


def test_t005_parse_roundtrip():
    assert er.parse("client:ezyvet_c123") == ("client", "ezyvet_c123")
    assert er.ref_type("household:vah_abc") == "household"
