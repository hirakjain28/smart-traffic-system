# backend/api/routes/signals.py

"""
SIGNAL ROUTES — Traffic light state endpoints
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/signals", tags=["signals"])

PHASE_NAMES = {
    0: "NS Green", 1: "NS Yellow",
    2: "EW Green", 3: "EW Yellow"
}


@router.get("/state")
async def get_signal_state():
    """Returns current traffic light state."""
    from backend.main import sim_service
    snapshot = sim_service.state.get_snapshot()

    return {
        "intersection_id": "C",
        "current_phase":   snapshot.get("current_phase", 0),
        "phase_name":      snapshot.get("phase_name", "Unknown"),
        "time_in_phase":   snapshot.get("time_in_phase", 0),
        "ai_mode":         snapshot.get("ai_mode", True),
        "timestamp":       datetime.utcnow().isoformat(),
    }


@router.get("/phases")
async def get_all_phases():
    """Returns info about all possible phases."""
    return {
        "phases": [
            {"id": 0, "name": "NS Green",  "type": "green",  "directions": ["north", "south"]},
            {"id": 1, "name": "NS Yellow", "type": "yellow", "directions": ["north", "south"]},
            {"id": 2, "name": "EW Green",  "type": "green",  "directions": ["east",  "west"]},
            {"id": 3, "name": "EW Yellow", "type": "yellow", "directions": ["east",  "west"]},
        ]
    }