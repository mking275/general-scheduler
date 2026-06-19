import sqlite3, json, uuid
from datetime import datetime, timedelta
import random

random.seed(123)
conn = sqlite3.connect('backend/scheduler.db')
conn.row_factory = sqlite3.Row

# Ensure table exists
conn.execute('''CREATE TABLE IF NOT EXISTS labs (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    timeblock_id TEXT,
    panel_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    ordered_by TEXT DEFAULT '',
    ordered_at TEXT NOT NULL,
    resulted_at TEXT,
    results TEXT DEFAULT '{}'
)''')

def make_cbc(alert_offset=0):
    return {
        "panels": [{
            "name": "CBC",
            "analytes": [
                {"name": "WBC",  "value": round(random.uniform(5.5, 14.0) + alert_offset, 1), "unit": "K/uL",  "low": 6.0,  "high": 17.0},
                {"name": "RBC",  "value": round(random.uniform(5.5, 8.0), 2), "unit": "M/uL",  "low": 5.5,  "high": 8.5},
                {"name": "HGB",  "value": round(random.uniform(11.5, 17.5), 1), "unit": "g/dL", "low": 12.0, "high": 18.0},
                {"name": "HCT",  "value": round(random.uniform(35.0, 55.0), 1), "unit": "%",    "low": 37.0, "high": 55.0},
                {"name": "PLT",  "value": round(random.uniform(180, 480)), "unit": "K/uL",  "low": 200,  "high": 500},
            ]
        }]
    }

def make_chemistry(sick=False):
    return {
        "panels": [{
            "name": "Chemistry Panel",
            "analytes": [
                {"name": "BUN",        "value": round(random.uniform(10, 28 if not sick else 45), 1), "unit": "mg/dL", "low": 10.0, "high": 28.0},
                {"name": "Creatinine", "value": round(random.uniform(0.5, 1.4 if not sick else 2.8), 2), "unit": "mg/dL", "low": 0.5,  "high": 1.5},
                {"name": "ALT",        "value": round(random.uniform(10, 80 if not sick else 200)), "unit": "U/L",   "low": 10,   "high": 100},
                {"name": "AST",        "value": round(random.uniform(15, 50 if not sick else 120)), "unit": "U/L",   "low": 15,   "high": 66},
                {"name": "Albumin",    "value": round(random.uniform(2.5, 4.0), 1), "unit": "g/dL",  "low": 2.5,  "high": 4.0},
                {"name": "Glucose",    "value": round(random.uniform(70, 120 if not sick else 280)), "unit": "mg/dL", "low": 70,   "high": 138},
                {"name": "Calcium",    "value": round(random.uniform(8.5, 11.0), 1), "unit": "mg/dL", "low": 8.5,  "high": 11.5},
            ]
        }]
    }

def make_thyroid():
    return {
        "panels": [{
            "name": "Thyroid Panel",
            "analytes": [
                {"name": "Total T4", "value": round(random.uniform(1.5, 4.0), 1), "unit": "ug/dL", "low": 1.5, "high": 4.0},
                {"name": "fT4",      "value": round(random.uniform(0.7, 2.5), 1), "unit": "ng/dL", "low": 0.7, "high": 2.5},
            ]
        }]
    }

patients = conn.execute("SELECT id, name FROM patients LIMIT 20").fetchall()
if not patients:
    print("No patients found. Run with existing patient data.")
    exit()

vets = ["Dr. Smith", "Dr. Jones", "Dr. Patel", "Dr. Chen"]
inserted = 0
for pat in patients:
    pid = pat['id']
    pname = pat['name']
    # Seed 2-3 past labs, spaced weeks apart
    for i, (panel_name, result_fn, sick) in enumerate([
        ("CBC",               lambda s: make_cbc(alert_offset=2 if s else 0), random.random() < 0.3),
        ("Chemistry Panel",   lambda s: make_chemistry(sick=s), random.random() < 0.25),
        ("Thyroid Panel",     lambda s: make_thyroid(), False),
    ]):
        is_sick = sick if isinstance(sick, bool) else sick
        ordered = (datetime.now() - timedelta(days=random.randint(30, 180))).isoformat()
        resulted = (datetime.fromisoformat(ordered) + timedelta(hours=random.randint(2, 8))).isoformat()
        lab_id = str(uuid.uuid4())
        results = result_fn(is_sick)
        conn.execute(
            "INSERT OR IGNORE INTO labs (id, patient_id, panel_name, status, ordered_by, ordered_at, resulted_at, results) VALUES (?,?,?,?,?,?,?,?)",
            (lab_id, pid, panel_name, 'resulted', random.choice(vets), ordered, resulted, json.dumps(results))
        )
        inserted += 1

conn.commit()
print(f"Seeded {inserted} lab results for {len(patients)} patients")
conn.close()
