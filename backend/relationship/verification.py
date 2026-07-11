"""Feature 011 — Phase C: caller-ID + tiered verification bar.

Three contracts live here:

* **T015 / R4** — ``VerificationService.require_verification``: a tiered,
  config-driven knowledge-factor bar (``verification_policy.<clinic>.yaml``).
  Soft-confirm (``phone_match``) is IDENTIFICATION ONLY and authorizes **no**
  change (FR-008/017, SC-005). Low-sensitivity actions need **1** knowledge
  factor; high-sensitivity actions need **2** or a ``deferred_staff_callback``.
  Every factor is validated against its **authoritative source** — a wrong
  value can never clear the bar (H3/FR-018): ``pet_name`` against
  ``patient_household_link`` (active pets only, normalized exact-or-first-token),
  ``appointment_day`` against the 010 booking/schedule store. A failure blocks
  the change, leaves state unchanged, offers a staff callback, and writes an
  append-only ``verification_challenge`` (no raw secret values).

* **T016** — ``VerificationSession``: mid-call sensitivity escalation re-applies
  the higher bar before a sensitive action (a caller who cleared the low bar for
  a reschedule is re-challenged to the 2-factor bar when they escalate to a
  contact-info edit).

* **T017 / R5** — ``reconcile_binding_tier``: a **one-way, NON-MUTATING** boundary
  adapter at the core-binding edge. It maps every value of BOTH 010 vocabularies
  (``VerificationLevel = none|soft_confirmed|strong`` shim +
  ``VerificationState = unverified|soft_confirmed``) onto core's tier. It reads a
  copy and emits a core value — 010's enum strings are NEVER rewritten. Audience
  derives from **tier + role, never caller-ID alone**.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

import yaml

from backend.models import SensitivityTier, VerificationChallenge

# Core's 4-tier verification vocabulary (the target of the R5 adapter + the
# tier 011's own factor progression produces). ``otp_verified`` is unused in 4a.
CoreTier = Literal["unverified", "phone_match", "code_verified", "identity_confirmed"]

Audience = Literal["owner", "manager", "staff", "client_verified", "caller_unverified"]


# =========================================================================== #
#  R5 — ChannelBinding tier reconcile (non-mutating boundary adapter, H2)
# =========================================================================== #
# Total over the UNION of both 010 vocabularies' string values. 010's strings
# are never mutated — this maps a COPY onto core's tier at the binding edge.
#   VerificationState: unverified | soft_confirmed
#   VerificationLevel (shim): none | soft_confirmed | strong
_BOUNDARY_MAP: dict[str, CoreTier] = {
    "unverified": "unverified",       # VerificationState.unverified
    "none": "unverified",             # shim VerificationLevel none
    "soft_confirmed": "phone_match",  # both enums -> caller-ID / identification only
    "strong": "identity_confirmed",   # shim VerificationLevel strong
}


def reconcile_binding_tier(binding_value: str) -> CoreTier:
    """Translate a 010 verification string onto core's tier (one-way, H2).

    Reads a COPY of the 010 value and returns a core tier; it writes nothing
    back into 010's enums. ``code_verified`` is deliberately **not** a boundary
    target — 010 carries no knowledge-factor state, so it never emits a value
    mapping there; ``code_verified`` is reached only through 011's own R4
    factor progression (see :meth:`VerificationService.require_verification`).
    """
    value = str(binding_value)
    if value not in _BOUNDARY_MAP:
        raise ValueError(f"reconcile_binding_tier: unmapped 010 value {value!r}")
    return _BOUNDARY_MAP[value]


def derive_audience(core_tier: CoreTier, *, staff_role: Optional[str] = None) -> Audience:
    """Audience scope derives from **tier + role, never caller-ID alone** (R5).

    Staff-side audience comes from ``clinic_staff_role`` (owner/manager/staff).
    Client-side (voice callers are always client-tier in 4a): only a knowledge
    factor (``code_verified`` / ``identity_confirmed``) grants ``client_verified``;
    a bare ``phone_match`` (caller-ID) authorizes ONLY unverified-scope reveals.
    """
    if staff_role in ("owner", "manager", "staff"):
        return staff_role  # type: ignore[return-value]
    if core_tier in ("code_verified", "identity_confirmed"):
        return "client_verified"
    return "caller_unverified"


# =========================================================================== #
#  R4 — verification policy (config-driven)
# =========================================================================== #
@dataclass
class VerificationPolicy:
    sensitivity: dict[str, str]              # action -> "low" | "high"
    factors_required: dict[str, int]         # tier -> count
    staff_callback_deferral: dict[str, bool] # tier -> may defer to staff callback
    factors: dict[str, dict]                 # factor name -> {source: ...}

    @classmethod
    def from_yaml(cls, text: str) -> "VerificationPolicy":
        data = yaml.safe_load(text) or {}
        return cls(
            sensitivity=data.get("sensitivity", {}),
            factors_required=data.get("factors_required", {}),
            staff_callback_deferral=data.get("staff_callback_deferral", {}),
            factors=data.get("factors", {}),
        )

    @classmethod
    def load(cls, path: str) -> "VerificationPolicy":
        with open(path) as f:
            return cls.from_yaml(f.read())

    def tier_for(self, action: str) -> str:
        # Fail-closed: an unknown action is treated as HIGH sensitivity.
        return self.sensitivity.get(action, "high")

    def required_for(self, tier: str) -> int:
        return int(self.factors_required.get(tier, 2))

    def can_defer(self, tier: str) -> bool:
        return bool(self.staff_callback_deferral.get(tier, False))


def _config_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(root, "config", "relationship",
                        "verification_policy.goldsmith.yaml")


def _norm(s: str) -> str:
    return " ".join(str(s).lower().split())


def _pet_name_matches(value: str, roster_name: str) -> bool:
    """Normalized exact-or-first-token match: ``"Rex"`` matches ``"Rex Alvarez"``."""
    nv, nn = _norm(value), _norm(roster_name)
    if not nv or not nn:
        return False
    if nv == nn:
        return True
    parts = nn.split()
    return bool(parts) and nv == parts[0]


def _day_matches(value: str, scheduled_days: list[str]) -> bool:
    nv = _norm(value)
    return any(nv == _norm(d) for d in scheduled_days)


# Injectable 010 booking/schedule source: household_id -> scheduled day strings.
AppointmentSource = Callable[[str], list[str]]


@dataclass
class ChallengeResult:
    outcome: Literal["passed", "failed", "deferred_staff_callback"]
    factors_presented: list[str]
    sensitivity_tier: str
    factors_required: int
    core_tier: CoreTier = "unverified"
    staff_callback_offered: bool = False

    @property
    def authorizes_change(self) -> bool:
        return self.outcome == "passed"


@dataclass
class PresentedFactor:
    name: str
    value: str


class VerificationService:
    """R4 tiered verification bar. Validates knowledge factors against their
    authoritative sources; a wrong value can never clear the bar."""

    def __init__(self, repo, policy: Optional[VerificationPolicy] = None,
                 appointment_source: Optional[AppointmentSource] = None):
        self.repo = repo
        self.policy = policy or VerificationPolicy.load(_config_path())
        # Default source yields no scheduled days -> appointment_day fails closed
        # until the 010 booking store is wired.
        self.appointment_source: AppointmentSource = appointment_source or (lambda hid: [])

    # ------------------------------------------------------------------ #
    #  Factor validation against authoritative sources (H3/FR-018)
    # ------------------------------------------------------------------ #
    def validate_factor(self, name: str, value: str, household_id: Optional[str]) -> bool:
        if not household_id:
            return False
        if name == "pet_name":
            for p in self.repo.get_patients_for_household(household_id):
                if p.get("status") != "active":      # deceased/rehomed never satisfy
                    continue
                if _pet_name_matches(value, p.get("display_name", "")):
                    return True
            return False
        if name == "appointment_day":
            return _day_matches(value, self.appointment_source(household_id))
        # Unknown factor type -> fail closed.
        return False

    # ------------------------------------------------------------------ #
    #  R4 — require_verification
    # ------------------------------------------------------------------ #
    def require_verification(
        self, action: str, party_id: Optional[str], *,
        binding_level: str = "none",
        presented_factors: Optional[list[PresentedFactor]] = None,
        household_id: Optional[str] = None,
        clinic_id: str,
        call_session_id: Optional[str] = None,
        prefer_staff_callback: bool = False,
    ) -> ChallengeResult:
        presented = presented_factors or []
        tier = self.policy.tier_for(action)
        required = self.policy.required_for(tier)
        can_defer = self.policy.can_defer(tier)

        # Validate each presented factor against its source. Soft-confirm /
        # caller-ID contributes ZERO factors: it never appears here.
        results = [(f.name, self.validate_factor(f.name, f.value, household_id))
                   for f in presented]
        passed_count = sum(1 for _, ok in results if ok)

        if prefer_staff_callback and can_defer:
            outcome = "deferred_staff_callback"
        elif passed_count >= required:
            outcome = "passed"
        else:
            outcome = "failed"

        core_tier = self._core_tier(outcome, required, binding_level)
        self._log(clinic_id, call_session_id, party_id, action, tier, required,
                  results, outcome)
        return ChallengeResult(
            outcome=outcome, factors_presented=[n for n, _ in results],
            sensitivity_tier=tier, factors_required=required, core_tier=core_tier,
            staff_callback_offered=(outcome != "passed" and can_defer),
        )

    @staticmethod
    def _core_tier(outcome: str, required: int, binding_level: str) -> CoreTier:
        if outcome == "passed":
            # 011's own factor progression -> core tiers directly (R5).
            return "identity_confirmed" if required >= 2 else "code_verified"
        # Non-pass: state unchanged — stay at the binding's (caller-ID) tier.
        return reconcile_binding_tier(binding_level)

    def _log(self, clinic_id, call_session_id, party_id, action, tier, required,
             results, outcome) -> None:
        self.repo.append_verification_challenge(VerificationChallenge(
            clinic_id=clinic_id, call_session_id=call_session_id, party_id=party_id,
            action_requested=action, sensitivity_tier=SensitivityTier(tier),
            factors_required=required,
            # factors_presented_json records WHICH factor + pass/fail — never the
            # raw secret value (FR-018).
            factors_presented_json=[{"factor": n, "passed": ok} for n, ok in results],
            outcome=outcome,
        ))


# =========================================================================== #
#  T016 — mid-call sensitivity escalation re-gate
# =========================================================================== #
class VerificationSession:
    """Tracks knowledge factors cleared within one call. A sensitivity
    escalation re-applies the HIGHER bar before the sensitive action: the
    accumulated distinct passed-factor count must meet the new action's tier."""

    def __init__(self, service: VerificationService, *, clinic_id: str,
                 party_id: Optional[str] = None, household_id: Optional[str] = None,
                 binding_level: str = "none", call_session_id: Optional[str] = None):
        self._svc = service
        self._clinic_id = clinic_id
        self._party_id = party_id
        self._household_id = household_id
        self._binding_level = binding_level
        self._call_session_id = call_session_id
        self._passed_factors: set[str] = set()

    @property
    def passed_factors(self) -> set[str]:
        return set(self._passed_factors)

    def request(self, action: str,
                presented_factors: Optional[list[PresentedFactor]] = None,
                prefer_staff_callback: bool = False) -> ChallengeResult:
        svc, policy = self._svc, self._svc.policy
        tier = policy.tier_for(action)
        required = policy.required_for(tier)
        can_defer = policy.can_defer(tier)

        # Accumulate newly-validated factors across the session.
        results = []
        for f in (presented_factors or []):
            ok = svc.validate_factor(f.name, f.value, self._household_id)
            results.append((f.name, ok))
            if ok:
                self._passed_factors.add(f.name)

        # Re-gate: the accumulated distinct passed-factor count must meet the
        # ESCALATED action's bar.
        if prefer_staff_callback and can_defer:
            outcome = "deferred_staff_callback"
        elif len(self._passed_factors) >= required:
            outcome = "passed"
        else:
            outcome = "failed"

        core_tier = VerificationService._core_tier(outcome, required, self._binding_level)
        svc._log(self._clinic_id, self._call_session_id, self._party_id, action,
                 tier, required, results, outcome)
        return ChallengeResult(
            outcome=outcome, factors_presented=[n for n, _ in results],
            sensitivity_tier=tier, factors_required=required, core_tier=core_tier,
            staff_callback_offered=(outcome != "passed" and can_defer),
        )
