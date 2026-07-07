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
    import uuid as _uuid_mod
    chen_id = str(_uuid_mod.uuid5(_uuid_mod.NAMESPACE_DNS, 'vet-chen'))
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
            "SELECT id FROM resources WHERE name='Dr. Chen' AND type='Vet' LIMIT 1"
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



def seed_phase3_data():
    """
    T005 + T006: Seed Phase 3 data.
    Guards against re-seeding with IF NOT EXISTS check on breed_protocols.
    G02: All historical dates use datetime.today() - timedelta(weeks=N) -- no hardcoded dates.
    """
    with _get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM breed_protocols").fetchone()[0]
    if count > 0:
        return  # Already seeded

    from datetime import date as _date, timedelta as _td
    import calendar

    today = _date.today()

    def add_months(d, months):
        y = d.year + (d.month - 1 + months) // 12
        m = (d.month - 1 + months) % 12 + 1
        day = min(d.day, calendar.monthrange(y, m)[1])
        return _date(y, m, day)

    # ------------------------------------------------------------------ #
    # Breed Protocols -- 12 entries (T005)
    # ------------------------------------------------------------------ #
    breed_entries = [
        ("bp-001", "Bulldog", "brachycephalic", "Anaesthesia Risk",
         "Brachycephalic breeds have narrow airways and are at elevated risk during general anaesthesia. "
         "Ensure pre-oxygenation, use short-acting agents, and have reversal agents ready. Monitor SpO2 closely post-procedure.",
         0, "critical"),
        ("bp-002", "Pug", "brachycephalic", "Anaesthesia Risk",
         "Pugs are extremely brachycephalic and require careful pre-anaesthetic workup. "
         "Avoid sedative pre-medications that suppress respiration. Maintain oxygen delivery throughout recovery.",
         0, "critical"),
        ("bp-003", "Boston Terrier", "brachycephalic", "Anaesthesia Risk",
         "Boston Terriers are brachycephalic. Pre-anaesthetic assessment should include evaluation for elongated soft palate. "
         "Use low-dose induction agents and ensure rapid intubation.",
         0, "critical"),
        ("bp-004", "Shih Tzu", "brachycephalic", "Airway Monitoring",
         "Shih Tzus are moderately brachycephalic. Monitor closely for respiratory distress in recovery. "
         "Keep head elevated post-procedure and avoid stress.",
         0, "warning"),
        ("bp-005", "Golden Retriever", "oncology", "Oncology Screening",
         "Golden Retrievers have an elevated lifetime risk of cancer (approx 60%). "
         "Annual blood panels including CBC and chemistry recommended from age 6. "
         "Lymph node palpation at every visit. Discuss cancer prevention with owner.",
         6, "warning"),
        ("bp-006", "Labrador", "oncology", "Oncology Screening",
         "Labradors are predisposed to soft-tissue sarcomas and mast cell tumours from age 7+. "
         "Full-body palpation at each visit. Consider annual chest X-ray for patients >8 years.",
         7, "info"),
        ("bp-007", "Cavalier King Charles", "cardiac", "Cardiac Monitoring",
         "CKCS are predisposed to Mitral Valve Disease (MVD) -- onset typically 4+ years. "
         "Annual cardiac auscultation mandatory. Refer to cardiologist if murmur detected. Follow EPIC trial protocol.",
         4, "warning"),
        ("bp-008", "Doberman", "cardiac", "DCM Screening",
         "Dobermans are highly predisposed to Dilated Cardiomyopathy (DCM). "
         "Annual cardiac echo and 24-hour Holter recommended from age 5. "
         "Holter may reveal occult DCM years before clinical signs.",
         5, "warning"),
        ("bp-009", "German Shepherd", "ortho", "Hip Dysplasia Protocol",
         "German Shepherds have a high rate of canine hip dysplasia (CHD). "
         "Hip radiographs recommended at 12-18 months for breeding assessment. "
         "PennHIP or OFA evaluation recommended. Monitor gait at each visit from age 1.",
         1, "info"),
        ("bp-010", "Dachshund", "ortho", "IVDD Risk",
         "Dachshunds are predisposed to intervertebral disc disease (IVDD). "
         "Avoid activities with excessive spinal loading. Monitor for back pain or hind limb weakness. "
         "Educate owners on ramp use and weight management from age 3.",
         3, "warning"),
        ("bp-011", "Maine Coon", "cardiac", "HCM Screening",
         "Maine Coons are predisposed to Hypertrophic Cardiomyopathy (HCM). "
         "Annual cardiac auscultation. Echo recommended every 2 years from age 3. "
         "MyBPC3 gene mutation screening available.",
         3, "warning"),
        ("bp-012", "Persian", "renal", "PKD Monitoring",
         "Persian cats carry a high prevalence of Polycystic Kidney Disease (PKD). "
         "DNA test recommended. Annual renal ultrasound from age 2. "
         "Monitor BUN/creatinine at every wellness visit.",
         2, "warning"),
    ]

    with _get_conn() as conn:
        for bp in breed_entries:
            conn.execute(
                "INSERT OR IGNORE INTO breed_protocols (id, breed_pattern, flag_type, title, detail, age_threshold_years, severity) VALUES (?,?,?,?,?,?,?)",
                bp
            )
    print("[SEED] Inserted {} breed protocols".format(len(breed_entries)))

    # ------------------------------------------------------------------ #
    # Care Protocols -- 8 entries (T005)
    # ------------------------------------------------------------------ #
    care_protocol_entries = [
        ("cp-001", "dog", "DHPP",          12),
        ("cp-002", "all", "Rabies",         12),
        ("cp-003", "dog", "Bordetella",      6),
        ("cp-004", "cat", "FVRCP",          12),
        ("cp-005", "cat", "FeLV",           12),
        ("cp-006", "dog", "Leptospirosis",  12),
        ("cp-007", "dog", "Heartworm Test", 12),
        ("cp-008", "all", "Dental",         12),
    ]

    with _get_conn() as conn:
        for cp in care_protocol_entries:
            conn.execute(
                "INSERT OR IGNORE INTO care_protocols (id, species, protocol_name, interval_months) VALUES (?,?,?,?)",
                cp
            )
    print("[SEED] Inserted {} care protocols".format(len(care_protocol_entries)))

    # ------------------------------------------------------------------ #
    # Lookup patient IDs
    # ------------------------------------------------------------------ #
    with _get_conn() as conn:
        buddy_row    = conn.execute("SELECT id FROM patients WHERE name='Buddy' LIMIT 1").fetchone()
        rex_row      = conn.execute("SELECT id FROM patients WHERE name='Rex' LIMIT 1").fetchone()
        luna_row     = conn.execute("SELECT id FROM patients WHERE name='Luna' LIMIT 1").fetchone()
        daisy_row    = conn.execute("SELECT id FROM patients WHERE name='Daisy' LIMIT 1").fetchone()
        whiskers_row = conn.execute("SELECT id FROM patients WHERE name='Whiskers' LIMIT 1").fetchone()

    buddy_id    = buddy_row["id"]    if buddy_row    else None
    rex_id      = rex_row["id"]      if rex_row      else None
    luna_id     = luna_row["id"]     if luna_row     else None
    daisy_id    = daisy_row["id"]    if daisy_row    else None
    whiskers_id = whiskers_row["id"] if whiskers_row else None

    # ------------------------------------------------------------------ #
    # Care Events (T005) -- overdue and upcoming
    # SC-P3-004: >= 2 overdue on startup
    # ------------------------------------------------------------------ #
    care_event_entries = []

    if buddy_id:
        buddy_dhpp_admin = add_months(today, -14)
        buddy_dhpp_due   = add_months(buddy_dhpp_admin, 12)
        care_event_entries.append({
            "id": "ce-buddy-dhpp", "patient_id": buddy_id, "protocol_id": "cp-001",
            "timeblock_id": None,
            "administered_date": buddy_dhpp_admin.isoformat(),
            "next_due_date":     buddy_dhpp_due.isoformat(),
            "batch_number": "LOT-4421", "administered_by": "Dr. Smith",
        })
        buddy_rabies_admin = add_months(today, -11)
        buddy_rabies_due   = today + _td(days=15)
        care_event_entries.append({
            "id": "ce-buddy-rabies", "patient_id": buddy_id, "protocol_id": "cp-002",
            "timeblock_id": None,
            "administered_date": buddy_rabies_admin.isoformat(),
            "next_due_date":     buddy_rabies_due.isoformat(),
            "batch_number": "LOT-7812", "administered_by": "Dr. Smith",
        })

    if rex_id:
        rex_dhpp_admin = add_months(today, -15)
        rex_dhpp_due   = add_months(rex_dhpp_admin, 12)
        care_event_entries.append({
            "id": "ce-rex-dhpp", "patient_id": rex_id, "protocol_id": "cp-001",
            "timeblock_id": None,
            "administered_date": rex_dhpp_admin.isoformat(),
            "next_due_date":     rex_dhpp_due.isoformat(),
            "batch_number": "LOT-3319", "administered_by": "Dr. Smith",
        })
        rex_bord_admin = add_months(today, -5)
        rex_bord_due   = today + _td(days=20)
        care_event_entries.append({
            "id": "ce-rex-bordetella", "patient_id": rex_id, "protocol_id": "cp-003",
            "timeblock_id": None,
            "administered_date": rex_bord_admin.isoformat(),
            "next_due_date":     rex_bord_due.isoformat(),
            "batch_number": "LOT-5502", "administered_by": "Dr. Smith",
        })

    if luna_id:
        luna_fvrcp_admin = add_months(today, -11)
        luna_fvrcp_due   = today + _td(days=10)
        care_event_entries.append({
            "id": "ce-luna-fvrcp", "patient_id": luna_id, "protocol_id": "cp-004",
            "timeblock_id": None,
            "administered_date": luna_fvrcp_admin.isoformat(),
            "next_due_date":     luna_fvrcp_due.isoformat(),
            "batch_number": "LOT-8891", "administered_by": "Dr. Jones",
        })

    if whiskers_id:
        wh_admin = add_months(today, -13)
        wh_due   = add_months(wh_admin, 12)
        care_event_entries.append({
            "id": "ce-whiskers-felv", "patient_id": whiskers_id, "protocol_id": "cp-005",
            "timeblock_id": None,
            "administered_date": wh_admin.isoformat(),
            "next_due_date":     wh_due.isoformat(),
            "batch_number": "LOT-2201", "administered_by": "Dr. Jones",
        })

    with _get_conn() as conn:
        for ce in care_event_entries:
            conn.execute(
                "INSERT OR IGNORE INTO care_events (id, patient_id, protocol_id, timeblock_id, administered_date, next_due_date, batch_number, administered_by) VALUES (?,?,?,?,?,?,?,?)",
                (ce["id"], ce["patient_id"], ce["protocol_id"], ce.get("timeblock_id"),
                 ce["administered_date"], ce["next_due_date"], ce["batch_number"], ce["administered_by"])
            )
    print("[SEED] Inserted {} care events".format(len(care_event_entries)))

    # ------------------------------------------------------------------ #
    # Waitlist -- 3 entries with varied urgency (T005)
    # ------------------------------------------------------------------ #
    waitlist_entries = []
    if daisy_id:
        waitlist_entries.append({
            "id": "wl-daisy-dental", "patient_id": daisy_id,
            "clinic_id": "clinic-downtown", "procedure_type": "Dental Cleaning",
            "preferred_vet_id": None, "urgency": "asap", "offer_status": "waiting",
            "join_date": (datetime.today() - timedelta(days=5)).isoformat(),
        })
    if rex_id:
        waitlist_entries.append({
            "id": "wl-rex-wellness", "patient_id": rex_id,
            "clinic_id": "clinic-downtown", "procedure_type": "Wellness Exam",
            "preferred_vet_id": None, "urgency": "within_week", "offer_status": "waiting",
            "join_date": (datetime.today() - timedelta(days=3)).isoformat(),
        })
    if luna_id:
        waitlist_entries.append({
            "id": "wl-luna-vaccination", "patient_id": luna_id,
            "clinic_id": "clinic-downtown", "procedure_type": "Vaccination",
            "preferred_vet_id": None, "urgency": "flexible", "offer_status": "waiting",
            "join_date": (datetime.today() - timedelta(days=1)).isoformat(),
        })

    with _get_conn() as conn:
        for wl in waitlist_entries:
            conn.execute(
                "INSERT OR IGNORE INTO waitlist (id, patient_id, clinic_id, procedure_type, preferred_vet_id, urgency, offer_status, join_date) VALUES (?,?,?,?,?,?,?,?)",
                (wl["id"], wl["patient_id"], wl["clinic_id"], wl["procedure_type"],
                 wl.get("preferred_vet_id"), wl["urgency"], wl["offer_status"], wl["join_date"])
            )
    print("[SEED] Inserted {} waitlist entries".format(len(waitlist_entries)))

    # ------------------------------------------------------------------ #
    # Prescriptions -- 2 active Rx (T005)
    # ------------------------------------------------------------------ #
    rx_entries = []
    if buddy_id:
        rx_entries.append({
            "id": "rx-buddy-carprofen", "patient_id": buddy_id, "timeblock_id": None,
            "drug_name": "Carprofen", "dose": "25mg", "frequency": "BID",
            "duration_days": 14, "refills_remaining": 2,
            "supply_ends_at": (today + _td(days=7)).isoformat(),
            "issued_by": "Dr. Smith",
            "issued_date": (today - _td(days=7)).isoformat(),
        })
    if rex_id:
        rx_entries.append({
            "id": "rx-rex-gabapentin", "patient_id": rex_id, "timeblock_id": None,
            "drug_name": "Gabapentin", "dose": "100mg", "frequency": "TID",
            "duration_days": 14, "refills_remaining": 1,
            "supply_ends_at": (today + _td(days=7)).isoformat(),
            "issued_by": "Dr. Smith",
            "issued_date": (today - _td(days=14)).isoformat(),
        })

    with _get_conn() as conn:
        for rx in rx_entries:
            conn.execute(
                "INSERT OR IGNORE INTO prescriptions (id, patient_id, timeblock_id, drug_name, dose, frequency, duration_days, refills_remaining, supply_ends_at, issued_by, issued_date) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rx["id"], rx["patient_id"], rx.get("timeblock_id"), rx["drug_name"],
                 rx["dose"], rx["frequency"], rx["duration_days"], rx["refills_remaining"],
                 rx["supply_ends_at"], rx["issued_by"], rx["issued_date"])
            )
    print("[SEED] Inserted {} prescriptions".format(len(rx_entries)))

    # ------------------------------------------------------------------ #
    # T006: Historical completed timeblocks for forecast linear regression
    # 8 weeks, clinic-downtown, slight upward trend
    # G02: All dates use datetime.today() - timedelta(weeks=N) -- no hardcoded dates
    # ------------------------------------------------------------------ #
    weekly_counts = [8, 9, 9, 10, 10, 11, 12, 13]  # oldest-first

    with _get_conn() as conn:
        smith_row = conn.execute("SELECT id FROM resources WHERE name='Dr. Smith' LIMIT 1").fetchone()
        room_row  = conn.execute("SELECT id FROM resources WHERE name='Exam Room 1' LIMIT 1").fetchone()
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM timeblocks WHERE status='complete' AND clinic_id='clinic-downtown'"
        ).fetchone()[0]

    if existing_count < 10 and smith_row and room_row:
        smith_id  = smith_row["id"]
        room_id   = room_row["id"]
        resource_ids_json = json.dumps([smith_id, room_id])

        hist_entries = []
        for week_back, appt_count in enumerate(reversed(weekly_counts), start=1):
            week_start = datetime.today() - timedelta(weeks=week_back)
            for appt_idx in range(appt_count):
                hour_offset = 8 + (appt_idx % 8)
                start_dt = week_start.replace(
                    hour=hour_offset, minute=0, second=0, microsecond=0
                ) + timedelta(days=appt_idx // 8)
                end_dt = start_dt + timedelta(minutes=60)
                tb_id  = str(_uuid.uuid4())
                job_id = str(_uuid.uuid4())
                job_data = json.dumps({
                    "id": job_id, "required_skills": ["General Practice"],
                    "estimated_duration": 60, "patient_name": None,
                    "procedure": "Wellness Exam", "soft_requirements": "",
                    "scheduled_date": None, "scheduled_time": None,
                })
                hist_entries.append((tb_id, job_id, job_data, start_dt, end_dt))

        with _get_conn() as conn:
            for tb_id, job_id, job_data, start_dt, end_dt in hist_entries:
                conn.execute("INSERT OR IGNORE INTO jobs VALUES (?,?)", (job_id, job_data))
                conn.execute(
                    """INSERT OR IGNORE INTO timeblocks
                       (id, job_id, resource_ids, start_time, end_time,
                        patient_id, intake_status, followup_status, risk_level, status, clinic_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (tb_id, job_id, resource_ids_json,
                     start_dt.isoformat(), end_dt.isoformat(),
                     None, "not_started", "not_started", "low", "complete",
                     "clinic-downtown"),
                )
        print("[SEED] Inserted {} historical completed timeblocks for forecast regression".format(len(hist_entries)))
    else:
        print("[SEED] Skipping historical timeblock seed -- already {} complete records".format(existing_count))

    print("[SEED] Phase 3 seed complete.")
