# backend/api/routes/traffic.py

"""
TRAFFIC ROUTES — HTTP endpoints for traffic data

These are the REST API endpoints the dashboard calls
to get current traffic state and history.

ENDPOINT SUMMARY:
  GET /api/traffic/status     → current state right now
  GET /api/traffic/history    → last N snapshots
  GET /api/traffic/summary    → aggregate stats
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.db import get_db
from backend.database.crud import get_recent_snapshots
from backend.schemas.traffic_schema import TrafficStatus

router = APIRouter(prefix="/api/traffic", tags=["traffic"])


@router.get("/status")
async def get_traffic_status(simulation_service=None):
    """
    Returns the CURRENT traffic state.
    Called by the dashboard to refresh data.
    
    Response example:
    {
        "step": 45,
        "current_phase": 0,
        "phase_name": "NS Green",
        "traffic": {
            "queue": {"north": 3, "south": 2, "east": 0, "west": 1},
            "wait":  {"north": 45.0, ...}
        },
        "ai_mode": true
    }
    """
    from backend.main import sim_service
    snapshot = sim_service.state.get_snapshot()

    # Build clean response
    traffic = snapshot.get("traffic", {})
    return {
        "step":          snapshot.get("step", 0),
        "timestamp":     snapshot.get("timestamp", datetime.utcnow().isoformat()),
        "phase":         snapshot.get("current_phase", 0),
        "phase_name":    snapshot.get("phase_name", "Unknown"),
        "time_in_phase": snapshot.get("time_in_phase", 0),
        "queue":         traffic.get("queue", {}),
        "wait":          traffic.get("wait", {}),
        "vehicles":      traffic.get("vehicles", {}),
        "total_wait":    sum(traffic.get("wait", {}).values()),
        "total_queue":   sum(traffic.get("queue", {}).values()),
        "last_action":   snapshot.get("last_action"),
        "last_reward":   snapshot.get("last_reward"),
        "ai_mode":       snapshot.get("ai_mode", True),
        "is_running":    snapshot.get("is_running", False),
    }


@router.get("/history")
async def get_traffic_history(limit: int = 50, db: Session = Depends(get_db)):
    """
    Returns the last N traffic snapshots from the database.
    Used to draw historical charts on the dashboard.
    
    Query param: limit (default 50, max 500)
    """
    limit = min(limit, 500)
    snapshots = get_recent_snapshots(db, limit=limit)

    return {
        "count": len(snapshots),
        "snapshots": [
            {
                "step":        s.step,
                "timestamp":   s.timestamp.isoformat(),
                "queue":       {
                    "north": s.queue_north, "south": s.queue_south,
                    "east":  s.queue_east,  "west":  s.queue_west,
                },
                "wait": {
                    "north": s.wait_north, "south": s.wait_south,
                    "east":  s.wait_east,  "west":  s.wait_west,
                },
                "total_wait":  s.total_wait,
                "total_queue": s.total_queue,
                "phase":       s.current_phase,
            }
            for s in snapshots
        ]
    }


@router.get("/summary")
async def get_traffic_summary(db: Session = Depends(get_db)):
    """
    Returns aggregate statistics across all logged snapshots.
    Shown in the summary stats panel at top of dashboard.
    """
    snapshots = get_recent_snapshots(db, limit=500)

    if not snapshots:
        return {"message": "No data yet"}

    total_waits  = [s.total_wait  for s in snapshots]
    total_queues = [s.total_queue for s in snapshots]

    return {
        "total_snapshots": len(snapshots),
        "avg_wait":   round(sum(total_waits)  / len(total_waits),  1),
        "max_wait":   round(max(total_waits),  1),
        "avg_queue":  round(sum(total_queues) / len(total_queues), 1),
        "max_queue":  max(total_queues),
    }