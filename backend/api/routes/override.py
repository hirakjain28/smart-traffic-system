# backend/api/routes/override.py

"""
OVERRIDE ROUTES — Manual operator control endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.db import get_db
from backend.database.crud import save_override, get_recent_overrides
from backend.schemas.traffic_schema import OverrideRequest

router = APIRouter(prefix="/api/override", tags=["override"])


@router.post("/phase")
async def override_phase(request: OverrideRequest,
                         db: Session = Depends(get_db)):
    """
    Operator forces a specific traffic light phase.
    
    Body:
    {
        "phase": 0,
        "duration": 30,
        "reason": "Emergency vehicle on North road"
    }
    """
    from backend.main import override_service

    result = override_service.apply_phase_override(
        phase    = request.phase,
        duration = request.duration,
        reason   = request.reason,
    )

    if result["success"]:
        # Log to database
        save_override(
            db,
            forced_phase    = request.phase,
            forced_duration = request.duration,
            reason          = request.reason,
        )

    return result


@router.post("/mode")
async def set_control_mode(ai_mode: bool):
    """
    Toggle between AI and Manual control mode.
    
    Query param: ai_mode=true or ai_mode=false
    """
    from backend.main import override_service
    return override_service.set_mode(ai_mode)


@router.get("/history")
async def get_override_history(db: Session = Depends(get_db)):
    """Returns recent operator overrides."""
    overrides = get_recent_overrides(db, limit=20)
    return {
        "overrides": [
            {
                "timestamp":    o.timestamp.isoformat(),
                "phase_forced": o.forced_phase,
                "duration":     o.forced_duration,
                "reason":       o.reason,
            }
            for o in overrides
        ]
    }