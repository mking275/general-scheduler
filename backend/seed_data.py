"""
Seed mock patients, owners, appointments, and clinics for the vet clinic demo.
Called on app startup if the respective tables are empty.
"""
from datetime import datetime, timedelta
import json
import uuid as _uuid
from .repository import db, _get_conn
from .models import Patient, Owner, Clinic, VetClinicAssignment


def seed_patients_and_owners():
    """Seed 10 mock owners + 10 patients across 4 species with 3 flag types."""
    with _get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    if count > 0:
        return  # Already seeded

    # ------------------------------------------------------------------ #
    # Owners
    # ------------------------------------------------------------------ #
    owners_data = [
        ("Sarah Mitchell",   "(503) 555-0142", "sarah.m@email.com"),
        ("James Kowalski",   "(503) 555-0187", "james.k@email.com"),
        ("Priya Sharma",     "(503) 555-0263", "priya.s@email.com"),
        ("Carlos Rivera",    "(503) 555-0331", "carlos.r@email.com"),
        ("Emily Chen",       "(503) 555-0408", "emily.c@email.com"),
        ("David O'Brien",    "(503) 555-0572", "david.o@email.com"),
        ("Nadia Petrov",     "(503) 555-0619", "nadia.p@email.com"),
        ("Marcus Johnson",   "(503) 555-0743", "marcus.j@email.com"),
        ("Lucia Gomez",      "(503) 555-0855", "lucia.g@email.com"),
        ("Tom Nakamura",     "(503) 555-0924", "tom.n@email.com"),
    ]

    owner_ids = []
    for name, phone, email in owners_data:
        oid = str(_uuid.uuid4())
        owner_ids.append(oid)
        db.create_owner(Owner(id=oid, name=name, phone=phone, email=email, patient_ids=[]))

    # ------------------------------------------------------------------ #
    # Patients (10 patients, 4 species: dog/cat/bird/exotic)
    # Mix of flag types: alert, chronic, first_visit
    # ------------------------------------------------------------------ #
    patients_raw = [
        # id_idx, name, species, breed, dob, weight_kg, flags, flag_notes, owner_idx,
        # visit_count, last_visit_date, last_visit_procedure
        (0, "Buddy",      "dog",    "Golden Retriever",    "2019-03-14", 28.5, ["alert"],       "Allergic to penicillin",           0,  7, "2026-04-10", "Annual Wellness"),
        (1, "Whiskers",   "cat",    "Siamese",             "2021-06-01",  4.2, ["chronic"],     "Hyperthyroidism — daily medication",1,  4, "2026-03-22", "Thyroid Check"),
        (2, "Mango",      "bird",   "African Grey Parrot", "2018-11-05",  0.5, ["first_visit"], "",                                  2,  0, None,         None),
        (3, "Rex",        "dog",    "German Shepherd",     "2017-08-20", 35.0, ["alert","chronic"], "Hip dysplasia; NSAIDs contraindicated", 3, 12, "2026-05-15", "Surgery Follow-up"),
        (4, "Luna",       "cat",    "Maine Coon",          "2020-02-14",  6.8, [],              "",                                  4,  2, "2026-01-30", "Vaccination"),
        (5, "Kiwi",       "bird",   "Cockatiel",           "2022-04-03",  0.1, ["first_visit"], "",                                  5,  0, None,         None),
        (6, "Spike",      "exotic", "Bearded Dragon",      "2020-09-12",  0.4, ["chronic"],     "Metabolic bone disease — supplement monthly", 6, 5, "2026-02-18", "Wellness Exam"),
        (7, "Daisy",      "dog",    "Labrador Retriever",  "2023-01-07", 22.0, ["first_visit"], "",                                  7,  0, None,         None),
        (8, "Cleo",       "cat",    "British Shorthair",   "2016-05-30",  5.5, ["alert"],       "Cardiomyopathy — stress monitoring required", 8, 9, "2026-05-01", "Cardiac Check"),
        (9, "Ziggy",      "exotic", "Ball Python",         "2019-07-22",  1.2, [],              "",                                  9,  3, "2025-12-10", "Wellness Exam"),
    ]

    patient_ids = []
    for (_, p_name, species, breed, dob, weight_kg, flags, flag_notes,
         owner_idx, visit_count, last_visit_date, last_visit_procedure) in patients_raw:
        pid = str(_uuid.uuid4())
        patient_ids.append(pid)
        patient = Patient(
            id=pid,
            name=p_name,
            species=species,
            breed=breed,
            dob=dob,
            weight_kg=weight_kg,
            flags=flags,
            flag_notes=flag_notes,
            owner_id=owner_ids[owner_idx],
            visit_count=visit_count,
            last_visit_date=last_visit_date,
            last_visit_procedure=last_visit_procedure,
        )
        db.create_patient(patient)

        # Link patient to owner
        with _get_conn() as conn:
            row = conn.execute("SELECT patient_ids FROM owners WHERE id=?", (owner_ids[owner_idx],)).fetchone()
            existing = json.loads(row["patient_ids"])
            existing.append(pid)
            conn.execute("UPDATE owners SET patient_ids=? WHERE id=?", (json.dumps(existing), owner_ids[owner_idx]))

    # ------------------------------------------------------------------ #
    # Seed 8 appointments linked to patients
    # Vary: lead time, procedure type, patient visit count → 3 risk levels
    # Cover procedures: Wellness, Surgery, Dental, Vaccination, Grooming
    # ------------------------------------------------------------------ #
    _seed_appointments(patient_ids, owner_ids)

    print(f"[SEED] Seeded {len(patient_ids)} patients and {len(owners_data)} owners.")


