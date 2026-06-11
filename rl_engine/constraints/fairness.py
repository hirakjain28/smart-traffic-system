# rl_engine/constraints/fairness.py

"""
FAIRNESS CONSTRAINTS — Rules the AI cannot break

WHAT IS A CONSTRAINT vs A REWARD?

Reward = "we prefer you don't do this" (soft)
Constraint = "you absolutely cannot do this" (hard)

Example:
    Reward tells AI: "long queues = bad score"
    Constraint tells AI: "you MUST give every direction at least 10 seconds"

Without constraints, an AI might find a "clever" shortcut:
    "If I give NS 58 seconds and EW only 2 seconds, NS waits less!"
    → This technically reduces total wait, but EW vehicles wait 2 minutes!
    → Real-world: emergency vehicles, pedestrians, buses — 2s is dangerous

OUR CONSTRAINTS:
    1. Minimum green time = 10 seconds
       (Prevents switching too rapidly — dangerous and inefficient)
       
    2. Maximum green time = 60 seconds
       (Prevents one direction hoarding all the time)
       
    3. Yellow phases = always exactly 3 seconds
       (Safety requirement — drivers need transition time)

HOW WE ENFORCE THEM:
    In the environment's step() function, BEFORE applying the AI's action,
    we check if it violates a constraint.
    If it does → we OVERRIDE the action (force it to be valid).
    
    This is called "action masking" or "action clipping."
"""

# ── CONSTRAINT PARAMETERS ─────────────────────────────────────────────────────
MIN_GREEN_TIME = 10   # Minimum seconds a green phase must be held
MAX_GREEN_TIME = 60   # Maximum seconds a green phase can be held


class FairnessConstraint:
    """
    Checks and enforces fairness constraints on the AI's actions.
    
    Used by the TrafficEnv to ensure the AI never makes unsafe decisions.
    """

    def __init__(self,
                 min_green=MIN_GREEN_TIME,
                 max_green=MAX_GREEN_TIME):
        self.min_green = min_green
        self.max_green = max_green

    def validate_action(self, action, time_in_phase, current_phase):
        """
        Checks if the AI's chosen action is valid.
        If not, overrides it with the correct forced action.
        
        Parameters:
            action         - the AI's chosen action (0=keep, 1=switch)
            time_in_phase  - how long current phase has been active (seconds)
            current_phase  - which phase is currently active (0, 1, 2, 3)
        
        Returns:
            final_action   - the action to actually apply (may differ from AI's)
            reason         - why the action was overridden (or None if not)
        
        LOGIC:
            Case 1: AI wants to SWITCH but phase is too new (< min_green)
                    → Force KEEP instead
                    → "You haven't held this long enough yet"
            
            Case 2: AI wants to KEEP but phase is too old (> max_green)
                    → Force SWITCH instead
                    → "You've held this too long, must switch now"
            
            Case 3: Action is valid
                    → Let the AI's choice stand
        """
        from rl_engine.environment.action_space import (
            ACTION_KEEP, ACTION_SWITCH, GREEN_PHASES
        )

        # Yellow phases are never controlled by AI — skip validation
        if current_phase not in GREEN_PHASES:
            return ACTION_KEEP, "yellow_phase_auto"

        # ── CONSTRAINT 1: Too early to switch ────────────────────────────────
        if action == ACTION_SWITCH and time_in_phase < self.min_green:
            return ACTION_KEEP, f"too_early (only {time_in_phase}s, min={self.min_green}s)"

        # ── CONSTRAINT 2: Held too long, must switch ─────────────────────────
        if action == ACTION_KEEP and time_in_phase >= self.max_green:
            return ACTION_SWITCH, f"forced_switch (held {time_in_phase}s, max={self.max_green}s)"

        # ── VALID: let AI's action proceed ────────────────────────────────────
        return action, None

    def get_info(self):
        """Returns constraint parameters as a dictionary (for logging)."""
        return {
            "min_green_time": self.min_green,
            "max_green_time": self.max_green,
        }