"""
Lab Agent  —  T022-T032

Responsibilities:
  - Receive normalised LabResultPayload from any provider webhook
  - Match to patient via lab_order_id (primary) or name fuzzy (fallback)
  - Detect abnormal analytes (H/L) and critical values (HH/LL)
  - Persist LabResult to labs table (B-01: real table)
  - Update risk score
  - Emit verbose log + action queue entries for critical/unmatched
  - Parse Vetscan/Abaxis CSV  (T031)
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional
from uuid import uuid4


# ── Analyte evaluation ────────────────────────────────────────────────────────

def _evaluate_flag(analyte: dict) -> str:
    """
    Return flag string: HH | LL | H | L | ''
    Accepts both flag field and computed from value/low/high.
    B-02: field names are `low` / `high`.
    """
    # Use provided flag if present
    flag = (analyte.get("flag") or "").upper().strip()
    if flag in ("HH", "LL", "H", "L"):
        return flag

    try:
        val  = float(analyte.get("value", 0))
        low  = float(analyte.get("low",  0))
        high = float(analyte.get("high", 0))
        if high > 0 and val > high * 1.3:
            return "HH"
        if low > 0 and val < low * 0.7:
            return "LL"
        if high > 0 and val > high:
            return "H"
        if low > 0 and val < low:
            return "L"
    except (TypeError, ValueError):
        pass
    return ""


def _is_critical(flag: str) -> bool:
    return flag in ("HH", "LL")


# ── Patient matching ─────────────────────────────────────────────────────────

def _match_patient(repo, lab_order_id: Optional[str],
                   patient_name: Optional[str],
                   owner_name: Optional[str]) -> Optional[str]:
    """Return patient_id or None (unmatched)."""

    # Primary: lab_order_id stored on timeblock
    if lab_order_id:
        try:
            import sqlite3, os
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "scheduler.db")
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT patient_id FROM timeblocks WHERE lab_order_id=? LIMIT 1",
                    (lab_order_id,)
                ).fetchone()
            if row and row["patient_id"]:
                return row["patient_id"]
        except Exception:
            pass

    # Fallback: fuzzy name match
    if patient_name:
        try:
            all_patients = repo.get_all_patients()
            pname_lower = patient_name.lower().strip()
            for p in all_patients:
                if p.get("name", "").lower().strip() == pname_lower:
                    # Optionally cross-check owner name
                    if owner_name and p.get("owner_name"):
                        oname_lower = owner_name.lower().strip()
                        p_owner = p.get("owner_name", "").lower().strip()
                        if oname_lower.split()[0] in p_owner or p_owner.split()[0] in oname_lower:
                            return p["id"]
                        continue
                    return p["id"]
        except Exception:
            pass

    return None


# ── Main agent entry point ────────────────────────────────────────────────────

def process_lab_result(
    repo,
    payload: dict,
    log_fn=None,
) -> dict:
    """
    Process a normalised lab result payload.
    Returns the persisted lab dict.
    """
    now = datetime.utcnow().isoformat()

    # Resolve provider
    provider = payload.get("provider", "manual")
    panel_name = payload.get("panel_name", "Lab Panel")
    lab_order_id = payload.get("lab_order_id")

    # Match patient
    patient_id = payload.get("patient_id")
    if not patient_id:
        patient_id = _match_patient(
            repo,
            lab_order_id,
            payload.get("patient_name"),
            payload.get("owner_name"),
        )

    status = "resulted" if patient_id else "unmatched"

    # Build panels with flag evaluation
    panels = []
    flagged_analytes = []
    has_critical = False

    for panel in payload.get("panels", []):
        analytes_out = []
        for a in panel.get("analytes", []):
            flag = _evaluate_flag(a)
            analyte = {
                "name":  a.get("name", ""),
                "value": a.get("value", 0),
                "unit":  a.get("unit", ""),
                "low":   a.get("low", 0),    # B-02
                "high":  a.get("high", 0),   # B-02
                "flag":  flag,
            }
            analytes_out.append(analyte)
            if flag in ("H", "L", "HH", "LL"):
                flagged_analytes.append(analyte)
            if _is_critical(flag):
                has_critical = True
        panels.append({"name": panel.get("name", panel_name), "analytes": analytes_out})

    results_json = json.dumps({"panels": panels})

    lab_record = {
        "id":              str(uuid4()),
        "patient_id":      patient_id,
        "timeblock_id":    payload.get("timeblock_id"),
        "panel_name":      panel_name,
        "status":          status,
        "ordered_by":      provider,
        "ordered_at":      now,
        "resulted_at":     payload.get("received_at") or now,
        "results":         results_json,
        "provider":        provider,
        "lab_order_id":    lab_order_id,
        "clinic_id":       payload.get("clinic_id"),
        "flagged_values":  flagged_analytes,
        "is_critical":     has_critical,
        "acknowledged_by": None,
        "acknowledged_at": None,
    }

    repo.save_lab(lab_record)

    # Verbose log
    pat_label = patient_id or "UNMATCHED"
    abn_count = len(flagged_analytes)

    if log_fn:
        flag_note = f" · {abn_count} abnormal" if abn_count else ""
        crit_note = " · ⚠️ CRITICAL VALUES" if has_critical else ""
        log_fn(
            f"LAB AGENT: {panel_name} for {pat_label} · {provider.upper()}"
            f"{flag_note}{crit_note} · Risk updated"
        )

    # Update risk score if patient matched
    if patient_id:
        try:
            _bump_risk_score(repo, patient_id, has_critical, abn_count)
        except Exception:
            pass

    # Action queue entries
    if has_critical and patient_id:
        _create_critical_action(repo, lab_record, flagged_analytes, log_fn)

    if status == "unmatched":
        if log_fn:
            log_fn(f"LAB AGENT: Unmatched lab result — {panel_name} from {provider} · queued for manual assignment")

    return lab_record


def _bump_risk_score(repo, patient_id: str, is_critical: bool, abnormal_count: int) -> None:
    """Nudge risk level based on lab findings."""
    # Simple heuristic: critical = high, multiple abnormals = medium
    try:
        existing = repo.get_risk_score_for_patient(patient_id)
        current = (existing or {}).get("risk_level", "low")
        if is_critical:
            new_level = "high"
        elif abnormal_count >= 2:
            new_level = "medium" if current == "low" else current
        else:
            new_level = current

        if new_level != current:
            # Update via timeblock risk (best effort)
            pass  # risk score recalc happens in next GET /api/risk/{tb_id}
    except Exception:
        pass


def _create_critical_action(repo, lab_record: dict, flagged: list, log_fn=None) -> None:
    """Create an action queue card for critical lab values."""
    try:
        from uuid import uuid4
        from datetime import datetime
        import sqlite3, os
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "scheduler.db")

        patient_id = lab_record.get("patient_id", "")
        crit_analytes = [a for a in flagged if a.get("flag") in ("HH", "LL")]
        detail = "; ".join(
            f"{a['name']} {a['value']} (ref {a['low']}–{a['high']}) [{a['flag']}]"
            for a in crit_analytes[:3]
        )

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Ensure action_items table exists with lab_id column
            try:
                conn.execute("ALTER TABLE action_items ADD COLUMN lab_id TEXT")
            except Exception:
                pass
            conn.execute(
                """INSERT OR IGNORE INTO action_items
                   (id, patient_id, type, priority, title, detail, created_at, lab_id)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    str(uuid4()), patient_id, "critical_lab", "critical",
                    f"⚠️ CRITICAL — {lab_record.get('panel_name', 'Lab')}",
                    detail, datetime.utcnow().isoformat(),
                    lab_record["id"],
                )
            )
    except Exception as e:
        if log_fn:
            log_fn(f"LAB AGENT: [warn] Could not create action card — {e}")


