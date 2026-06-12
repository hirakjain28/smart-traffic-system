# backend/services/override_service.py

"""
OVERRIDE SERVICE — Handles manual operator control

When an operator uses the dashboard to manually control signals,
this service processes that request and applies it to the simulation.

OVERRIDE MODES:
  1. Timed override: force phase X for N seconds, then AI resumes
  2. Mode switch: toggle entire system from AI → Manual or back
  3. Emergency: immediately force a specific phase (no timer)
"""

from datetime import datetime
from backend.config import DELTA_TIME


class OverrideService:
    """
    Handles manual override requests from operators.
    Works closely with SimulationService.
    """

    def __init__(self, simulation_service):
        self.sim = simulation_service

    def apply_phase_override(self, phase: int,
                             duration: int = None,
                             reason: str = None) -> dict:
        """
        Forces the traffic light to a specific phase.
        
        Parameters:
            phase     - target phase (0=NS Green, 2=EW Green)
            duration  - seconds to hold (None = until next AI step)
            reason    - operator's reason (for audit log)
        
        Returns:
            Response dict with success status
        """
        # Validate phase
        if phase not in [0, 1, 2, 3]:
            return {
                "success":   False,
                "message":   f"Invalid phase {phase}. Must be 0-3.",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Apply to simulation
        self.sim.apply_override(phase=phase, duration=duration)

        phase_names = {0: "NS Green", 1: "NS Yellow",
                       2: "EW Green", 3: "EW Yellow"}
        msg = (
            f"Override applied: {phase_names[phase]}"
            f"{f' for {duration}s' if duration else ''}"
            f"{f' — {reason}' if reason else ''}"
        )
        print(f"🔧 {msg}")

        return {
            "success":      True,
            "message":      msg,
            "phase_forced": phase,
            "timestamp":    datetime.utcnow().isoformat(),
        }

    def set_mode(self, ai_mode: bool) -> dict:
        """
        Switches between AI and Manual control modes.
        
        Parameters:
            ai_mode  - True = AI controls signals, False = Manual
        """
        self.sim.set_ai_mode(ai_mode)
        mode_name = "AI Automatic" if ai_mode else "Manual"

        return {
            "success":   True,
            "message":   f"Switched to {mode_name} mode",
            "ai_mode":   ai_mode,
            "timestamp": datetime.utcnow().isoformat(),
        }