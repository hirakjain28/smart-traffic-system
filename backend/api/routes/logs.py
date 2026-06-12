# backend/api/routes/logs.py

"""
LOG ROUTES — Decision history endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.db import get_db
from backend.database.crud import get_recent_decisions

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/decisions")
async def get_decision_log(limit: int = 20, db: Session = Depends(get_db)):
    """Returns the recent AI decision history."""
    decisions = get_recent_decisions(db, limit=limit)
    return {
        "decisions": [
            {
                "timestamp":    d.timestamp.isoformat(),
                "step":         d.step,
                "action":       d.action_label,
                "overridden":   d.was_overridden,
                "total_wait":   d.total_wait,
                "reward":       d.reward,
                "ai_mode":      d.ai_mode,
            }
            for d in decisions
        ]
    }


@router.get("/ai/suggestion")
async def get_ai_suggestion():
    """Returns what the AI currently recommends."""
    from backend.main import sim_service
    snapshot   = sim_service.state.get_snapshot()
    suggestion = snapshot.get("ai_suggestion")

    if not suggestion:
        return {"message": "No AI suggestion available"}

    return suggestion