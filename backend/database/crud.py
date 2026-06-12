# backend/database/crud.py

"""
CRUD OPERATIONS — Create, Read, Update, Delete

These functions are the ONLY way our app talks to the database.
All database logic lives here — routes just call these functions.

WHY ISOLATE DB LOGIC?
If we ever switch from SQLite to PostgreSQL,
we only change these functions — not every route.

WHY NOT JUST WRITE SQL STRINGS?
SQLAlchemy ORM prevents SQL injection attacks automatically.
It's also more readable and Pythonic.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.database.models import TrafficSnapshot, SignalDecision, OverrideLog
from datetime import datetime


# ── TRAFFIC SNAPSHOTS ─────────────────────────────────────────────────────────

def save_traffic_snapshot(db: Session, step: int, traffic_data: dict,
                           current_phase: int, time_in_phase: float):
    """
    Saves one traffic state snapshot to the database.
    Called every simulation step.
    """
    q = traffic_data.get("queue", {})
    w = traffic_data.get("wait", {})
    v = traffic_data.get("vehicles", {})

    snapshot = TrafficSnapshot(
        step           = step,
        queue_north    = q.get("north", 0),
        queue_south    = q.get("south", 0),
        queue_east     = q.get("east", 0),
        queue_west     = q.get("west", 0),
        wait_north     = w.get("north", 0.0),
        wait_south     = w.get("south", 0.0),
        wait_east      = w.get("east", 0.0),
        wait_west      = w.get("west", 0.0),
        vehicles_north = v.get("north", 0),
        vehicles_south = v.get("south", 0),
        vehicles_east  = v.get("east", 0),
        vehicles_west  = v.get("west", 0),
        current_phase  = current_phase,
        time_in_phase  = time_in_phase,
        total_wait     = sum(w.values()),
        total_queue    = sum(q.values()),
    )
    db.add(snapshot)
    db.commit()
    return snapshot


def get_recent_snapshots(db: Session, limit: int = 50):
    """Returns the most recent N traffic snapshots."""
    return db.query(TrafficSnapshot)\
             .order_by(desc(TrafficSnapshot.timestamp))\
             .limit(limit).all()


# ── SIGNAL DECISIONS ──────────────────────────────────────────────────────────

def save_signal_decision(db: Session, step: int, action: int,
                          action_label: str, was_overridden: bool,
                          override_reason: str, phase_before: int,
                          phase_after: int, total_wait: float,
                          reward: float, ai_mode: bool):
    """Saves one AI decision to the database."""
    decision = SignalDecision(
        step            = step,
        action          = action,
        action_label    = action_label,
        was_overridden  = was_overridden,
        override_reason = override_reason,
        phase_before    = phase_before,
        phase_after     = phase_after,
        total_wait      = total_wait,
        reward          = reward,
        ai_mode         = ai_mode,
    )
    db.add(decision)
    db.commit()
    return decision


def get_recent_decisions(db: Session, limit: int = 20):
    """Returns the most recent N AI decisions."""
    return db.query(SignalDecision)\
             .order_by(desc(SignalDecision.timestamp))\
             .limit(limit).all()


# ── OVERRIDE LOGS ─────────────────────────────────────────────────────────────

def save_override(db: Session, forced_phase: int,
                  forced_duration: int = None, reason: str = None):
    """Saves an operator override to the database."""
    override = OverrideLog(
        forced_phase    = forced_phase,
        forced_duration = forced_duration,
        reason          = reason,
    )
    db.add(override)
    db.commit()
    return override


def get_recent_overrides(db: Session, limit: int = 10):
    """Returns the most recent N operator overrides."""
    return db.query(OverrideLog)\
             .order_by(desc(OverrideLog.timestamp))\
             .limit(limit).all()