def _seed_appointments(patient_ids: list, owner_ids: list):
    """Create 8 mock timeblocks linked to patients with varied risk profiles."""
    from .repository import db, _get_conn
    import json

    # Check if timeblocks already exist
    with _get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM timeblocks").fetchone()[0]
    if count > 0:
        return

    # Get resource IDs from DB
    with _get_conn() as conn:
        res_rows = conn.execute("SELECT id, name, type FROM resources").fetchall()
    resources = {r["name"]: r["id"] for r in res_rows}

    now = datetime.now().replace(minute=0, second=0, microsecond=0)

    def make_slot(hour_offset, duration=60):
        start = now.replace(hour=9) + timedelta(hours=hour_offset)
        end = start + timedelta(minutes=duration)
        return start, end

    # job_id, patient_idx, owner_idx, vet_name, room_name, start_offset, duration,
    # procedure, intake_status, risk_level (seeded)
    appointments = [
        # 1. Buddy — Wellness, booked 8+ days ahead → LOW risk
        (patient_ids[0], owner_ids[0], "Dr. Smith",  "Exam Room 1",      0,  60, "Wellness Exam",   "not_started", "low"),
        # 2. Rex — Surgery, same-day, first_visit combo but chronic → HIGH risk
        (patient_ids[3], owner_ids[3], "Dr. Smith",  "Operating Room A", 1,  90, "Surgery",         "received",    "high"),
        # 3. Whiskers — Dental, booked 3 days ahead → MEDIUM risk
        (patient_ids[1], owner_ids[1], "Dr. Patel",  "Operating Room B", 2,  60, "Dental Cleaning", "pending",     "medium"),
        # 4. Mango — Avian exam, first visit → MEDIUM risk
        (patient_ids[2], owner_ids[2], "Dr. Jones",  "Exam Room 1",      3,  45, "Avian Exam",      "not_started", "medium"),
        # 5. Luna — Vaccination → LOW risk (repeat visit, wellness)
        (patient_ids[4], owner_ids[4], "Dr. Jones",  "Exam Room 2",      4,  30, "Vaccination",     "not_started", "low"),
        # 6. Daisy — Grooming, first visit → MEDIUM risk
        (patient_ids[7], owner_ids[7], "Dr. Patel",  "Grooming Suite",   5,  60, "Grooming",        "not_started", "medium"),
        # 7. Cleo — Emergency cardiac → HIGH risk
        (patient_ids[8], owner_ids[8], "Dr. Smith",  "Exam Room 1",      6,  60, "Emergency Visit", "received",    "high"),
        # 8. Spike — Wellness exotic → LOW risk (repeat)
        (patient_ids[6], owner_ids[6], "Dr. Jones",  "Exam Room 1",      7,  45, "Wellness Exam",   "not_started", "low"),
    ]

    from .models import RiskScore
    from datetime import datetime as dt

    with _get_conn() as conn:
        for (pid, oid, vet_name, room_name, offset, dur, procedure, intake_status, risk_level) in appointments:
            tb_id = str(_uuid.uuid4())
            job_id = str(_uuid.uuid4())
            start, end = make_slot(offset, dur)

            vet_id = resources.get(vet_name, "")
            room_id = resources.get(room_name, "")
            resource_ids = [r for r in [vet_id, room_id] if r]

            # Insert job
            job_data = json.dumps({
                "id": job_id,
                "required_skills": ["General Practice"],
                "estimated_duration": dur,
                "patient_name": None,
                "procedure": procedure,
                "soft_requirements": "",
                "scheduled_date": None,
                "scheduled_time": None,
            })
            conn.execute("INSERT OR IGNORE INTO jobs VALUES (?,?)", (job_id, job_data))

            # Insert timeblock
            conn.execute(
                """INSERT OR IGNORE INTO timeblocks
                   (id, job_id, resource_ids, start_time, end_time,
                    patient_id, intake_status, followup_status, risk_level, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    tb_id, job_id, json.dumps(resource_ids),
                    start.isoformat(), end.isoformat(),
                    pid, intake_status, "not_started", risk_level, "scheduled",
                ),
            )

            # Insert risk score
            risk_scores = {"low": 15, "medium": 45, "high": 75}
            factors_map = {
                "low": ["Repeat patient (−15)", "Advance booking (0)", "Wellness procedure (+20)"],
                "medium": ["First visit (+15)", "Lead time 48-72h (+20)", "Routine procedure (0)"],
                "high": ["Same-day booking (+40)", "Alert flag — medical risk (+15)", "Emergency/surgical (+15)"],
            }
            rs_id = str(_uuid.uuid4())
            conn.execute(
                """INSERT OR IGNORE INTO risk_scores
                   (id, timeblock_id, risk_level, score, factors, calculated_at)
                   VALUES (?,?,?,?,?,?)""",
                (
                    rs_id, tb_id, risk_level, risk_scores[risk_level],
                    json.dumps(factors_map[risk_level]),
                    dt.utcnow().isoformat(),
                ),
            )

            # For appointments with received intake, seed a pre-exam brief
            if intake_status == "received":
                brief_id = str(_uuid.uuid4())
                if procedure == "Surgery":
                    chief = "Limping and pain in rear left leg"
                    symptoms = [{"name": "limping", "duration_days": 5, "severity": "high"}, {"name": "anorexia", "duration_days": 2, "severity": "mild"}]
                    focus = ["Orthopedic", "pain management"]
                    verbatim = "He's been limping badly for 5 days and stopped eating."
                else:
                    chief = "Lethargy and labored breathing"
                    symptoms = [{"name": "lethargy", "duration_days": 3, "severity": "high"}, {"name": "coughing", "duration_days": 2, "severity": "mild"}]
                    focus = ["Cardiovascular", "respiratory"]
                    verbatim = "She seems exhausted and is coughing at night."
                conn.execute(
                    """INSERT OR IGNORE INTO pre_exam_briefs
                       (id, timeblock_id, chief_complaint, symptoms, owner_verbatim,
                        suggested_focus, status, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        brief_id, tb_id, chief, json.dumps(symptoms),
                        verbatim, json.dumps(focus), "received",
                        dt.utcnow().isoformat(),
                    ),
                )

    # T018: Tag existing seeded timeblocks with clinic-downtown
    with _get_conn() as conn:
        conn.execute(
            "UPDATE timeblocks SET clinic_id='clinic-downtown' WHERE clinic_id IS NULL"
        )


