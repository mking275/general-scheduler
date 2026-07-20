"""Token mint/verify: round-trip, type assertion, issuer, clock skew, tamper."""
import pytest

from cos_identity import IdentitySettings
from cos_identity.tokens import (
    ACCESS,
    REFRESH,
    TokenError,
    hash_refresh_token,
    mint_access_token,
    mint_refresh_token,
    verify_token,
)

SETTINGS = IdentitySettings(jwt_secret="unit-test-secret-value-1234567890")


def _access(**over):
    kw = dict(
        user_id="u-1", email="a@example.com", role="agent", customer_id="tenant-1",
        customer_name="Tenant One", customer_role="member", cs_admin_scope=["tenant-1"],
        entitlements={"module_x": True},
    )
    kw.update(over)
    return mint_access_token(SETTINGS, **kw)


def test_access_round_trip_carries_all_claims():
    claims = verify_token(SETTINGS, _access(), expected_type=ACCESS)
    assert claims["sub"] == "u-1"
    assert claims["role"] == "agent"
    assert claims["customer_id"] == "tenant-1"
    assert claims["customer_name"] == "Tenant One"
    assert claims["customer_role"] == "member"
    assert claims["cs_admin_scope"] == ["tenant-1"]
    assert claims["entitlements"] == {"module_x": True}
    assert claims["token_type"] == ACCESS
    assert claims["iss"] == "cos-identity"


def test_entitlements_are_opaque_passthrough():
    payload = {"nested": {"a": [1, 2]}, "flag": False}
    claims = verify_token(SETTINGS, _access(entitlements=payload), expected_type=ACCESS)
    assert claims["entitlements"] == payload


def test_refresh_round_trip_and_jti():
    token, jti = mint_refresh_token(SETTINGS, user_id="u-1")
    claims = verify_token(SETTINGS, token, expected_type=REFRESH)
    assert claims["token_type"] == REFRESH
    assert claims["jti"] == jti


def test_wrong_type_rejected():
    access = _access()
    with pytest.raises(TokenError):
        verify_token(SETTINGS, access, expected_type=REFRESH)
    refresh, _ = mint_refresh_token(SETTINGS, user_id="u-1")
    with pytest.raises(TokenError):
        verify_token(SETTINGS, refresh, expected_type=ACCESS)


def test_tampered_and_wrong_secret_rejected():
    token = _access()
    with pytest.raises(TokenError):
        verify_token(SETTINGS, token + "x", expected_type=ACCESS)
    other = SETTINGS.with_overrides(jwt_secret="a-different-secret-value-000000")
    with pytest.raises(TokenError):
        verify_token(other, token, expected_type=ACCESS)


def test_wrong_issuer_rejected():
    minted = _access()
    other = SETTINGS.with_overrides(token_issuer="someone-else")
    with pytest.raises(TokenError):
        verify_token(other, minted, expected_type=ACCESS)


def test_clock_skew_within_leeway_ok_but_expired_rejected():
    # ttl -1 min → exp is 60s in the past; leeway 30s → expired.
    expired = SETTINGS.with_overrides(access_token_ttl_minutes=-1, clock_skew_leeway_seconds=30)
    with pytest.raises(TokenError):
        verify_token(expired, _skew_token(expired), expected_type=ACCESS)
    # Small negative skew inside the leeway window still verifies.
    skewed = SETTINGS.with_overrides(access_token_ttl_minutes=0, clock_skew_leeway_seconds=120)
    verify_token(skewed, _skew_token(skewed), expected_type=ACCESS)


def _skew_token(settings):
    return mint_access_token(
        settings, user_id="u", email="a@b.com", role="viewer", customer_id="t",
        customer_name="T", customer_role="member",
    )


def test_hash_refresh_token_is_stable_sha256():
    h1 = hash_refresh_token("abc")
    h2 = hash_refresh_token("abc")
    assert h1 == h2 and len(h1) == 64
    assert hash_refresh_token("abd") != h1