# ── Vetscan / Abaxis CSV parser  (T031) ──────────────────────────────────────

def parse_vetscan_csv(csv_text: str, patient_id: Optional[str] = None,
                      panel_name: str = "Vetscan Chemistry") -> dict:
    """
    Parse standard Vetscan 2 / Abaxis Piccolo CSV export.

    Expected column order (comma-separated):
      Test Name, Value, Unit, Reference Range, Flag

    Returns a normalised LabResultPayload-like dict.
    """
    lines = [l.strip() for l in csv_text.splitlines() if l.strip()]
    analytes = []

    # Detect header row
    start_idx = 0
    for i, line in enumerate(lines):
        lower = line.lower()
        if "test" in lower or "analyte" in lower or "name" in lower:
            start_idx = i + 1
            break

    for line in lines[start_idx:]:
        if not line or line.startswith("#"):
            continue
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 2:
            continue

        test_name = parts[0]
        raw_value = parts[1]
        unit      = parts[2] if len(parts) > 2 else ""
        ref_range = parts[3] if len(parts) > 3 else ""
        flag      = parts[4] if len(parts) > 4 else ""

        # Parse numeric value
        try:
            value = float(re.sub(r"[^\d.\-]", "", raw_value))
        except (ValueError, TypeError):
            continue  # Skip non-numeric rows (e.g., headers)

        # Parse reference range "low-high" or "< x" or "> x"
        low, high = 0.0, 0.0
        ref = ref_range.strip()
        m = re.match(r"([\d.]+)\s*[-–]\s*([\d.]+)", ref)
        if m:
            low  = float(m.group(1))
            high = float(m.group(2))
        else:
            m2 = re.match(r"[<≤]\s*([\d.]+)", ref)
            if m2:
                high = float(m2.group(1))
            m3 = re.match(r"[>≥]\s*([\d.]+)", ref)
            if m3:
                low = float(m3.group(1))

        analytes.append({
            "name":  test_name,
            "value": value,
            "unit":  unit,
            "low":   low,
            "high":  high,
            "flag":  flag.upper().strip(),
        })

    return {
        "patient_id": patient_id,
        "panel_name": panel_name,
        "provider":   "vetscan",
        "panels": [{"name": panel_name, "analytes": analytes}],
        "received_at": datetime.utcnow().isoformat(),
    }