def seed_clinics_and_assignments():
    """
    T006: Seed 2 clinics (Downtown + Westside), assign vets and rooms.
    Called from on_startup only if clinics table is empty.
    """
    with _get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM clinics").fetchone()[0]
    if count > 0:
        return  # Already seeded

    # --- Create clinics ---
    downtown = Clinic(
        id="clinic-downtown",
        name="Paws & Claws Downtown",
        address="123 Main St, Portland, OR 97201",
        phone="(503) 555-1000",
        email="downtown@pawsclaws.com",
        color_hex="#6C63FF",
        is_active=True,
    )
    westside = Clinic(
        id="clinic-westside",
        name="Paws & Claws Westside",
        address="456 Oak Ave, Beaverton, OR 97005",
        phone="(503) 555-2000",
        email="westside@pawsclaws.com",
        color_hex="#00BFA6",
        is_active=True,
    )
    db.create_clinic(downtown)
    db.create_clinic(westside)
    print("[SEED] Created 2 clinics: Downtown, Westside")

    # --- Get existing vets from resources table ---
    with _get_conn() as conn:
        vet_rows = conn.execute(
            "SELECT id, name FROM resources WHERE type='Vet' ORDER BY name ASC"
        ).fetchall()
        room_rows = conn.execute(
            "SELECT id, name FROM resources WHERE type='Room'"
        ).fetchall()

    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Assign first 2 existing vets to Downtown (all days, primary)
    for vet_row in vet_rows[:2]:
        assign = VetClinicAssignment(
            id=str(_uuid.uuid4()),
            vet_id=vet_row["id"],
            clinic_id="clinic-downtown",
            schedule_days=all_days,
            is_primary=True,
        )
        db.save_assignment(assign)

    # If there's a 3rd vet (Dr. Patel), also assign to Downtown
    for vet_row in vet_rows[2:]:
        assign = VetClinicAssignment(
            id=str(_uuid.uuid4()),
            vet_id=vet_row["id"],
            clinic_id="clinic-downtown",
            schedule_days=all_days,
            is_primary=True,
        )
        db.save_assignment(assign)

    # --- Create floating vet Dr. Chen ---
    chen_id = "vet-chen"
    windows_json = json.dumps([
        {"start_time": datetime.now().replace(hour=8, minute=0, second=0, microsecond=0).isoformat(),
         "end_time": datetime.now().replace(hour=17, minute=0, second=0, microsecond=0).isoformat()}
    ])
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO resources (id, name, type, hard_skills, attributes, availability_windows, clinic_id) VALUES (?,?,?,?,?,?,?)",
            (
                chen_id,
                "Dr. Chen",
                "Vet",
                json.dumps(["General Practice", "Surgery", "Dental"]),
                "Floating specialist. Mon/Wed/Fri at Downtown; Tue/Thu at Westside.",
                windows_json,
                None,
            ),
        )

    # Assign Dr. Chen: Downtown Mon/Wed/Fri (primary), Westside Tue/Thu
    db.save_assignment(VetClinicAssignment(
        id=str(_uuid.uuid4()),
        vet_id=chen_id,
        clinic_id="clinic-downtown",
        schedule_days=["Monday", "Wednesday", "Friday"],
        is_primary=True,
    ))
    db.save_assignment(VetClinicAssignment(
        id=str(_uuid.uuid4()),
        vet_id=chen_id,
        clinic_id="clinic-westside",
        schedule_days=["Tuesday", "Thursday"],
        is_primary=False,
    ))
    print("[SEED] Created floating vet Dr. Chen with cross-clinic assignments")

    # --- Assign existing rooms to Downtown ---
    with _get_conn() as conn:
        conn.execute(
            "UPDATE resources SET clinic_id='clinic-downtown' WHERE type='Room'"
        )

    # --- Create 2 Westside rooms ---
    westside_rooms = [
        ("Westside Exam Room 1", ["General Practice", "Avian", "Exotics"],
         "Standard exam room at Westside. Great natural lighting."),
        ("Westside Exam Room 2", ["General Practice", "Vaccination"],
         "Vaccination and wellness room at Westside branch."),
    ]
    with _get_conn() as conn:
        for rname, rskills, rattrs in westside_rooms:
            rid = str(_uuid.uuid4())
            conn.execute(
                "INSERT OR IGNORE INTO resources (id, name, type, hard_skills, attributes, availability_windows, clinic_id) VALUES (?,?,?,?,?,?,?)",
                (rid, rname, "Room", json.dumps(rskills), rattrs, windows_json, "clinic-westside"),
            )
    print("[SEED] Assigned rooms to Downtown; created 2 Westside rooms")

    # T018: set home_clinic_id for last patient (Ziggy) to clinic-westside for cross-clinic demo
    with _get_conn() as conn:
        # Find Ziggy (ball python)
        ziggy_row = conn.execute(
            "SELECT id FROM patients WHERE name='Ziggy' LIMIT 1"
        ).fetchone()
        if ziggy_row:
            conn.execute(
                "UPDATE patients SET home_clinic_id='clinic-westside' WHERE id=?",
                (ziggy_row["id"],),
            )
            print("[SEED] Set Ziggy's home_clinic_id=clinic-westside for cross-clinic demo")


