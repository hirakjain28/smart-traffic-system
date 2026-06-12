# backend/database/models.py

"""
DATABASE MODELS — Table definitions

Each class here = one table in the SQLite database.

WHY THESE TABLES?

TrafficSnapshot:
  Records what the traffic looked like at each simulation step.
  Lets us build historical charts on the dashboard.
  "How was traffic at 2:30 PM vs 5:00 PM?"

SignalDecision:
  Records every decision the AI made.
  "At step 45, AI said SWITCH because NS wait=120s, EW wait=5s"
  Lets operators review AI behavior and audit decisions.

OverrideLog:
  Records every time an operator manually changed a signal.
  "Operator forced NS green at 14:32 for 45 seconds"
  Essential for safety auditing in a real system.
"""

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TrafficSnapshot(Base):
    """
    One row = traffic state at one simulation step.
    Saved every DELTA_TIME seconds.
    """
    __tablename__ = "traffic_snapshots"

    id           = Column(Integer, primary_key=True, index=True)
    timestamp    = Column(DateTime, default=datetime.utcnow)
    step         = Column(Integer)                    # simulation step number

    # Queue lengths (number of stopped cars)
    queue_north  = Column(Integer, default=0)
    queue_south  = Column(Integer, default=0)
    queue_east   = Column(Integer, default=0)
    queue_west   = Column(Integer, default=0)

    # Waiting times (cumulative seconds)
    wait_north   = Column(Float, default=0.0)
    wait_south   = Column(Float, default=0.0)
    wait_east    = Column(Float, default=0.0)
    wait_west    = Column(Float, default=0.0)

    # Vehicle counts
    vehicles_north = Column(Integer, default=0)
    vehicles_south = Column(Integer, default=0)
    vehicles_east  = Column(Integer, default=0)
    vehicles_west  = Column(Integer, default=0)

    # Current signal phase
    current_phase  = Column(Integer, default=0)
    time_in_phase  = Column(Float, default=0.0)

    # Totals
    total_wait     = Column(Float, default=0.0)
    total_queue    = Column(Integer, default=0)


class SignalDecision(Base):
    """
    One row = one AI decision.
    Records what the AI saw and what it decided.
    """
    __tablename__ = "signal_decisions"

    id              = Column(Integer, primary_key=True, index=True)
    timestamp       = Column(DateTime, default=datetime.utcnow)
    step            = Column(Integer)

    # What the AI decided
    action          = Column(Integer)          # 0=KEEP, 1=SWITCH
    action_label    = Column(String)           # "KEEP" or "SWITCH"
    was_overridden  = Column(Boolean, default=False)
    override_reason = Column(String, nullable=True)

    # Context at time of decision
    phase_before    = Column(Integer)
    phase_after     = Column(Integer)
    total_wait      = Column(Float)
    reward          = Column(Float)

    # Control mode when decision was made
    ai_mode         = Column(Boolean, default=True)  # True=AI, False=Manual


class OverrideLog(Base):
    """
    One row = one manual operator override.
    """
    __tablename__ = "override_logs"

    id            = Column(Integer, primary_key=True, index=True)
    timestamp     = Column(DateTime, default=datetime.utcnow)

    operator_id   = Column(String, default="operator")
    forced_phase  = Column(Integer)               # which phase was forced
    forced_duration = Column(Integer, nullable=True)  # how long (seconds)
    reason        = Column(String, nullable=True)  # why operator overrode