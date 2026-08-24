"""
Activity Logger — Persistent Disk-Backed Audit Event Log for Platform Administrators.

Captures key operational, administrative, and clinical events:
- User Registrations
- Athlete <-> Professional Linking & Unlinking (both directions)
- Admin Status Updates & Account Deletions
- Video Uploads & Risk Classification
- Video Deletions
- PDF Clinical Report Exports

Persists state to database/activity_logs.json across server reloads and restarts.
"""

import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DB_DIR = os.path.join(_BASE_DIR, "database")
_LOG_FILE = os.path.join(_DB_DIR, "activity_logs.json")

_lock = threading.Lock()
MAX_AUDIT_EVENTS = 500


def _load_events() -> List[Dict[str, Any]]:
    """Loads audit events from persistent storage."""
    os.makedirs(_DB_DIR, exist_ok=True)
    if os.path.exists(_LOG_FILE):
        try:
            with open(_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def _save_events_unlocked(events: List[Dict[str, Any]]) -> None:
    """Saves audit events list to persistent file."""
    try:
        os.makedirs(_DB_DIR, exist_ok=True)
        with open(_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
    except Exception:
        pass


def log_activity(
    event: str,
    user_name: str,
    user_email: str,
    user_role: str,
    details: str,
    filename: Optional[str] = None,
    session_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    duration_seconds: Optional[float] = None,
) -> None:
    """Record an audit event into the persistent platform activity stream."""
    with _lock:
        events = _load_events()
        entry = {
            "session_id": session_id or "",
            "event": event,
            "user_name": user_name,
            "user_email": user_email,
            "user_role": user_role,
            "details": details,
            "filename": filename or details,
            "risk_level": risk_level or "—",
            "duration_seconds": duration_seconds,
            "created_at": datetime.utcnow().isoformat(),
        }
        events.insert(0, entry)  # Newest first
        if len(events) > MAX_AUDIT_EVENTS:
            events = events[:MAX_AUDIT_EVENTS]
        _save_events_unlocked(events)


def get_all_activity_events() -> List[Dict[str, Any]]:
    """Retrieve all logged audit events, newest first."""
    with _lock:
        events = _load_events()
    return events
