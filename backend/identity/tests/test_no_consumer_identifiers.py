"""SC-005 — the component source carries no consumer-specific identifier.

Greps the package source for a denylist of consumer names, hardcoded infra
identifiers, and non-neutral locale/timezone DEFAULTS. Test files themselves are
excluded (fixtures legitimately mention es-MX/America/Mexico_City as OVERRIDES).
"""
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "cos_identity"

# Plain substrings that must never appear in component source.
DENY_SUBSTRINGS = [
    "fruitscout", "farmagent", "vetagent", "herradura", "goldsmith",
    "glass-hydra", "fruit-scout-production", "matt@", "farmagent.fruitscout.ai",
]

# Non-neutral locale/timezone may appear ONLY as configurable values, never as a
# DEFAULT. We assert the settings defaults are the neutral en-US / UTC and that
# these tokens do not appear anywhere in source.
DENY_DEFAULT_TOKENS = ["America/Mexico_City", "es-MX"]


def _source_files():
    return [p for p in PACKAGE.rglob("*.py")] + [p for p in PACKAGE.rglob("*.sql")]


def test_no_consumer_identifier_in_source():
    offenders = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8").lower()
        for needle in DENY_SUBSTRINGS:
            if needle.lower() in text:
                offenders.append((str(path), needle))
    assert not offenders, f"consumer identifiers found: {offenders}"


def test_no_nonneutral_locale_or_tz_default_in_source():
    offenders = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8")
        for token in DENY_DEFAULT_TOKENS:
            if token in text:
                offenders.append((str(path), token))
    assert not offenders, f"non-neutral locale/tz found in source: {offenders}"


def test_settings_defaults_are_neutral():
    from cos_identity import IdentitySettings

    s = IdentitySettings(jwt_secret="x")
    assert s.default_locale == "en-US"
    assert s.default_timezone == "UTC"


def test_ddl_declares_neutral_defaults():
    ddl = (PACKAGE / "sql" / "001_identity_schema.sql").read_text(encoding="utf-8")
    assert "'en-US'" in ddl and "'UTC'" in ddl
    assert not re.search(r"America/Mexico_City|es-MX", ddl)
