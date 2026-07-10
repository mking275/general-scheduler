"""T042 — after-hours boundary gate (FR-004).

The runtime gate consumes ``clinic_voice_config.after_hours_window`` to decide
whether the voice line handles a call. It MUST exist and be tested (so daytime
scope stays out of 3a/3b) even though the pilot line may be after-hours-only at
the telephony layer. Boundary times are tested, including overnight windows that
span midnight and all-day Sunday. The boundary is read from config, never
hard-coded.
"""
import os
from datetime import datetime

import yaml

from backend.voice.verbs import AfterHoursGate, after_hours_admits

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _window() -> dict:
    with open(os.path.join(_REPO_ROOT, "config", "voice",
                           "clinic_voice_config.goldsmith.yaml")) as f:
        return yaml.safe_load(f)["after_hours_window"]


# Explicit calendar anchors (2026-07-07 is a Tuesday).
_MON, _WED, _SAT, _SUN = "2026-07-06", "2026-07-08", "2026-07-11", "2026-07-12"


def _at(date: str, hhmm: str) -> datetime:
    return datetime.fromisoformat(f"{date}T{hhmm}:00")


def test_t042_weekday_boundaries_read_from_config():
    w = _window()
    # Business hours (08:00–18:00) -> NOT routed to Vera.
    assert after_hours_admits(w, _at(_WED, "12:00")) is False
    assert after_hours_admits(w, _at(_WED, "17:59")) is False
    assert after_hours_admits(w, _at(_WED, "08:00")) is False   # office opens
    # After-hours -> handled by Vera.
    assert after_hours_admits(w, _at(_WED, "18:00")) is True    # evening starts
    assert after_hours_admits(w, _at(_WED, "19:30")) is True
    assert after_hours_admits(w, _at(_WED, "07:59")) is True    # early morning


def test_t042_overnight_window_spans_midnight():
    w = _window()
    # The weekday_evening window (18:00→08:00) wraps past midnight.
    assert after_hours_admits(w, _at(_WED, "23:59")) is True
    assert after_hours_admits(w, _at(_WED, "00:00")) is True
    assert after_hours_admits(w, _at(_WED, "02:00")) is True
    assert after_hours_admits(w, _at(_WED, "05:00")) is True


def test_t042_saturday_partial_window():
    w = _window()
    # Saturday office hours 09:00–13:00 -> not after hours.
    assert after_hours_admits(w, _at(_SAT, "10:00")) is False
    assert after_hours_admits(w, _at(_SAT, "09:00")) is False
    # Saturday afternoon/evening + early morning -> after hours (13:00→09:00 wrap).
    assert after_hours_admits(w, _at(_SAT, "13:00")) is True
    assert after_hours_admits(w, _at(_SAT, "20:00")) is True
    assert after_hours_admits(w, _at(_SAT, "07:00")) is True


def test_t042_sunday_is_all_day():
    w = _window()
    for hhmm in ("00:00", "06:00", "12:00", "18:00", "23:59"):
        assert after_hours_admits(w, _at(_SUN, hhmm)) is True


def test_t042_gate_routes_vera_vs_passthrough():
    gate = AfterHoursGate(_window())
    assert gate.route(_at(_WED, "02:00")) == "vera"          # after hours -> Vera
    assert gate.route(_at(_WED, "12:00")) == "passthrough"   # daytime -> not Vera
    assert gate.admits(_at(_SUN, "15:00")) is True


def test_t042_boundary_not_hardcoded_uses_config():
    # A different window changes the decision — proves it's config-driven.
    custom = {"weekday_evening": {"start": "20:00", "end": "06:00"}}
    assert after_hours_admits(custom, _at(_WED, "19:00")) is False   # still business
    assert after_hours_admits(custom, _at(_WED, "21:00")) is True
    # With no window config, nothing is after-hours (gate is inert, not crashing).
    assert after_hours_admits({}, _at(_WED, "02:00")) is False
