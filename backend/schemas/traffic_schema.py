# backend/schemas/traffic_schema.py

"""
PYDANTIC SCHEMAS — Data validation and serialization

WHY PYDANTIC?
When the dashboard sends data TO the backend (e.g., an override request),
we need to validate it: "Is the phase number valid? Is it an integer?"

When the backend sends data TO the dashboard,
we need to serialize it: "Convert Python objects to JSON"

Pydantic handles both automatically.
If data doesn't match the schema → FastAPI returns a 422 error automatically.

SCHEMA vs MODEL:
  Database Model  = defines how data is stored  (SQLAlchemy)
  Pydantic Schema = defines how data looks in API (Pydantic)
  They're separate on purpose — DB structure ≠ API structure.
"""

from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


# ── TRAFFIC DATA SCHEMAS ──────────────────────────────────────────────────────

class QueueData(BaseModel):
    """Queue lengths for each direction."""
    north: int = 0
    south: int = 0
    east:  int = 0
    west:  int = 0


class WaitData(BaseModel):
    """Waiting times for each direction."""
    north: float = 0.0
    south: float = 0.0
    east:  float = 0.0
    west:  float = 0.0


class VehicleData(BaseModel):
    """Vehicle counts for each direction."""
    north: int = 0
    south: int = 0
    east:  int = 0
    west:  int = 0


class TrafficStatus(BaseModel):
    """
    Complete traffic status snapshot.
    This is what the dashboard receives every tick.
    """
    step:          int
    timestamp:     str
    queue:         QueueData
    wait:          WaitData
    vehicles:      VehicleData
    current_phase: int
    phase_name:    str       # "NS Green", "NS Yellow", etc.
    time_in_phase: float
    total_wait:    float
    total_queue:   int
    ai_mode:       bool      # True = AI controlling, False = Manual


class SignalState(BaseModel):
    """Current state of the traffic signal."""
    intersection_id: str
    current_phase:   int
    phase_name:      str
    time_in_phase:   float
    ai_mode:         bool
    last_switch:     Optional[str] = None


# ── AI SUGGESTION SCHEMA ──────────────────────────────────────────────────────

class AISuggestion(BaseModel):
    """
    What the AI recommends doing right now.
    Shown on the dashboard even in manual mode.
    """
    recommended_action:  str      # "KEEP" or "SWITCH"
    confidence:          float    # how confident (Q-value difference)
    reason:              str      # human-readable explanation
    current_wait:        float    # total current wait time
    predicted_improvement: float  # estimated wait reduction if followed


# ── OVERRIDE REQUEST SCHEMA ───────────────────────────────────────────────────

class OverrideRequest(BaseModel):
    """
    Sent by operator to force a specific signal phase.
    
    Example JSON body:
    {
        "phase": 0,
        "duration": 30,
        "reason": "Emergency vehicle on North road"
    }
    """
    phase:    int              # which phase to force (0, 1, 2, 3)
    duration: Optional[int] = None   # how long to hold it (None = until next AI step)
    reason:   Optional[str] = None   # why the operator is overriding


class OverrideResponse(BaseModel):
    """Response after an override is applied."""
    success:      bool
    message:      str
    phase_forced: int
    timestamp:    str


# ── WEBSOCKET MESSAGE SCHEMA ──────────────────────────────────────────────────

class LiveUpdate(BaseModel):
    """
    Structure of messages sent over the WebSocket connection.
    The dashboard receives these every DELTA_TIME seconds.
    """
    type:       str           # "traffic_update", "signal_change", "override"
    data:       dict          # the actual payload
    timestamp:  str