"""
008 — Vera Onboarding Repository
All DB operations for the 6 onboarding tables.
No ORM — raw sqlite3 via stdlib, consistent with existing repository.py pattern.
"""
import os
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4

DB_PATH = os.path.join(os.path.dirname(__file__), "scheduler.db")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row(row) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)


class OnboardingRepository:
    """
    Repository for all onboarding-related DB operations.
    Follows the same sqlite3 stdlib pattern used in repository.py.
    """

    # ------------------------------------------------------------------
    # T001 — init_db: create all 6 tables + uploads directory
    # ------------------------------------------------------------------

    def init_db(self):
        """Create all 6 onboarding tables if they do not already exist."""
        os.makedirs(UPLOADS_DIR, exist_ok=True)

        with _get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS onboarding_sessions (
                    id               TEXT PRIMARY KEY,
                    session_token    TEXT UNIQUE NOT NULL,
                    email_anchor     TEXT,
                    persona_role     TEXT,
                    phase            INTEGER NOT NULL DEFAULT 0,
                    track            TEXT DEFAULT 'greenfield',
                    practice_name    TEXT,
                    state_json       TEXT DEFAULT '{}',
                    activation_timestamp TEXT,
                    created_at       TEXT NOT NULL,
                    updated_at       TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS magic_links (
                    id                TEXT PRIMARY KEY,
                    session_id        TEXT NOT NULL REFERENCES onboarding_sessions(id),
                    email             TEXT NOT NULL,
                    token_hash        TEXT UNIQUE NOT NULL,
                    expires_at        TEXT NOT NULL,
                    used_at           TEXT,
                    device_fingerprint TEXT,
                    created_at        TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS logo_assets (
                    id           TEXT PRIMARY KEY,
                    session_id   TEXT NOT NULL REFERENCES onboarding_sessions(id),
                    source_type  TEXT NOT NULL,
                    source_url   TEXT,
                    local_path   TEXT,
                    confirmed    INTEGER NOT NULL DEFAULT 0,
                    fallback_type TEXT,
                    initials     TEXT,
                    created_at   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS onboarding_documents (
                    id               TEXT PRIMARY KEY,
                    session_id       TEXT NOT NULL REFERENCES onboarding_sessions(id),
                    mime_type        TEXT NOT NULL,
                    file_size_bytes  INTEGER NOT NULL,
                    storage_path     TEXT NOT NULL,
                    classified_type  TEXT,
                    extraction_json  TEXT DEFAULT '{}',
                    streaming_status TEXT DEFAULT 'pending',
                    created_at       TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS extracted_entities (
                    id               TEXT PRIMARY KEY,
                    document_id      TEXT NOT NULL REFERENCES onboarding_documents(id),
                    entity_type      TEXT NOT NULL,
                    source_text      TEXT,
                    source_position  TEXT,
                    confidence       REAL NOT NULL DEFAULT 0.5,
                    extracted_fields TEXT DEFAULT '{}',
                    has_conflict     INTEGER DEFAULT 0,
                    requires_input   INTEGER DEFAULT 0,
                    confirmed        INTEGER DEFAULT 0,
                    created_at       TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS extraction_corrections (
                    id                       TEXT PRIMARY KEY,
                    entity_id                TEXT NOT NULL REFERENCES extracted_entities(id),
                    document_type            TEXT NOT NULL,
                    field_name               TEXT NOT NULL,
                    vera_value               TEXT NOT NULL,
                    correct_value            TEXT NOT NULL,
                    confidence_at_correction REAL NOT NULL,
                    corrected_at             TEXT NOT NULL
                );
            """)

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def create_session(self, device_fingerprint: Optional[str] = None) -> dict:
        """Create a new onboarding session, return the full session dict."""
        session_id = str(uuid4())
        session_token = str(uuid4())
        now = datetime.utcnow().isoformat()
        state = json.dumps({"device_fingerprint": device_fingerprint} if device_fingerprint else {})

        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO onboarding_sessions
                   (id, session_token, phase, track, state_json, created_at, updated_at)
                   VALUES (?, ?, 0, 'greenfield', ?, ?, ?)""",
                (session_id, session_token, state, now, now),
            )
        return {
            "session_id": session_id,
            "session_token": session_token,
            "phase": 0,
            "track": "greenfield",
            "state_json": {},
            "persona_role": None,
            "practice_name": None,
            "email_anchor": None,
            "created_at": now,
            "updated_at": now,
        }

    def get_session_by_token(self, token: str) -> Optional[dict]:
        """Retrieve session by cookie token."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM onboarding_sessions WHERE session_token=?", (token,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["state_json"] = json.loads(d.get("state_json") or "{}")
        except Exception:
            d["state_json"] = {}
        return d

    def get_session_by_id(self, session_id: str) -> Optional[dict]:
        """Retrieve session by primary key."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM onboarding_sessions WHERE id=?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["state_json"] = json.loads(d.get("state_json") or "{}")
        except Exception:
            d["state_json"] = {}
        return d

    def patch_session(self, session_id: str, **kwargs) -> Optional[dict]:
        """Update arbitrary fields on the session. Only whitelisted fields allowed."""
        allowed = {"phase", "persona_role", "practice_name", "track", "state_json", "email_anchor", "activation_timestamp"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_session_by_id(session_id)

        # Serialize state_json if dict
        if "state_json" in updates and isinstance(updates["state_json"], dict):
            updates["state_json"] = json.dumps(updates["state_json"])

        now = datetime.utcnow().isoformat()
        updates["updated_at"] = now

        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [session_id]
        with _get_conn() as conn:
            conn.execute(
                f"UPDATE onboarding_sessions SET {set_clause} WHERE id=?", values
            )
        return self.get_session_by_id(session_id)

    # ------------------------------------------------------------------
    # Magic link operations
    # ------------------------------------------------------------------

    def create_magic_link(self, session_id: str, email: str,
                          device_fingerprint: Optional[str] = None) -> dict:
        """
        Generate a magic link. Returns the raw token (for demo console delivery).
        Only the SHA-256 hash is stored.
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        link_id = str(uuid4())
        now = datetime.utcnow()
        expires_at = (now + timedelta(days=30)).isoformat()
        created_at = now.isoformat()

        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO magic_links
                   (id, session_id, email, token_hash, expires_at, device_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (link_id, session_id, email, token_hash, expires_at, device_fingerprint, created_at),
            )
        # Also update session with email anchor
        self.patch_session(session_id, email_anchor=email)

        return {
            "id": link_id,
            "session_id": session_id,
            "email": email,
            "raw_token": raw_token,  # returned to caller for demo delivery
            "expires_at": expires_at,
            "created_at": created_at,
        }

    def consume_magic_link(self, raw_token: str) -> Optional[dict]:
        """
        Verify token, check expiry, mark used. Returns session dict on success.
        Returns None if token invalid, expired, or already used.
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = datetime.utcnow().isoformat()

        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM magic_links WHERE token_hash=?", (token_hash,)
            ).fetchone()

        if row is None:
            return None

        link = dict(row)
        if link.get("used_at"):
            return None  # already used

        if link["expires_at"] < now:
            return None  # expired

        # Mark used
        with _get_conn() as conn:
            conn.execute(
                "UPDATE magic_links SET used_at=? WHERE id=?", (now, link["id"])
            )

        return self.get_session_by_id(link["session_id"])

    # ------------------------------------------------------------------
    # Logo asset operations
    # ------------------------------------------------------------------

    def create_logo_asset(self, session_id: str, source_type: str,
                           source_url: Optional[str], initials: Optional[str],
                           local_path: Optional[str] = None) -> dict:
        asset_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        fallback_type = "monogram" if source_type == "monogram" else "image"

        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO logo_assets
                   (id, session_id, source_type, source_url, local_path, confirmed, fallback_type, initials, created_at)
                   VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                (asset_id, session_id, source_type, source_url, local_path, fallback_type, initials, now),
            )
        return {
            "id": asset_id,
            "session_id": session_id,
            "source_type": source_type,
            "source_url": source_url,
            "local_path": local_path,
            "confirmed": False,
            "fallback_type": fallback_type,
            "initials": initials,
            "created_at": now,
        }

    def confirm_logo_asset(self, asset_id: str) -> Optional[dict]:
        with _get_conn() as conn:
            # Fetch session_id to unconfirm other assets for same session
            row = conn.execute("SELECT session_id FROM logo_assets WHERE id=?", (asset_id,)).fetchone()
            if row is None:
                return None
            session_id = row["session_id"]
            # Unconfirm all others, confirm this one
            conn.execute("UPDATE logo_assets SET confirmed=0 WHERE session_id=?", (session_id,))
            conn.execute("UPDATE logo_assets SET confirmed=1 WHERE id=?", (asset_id,))
            row = conn.execute("SELECT * FROM logo_assets WHERE id=?", (asset_id,)).fetchone()
        return _row(row)

    def get_logo_assets_for_session(self, session_id: str) -> List[dict]:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM logo_assets WHERE session_id=? ORDER BY created_at", (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    def create_document(self, session_id: str, mime_type: str,
                         file_size_bytes: int, storage_path: str) -> dict:
        doc_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO onboarding_documents
                   (id, session_id, mime_type, file_size_bytes, storage_path,
                    extraction_json, streaming_status, created_at)
                   VALUES (?, ?, ?, ?, ?, '{}', 'pending', ?)""",
                (doc_id, session_id, mime_type, file_size_bytes, storage_path, now),
            )
        return {
            "id": doc_id,
            "session_id": session_id,
            "mime_type": mime_type,
            "file_size_bytes": file_size_bytes,
            "storage_path": storage_path,
            "classified_type": None,
            "extraction_json": {},
            "streaming_status": "pending",
            "created_at": now,
        }

    def update_document_status(self, doc_id: str, streaming_status: str,
                                classified_type: Optional[str] = None):
        updates = {"streaming_status": streaming_status}
        if classified_type:
            updates["classified_type"] = classified_type
        set_clause = ", ".join(f"{k}=?" for k in updates)
        with _get_conn() as conn:
            conn.execute(
                f"UPDATE onboarding_documents SET {set_clause} WHERE id=?",
                list(updates.values()) + [doc_id],
            )

    def get_document(self, doc_id: str) -> Optional[dict]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM onboarding_documents WHERE id=?", (doc_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["extraction_json"] = json.loads(d.get("extraction_json") or "{}")
        except Exception:
            d["extraction_json"] = {}
        return d

    # ------------------------------------------------------------------
    # Extracted entity operations
    # ------------------------------------------------------------------

    def create_extracted_entity(self, document_id: str, entity_type: str,
                                  source_text: str, confidence: float,
                                  fields: dict, position: Optional[dict] = None) -> dict:
        entity_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        requires_input = 1 if confidence < 0.7 else 0

        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO extracted_entities
                   (id, document_id, entity_type, source_text, source_position,
                    confidence, extracted_fields, has_conflict, requires_input, confirmed, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 0, ?)""",
                (
                    entity_id, document_id, entity_type, source_text,
                    json.dumps(position or {}), confidence,
                    json.dumps(fields), requires_input, now,
                ),
            )
        return {
            "id": entity_id,
            "document_id": document_id,
            "entity_type": entity_type,
            "source_text": source_text,
            "source_position": position or {},
            "confidence": confidence,
            "extracted_fields": fields,
            "has_conflict": False,
            "requires_input": bool(requires_input),
            "confirmed": False,
            "created_at": now,
        }

    def confirm_entity(self, entity_id: str) -> Optional[dict]:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE extracted_entities SET confirmed=1 WHERE id=?", (entity_id,)
            )
            row = conn.execute(
                "SELECT * FROM extracted_entities WHERE id=?", (entity_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["extracted_fields"] = json.loads(d.get("extracted_fields") or "{}")
            d["source_position"] = json.loads(d.get("source_position") or "{}")
        except Exception:
            pass
        return d

    def correct_entity(self, entity_id: str, field_name: str,
                        vera_value: str, correct_value: str,
                        confidence: float) -> dict:
        """Log a correction as a training signal, then confirm the entity."""
        corr_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # Get document type for the correction record
        with _get_conn() as conn:
            row = conn.execute(
                """SELECT e.document_id, d.classified_type
                   FROM extracted_entities e
                   JOIN onboarding_documents d ON d.id = e.document_id
                   WHERE e.id=?""",
                (entity_id,),
            ).fetchone()
        doc_type = row["classified_type"] if row else "unknown"

        # Update the entity's extracted_fields with the correction
        entity = self.confirm_entity(entity_id)
        if entity:
            fields = entity.get("extracted_fields", {})
            fields[field_name] = correct_value
            with _get_conn() as conn:
                conn.execute(
                    "UPDATE extracted_entities SET extracted_fields=? WHERE id=?",
                    (json.dumps(fields), entity_id),
                )

        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO extraction_corrections
                   (id, entity_id, document_type, field_name, vera_value,
                    correct_value, confidence_at_correction, corrected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (corr_id, entity_id, doc_type, field_name, vera_value,
                 correct_value, confidence, now),
            )
        return {
            "id": corr_id,
            "entity_id": entity_id,
            "document_type": doc_type,
            "field_name": field_name,
            "vera_value": vera_value,
            "correct_value": correct_value,
            "confidence_at_correction": confidence,
            "corrected_at": now,
        }

    def get_entity(self, entity_id: str) -> Optional[dict]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM extracted_entities WHERE id=?", (entity_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["extracted_fields"] = json.loads(d.get("extracted_fields") or "{}")
            d["source_position"] = json.loads(d.get("source_position") or "{}")
        except Exception:
            pass
        return d

    def get_confirmed_entities(self, session_id: str) -> List[dict]:
        """Return all confirmed entities for a session (across all documents)."""
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT e.*
                   FROM extracted_entities e
                   JOIN onboarding_documents d ON d.id = e.document_id
                   WHERE d.session_id=? AND e.confirmed=1
                   ORDER BY e.created_at""",
                (session_id,),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["extracted_fields"] = json.loads(d.get("extracted_fields") or "{}")
                d["source_position"] = json.loads(d.get("source_position") or "{}")
            except Exception:
                pass
            result.append(d)
        return result

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def set_activation(self, session_id: str, booking_id: str) -> dict:
        now = datetime.utcnow().isoformat()
        state_update = json.dumps({"activation_booking_id": booking_id})
        with _get_conn() as conn:
            conn.execute(
                """UPDATE onboarding_sessions
                   SET activation_timestamp=?, phase=6, updated_at=?
                   WHERE id=?""",
                (now, now, session_id),
            )
        return {"activated_at": now, "session_id": session_id, "booking_id": booking_id}


# Singleton instance — initialized on startup
onboarding_repo = OnboardingRepository()
