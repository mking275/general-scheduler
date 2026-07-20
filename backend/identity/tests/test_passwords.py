"""Escape-hatch password hashing (bcrypt)."""
import pytest

from cos_identity.passwords import hash_password, verify_password


def test_hash_and_verify_round_trip():
    h = hash_password("correct horse")
    assert h != "correct horse"
    assert verify_password("correct horse", h)
    assert not verify_password("wrong", h)


def test_distinct_salts():
    assert hash_password("same") != hash_password("same")


def test_over_72_bytes_rejected_on_hash():
    with pytest.raises(ValueError):
        hash_password("x" * 73)


def test_verify_handles_garbage_hash():
    assert not verify_password("whatever", "not-a-bcrypt-hash")
