"""Settings contract: neutral defaults, env loading, required secret."""
import pytest

from cos_identity import IdentitySettings


def test_neutral_defaults():
    s = IdentitySettings(jwt_secret="s")
    assert s.default_locale == "en-US"
    assert s.default_timezone == "UTC"
    assert s.schema_name == "cos_identity"
    assert s.app_role == "cos_identity_app"
    assert s.auth_role == "cos_identity_auth"
    assert s.provider == "fake"
    assert s.seed_superuser_email is None


def test_from_env_requires_secret():
    with pytest.raises(ValueError):
        IdentitySettings.from_env(env={})


def test_from_env_reads_prefixed_vars():
    s = IdentitySettings.from_env(env={
        "COS_IDENTITY_JWT_SECRET": "abc",
        "COS_IDENTITY_ACCESS_TOKEN_TTL_MINUTES": "60",
        "COS_IDENTITY_DEFAULT_LOCALE": "es-MX",
        "COS_IDENTITY_SEED_SUPERUSER_EMAIL": "admin@example.com",
    })
    assert s.jwt_secret == "abc"
    assert s.access_token_ttl_minutes == 60
    assert s.default_locale == "es-MX"  # a CONSUMER may override; the default stays neutral
    assert s.seed_superuser_email == "admin@example.com"


def test_accept_invite_url():
    s = IdentitySettings(jwt_secret="s", app_base_url="https://app.example.com/", accept_invite_path="/accept")
    assert s.accept_invite_url("inv-1") == "https://app.example.com/accept?invitation_id=inv-1"


def test_frozen_and_overrides():
    s = IdentitySettings(jwt_secret="s")
    s2 = s.with_overrides(default_timezone="America/New_York")
    assert s.default_timezone == "UTC"
    assert s2.default_timezone == "America/New_York"
