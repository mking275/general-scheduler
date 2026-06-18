import sqlite3
import json
import os
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from .models import Resource, ResourceType, TimeBlock, TimeRange, Job
from .interfaces import BaseRepository

# Store the DB file next to this module (works locally and on Render's persistent disk)
_DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "scheduler.db"))


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                hard_skills TEXT NOT NULL,
                attributes TEXT,
                availability_windows TEXT
            );
            CREATE TABLE IF NOT EXISTS timeblocks (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                resource_ids TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
        """)


def _resource_from_row(row) -> Resource:
    now = datetime.now()
    start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    end = now.replace(hour=17, minute=0, second=0, microsecond=0)
    window = TimeRange(start_time=start, end_time=end)
    return Resource(
        id=UUID(row["id"]),
        name=row["name"],
        type=ResourceType(row["type"]),
        hard_skills=json.loads(row["hard_skills"]),
        attributes=row["attributes"],
        availability_windows=[window],
    )


def _timeblock_from_row(row) -> TimeBlock:
    return TimeBlock(
        id=UUID(row["id"]),
        job_id=UUID(row["job_id"]),
        resource_ids=[UUID(r) for r in json.loads(row["resource_ids"])],
        start_time=datetime.fromisoformat(row["start_time"]),
        end_time=datetime.fromisoformat(row["end_time"]),
    )


class InMemoryRepository(BaseRepository):
    """SQLite-backed repository (name kept for compatibility)."""

    def __init__(self):
        _init_db()
        self._seed_if_empty()

    def _seed_if_empty(self):
        with _get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        if count > 0:
            return  # Already seeded

        now = datetime.now()
        start = now.replace(hour=8, minute=0, second=0, microsecond=0)
        end = now.replace(hour=17, minute=0, second=0, microsecond=0)
        window = TimeRange(start_time=start, end_time=end)
        windows_json = json.dumps([{"start_time": start.isoformat(), "end_time": end.isoformat()}])

        seed_data = [
            # Vets
            (str(uuid4()), "Dr. Smith",  "Vet",  ["Surgery", "General Practice"],          "Experienced surgeon. Great with dogs. Prefers morning slots."),
            (str(uuid4()), "Dr. Jones",  "Vet",  ["Avian", "Exotics", "General Practice"], "Specialist in birds and exotic animals. Fast and precise."),
            (str(uuid4()), "Dr. Patel",  "Vet",  ["Surgery", "Dental", "General Practice"],"Dental and soft-tissue surgery specialist. Very thorough."),
            # Rooms
            (str(uuid4()), "Operating Room A", "Room", ["Surgery"],                             "Fully equipped surgical suite with anesthesia station."),
            (str(uuid4()), "Operating Room B", "Room", ["Surgery", "Dental"],                   "Surgical suite with dental equipment and overhead lighting."),
            (str(uuid4()), "Exam Room 1",       "Room", ["General Practice", "Avian", "Exotics"],"Standard exam room. Suitable for routine checkups and exotic animals."),
            (str(uuid4()), "Exam Room 2",       "Room", ["General Practice", "Vaccination"],     "Vaccination and wellness check room."),
            (str(uuid4()), "Grooming Suite",    "Room", ["Grooming"],                            "Dedicated grooming station with bathing and drying equipment."),
            (str(uuid4()), "Imaging Room",      "Room", ["X-Ray", "Ultrasound"],                 "Digital X-ray and ultrasound equipment. Lead-lined walls."),
            (str(uuid4()), "Isolation Ward",    "Room", ["General Practice", "Surgery"],         "Negative-pressure isolation room for infectious or post-op patients."),
        ]

        with _get_conn() as conn:
            for rid, name, rtype, skills, attrs in seed_data:
                conn.execute(
                    "INSERT OR IGNORE INTO resources VALUES (?,?,?,?,?,?)",
                    (rid, name, rtype, json.dumps(skills), attrs, windows_json),
                )

    # ------------------------------------------------------------------ #
    #  Resource methods
    # ------------------------------------------------------------------ #

    def get_all_resources(self) -> List[Resource]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM resources").fetchall()
        return [_resource_from_row(r) for r in rows]

    def get_resource(self, resource_id: UUID) -> Optional[Resource]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM resources WHERE id=?", (str(resource_id),)).fetchone()
        return _resource_from_row(row) if row else None

    # ------------------------------------------------------------------ #
    #  Job methods
    # ------------------------------------------------------------------ #

    def save_job(self, job: Job) -> Job:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?,?)",
                (str(job.id), job.model_dump_json()),
            )
        return job

    # ------------------------------------------------------------------ #
    #  TimeBlock methods
    # ------------------------------------------------------------------ #

    def save_timeblock(self, timeblock: TimeBlock) -> TimeBlock:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO timeblocks VALUES (?,?,?,?,?)",
                (
                    str(timeblock.id),
                    str(timeblock.job_id),
                    json.dumps([str(r) for r in timeblock.resource_ids]),
                    timeblock.start_time.isoformat(),
                    timeblock.end_time.isoformat(),
                ),
            )
        return timeblock

    def get_timeblocks(self, resource_id: UUID) -> List[TimeBlock]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM timeblocks").fetchall()
        result = []
        for row in rows:
            ids = json.loads(row["resource_ids"])
            if str(resource_id) in ids:
                result.append(_timeblock_from_row(row))
        return result


# Singleton
db = InMemoryRepository()