def seed_westside_appointment():
    """
    T018: Seed at least 1 Westside appointment.
    Called from on_startup after clinics are seeded.
    """
    with _get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM timeblocks WHERE clinic_id='clinic-westside'"
        ).fetchone()[0]
    if count > 0:
        return

    # Get Dr. Chen and a Westside room
    with _get_conn() as conn:
        chen_row = conn.execute(
            "SELECT id FROM resources WHERE id='vet-chen'"
        ).fetchone()
        ws_room_row = conn.execute(
            "SELECT id FROM resources WHERE type='Room' AND clinic_id='clinic-westside' LIMIT 1"
        ).fetchone()
        # Get a patient to attach (Mango the bird — first_visit, medium risk)
        mango_row = conn.execute(
            "SELECT id FROM patients WHERE name='Mango' LIMIT 1"
        ).fetchone()

    if not chen_row or not ws_room_row:
        print("[SEED] Skipping Westside appointment seed — resources not found")
        return

    from datetime import datetime as dt
    now = dt.now().replace(minute=0, second=0, microsecond=0)
    start = now.replace(hour=14) + timedelta(hours=0)
    end = start + timedelta(minutes=45)

    tb_id = str(_uuid.uuid4())
    job_id = str(_uuid.uuid4())
    patient_id = mango_row["id"] if mango_row else None

    job_data = json.dumps({
        "id": job_id,
        "required_skills": ["Avian", "General Practice"],
        "estimated_duration": 45,
        "patient_name": "Mango",
        "procedure": "Avian Wellness Exam",
        "soft_requirements": "",
        "scheduled_date": None,
        "scheduled_time": None,
    })

    resource_ids = [chen_row["id"], ws_room_row["id"]]

    with _get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO jobs VALUES (?,?)", (job_id, job_data))
        conn.execute(
            """INSERT OR IGNORE INTO timeblocks
               (id, job_id, resource_ids, start_time, end_time,
                patient_id, intake_status, followup_status, risk_level, status, clinic_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tb_id, job_id, json.dumps(resource_ids),
                start.isoformat(), end.isoformat(),
                patient_id, "not_started", "not_started", "medium", "scheduled",
                "clinic-westside",
            ),
        )
        # Seed risk score
        rs_id = str(_uuid.uuid4())
        conn.execute(
            """INSERT OR IGNORE INTO risk_scores
               (id, timeblock_id, risk_level, score, factors, calculated_at)
               VALUES (?,?,?,?,?,?)""",
            (
                rs_id, tb_id, "medium", 45,
                json.dumps(["First visit (+15)", "Avian specialist needed (+20)", "Advance booking (0)"]),
                dt.utcnow().isoformat(),
            ),
        )
    print("[SEED] Seeded 1 Westside appointment (Dr. Chen, Avian Wellness Exam)")

