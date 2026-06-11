# rl_engine/environment/action_space.py

"""
ACTION SPACE — What the AI can do

WHY WE KEEP IT SIMPLE (only 2 actions):
You might think: "Why not let the AI set exact green times like 25s or 42s?"
That would be a CONTINUOUS action space — much harder to learn.

Instead we use a DISCRETE action space:
Every N seconds, the AI makes ONE binary choice:
    Action 0 = Keep current phase (don't switch yet)
    Action 1 = Switch to next phase (change the light NOW)

This is simpler and works great because:
- AI learns WHEN to switch, not just what number to pick
- The effective green time = how many times it chose "keep" × step duration
- If step = 10 seconds and AI chose "keep" 3 times then "switch":
  effective green time = 30 seconds

PHASE SEQUENCE:
Our traffic light cycles through phases in order:
    Phase 0: NS Green   (North-South gets green)
    Phase 1: NS Yellow  (transition — always auto-skip, AI doesn't control this)
    Phase 2: EW Green   (East-West gets green)
    Phase 3: EW Yellow  (transition — always auto-skip)
    back to Phase 0...

The AI only decides during GREEN phases (0 and 2).
Yellow phases (1 and 3) are automatic 3-second transitions.
"""

import gymnasium as gym

# AI has exactly 2 choices
NUM_ACTIONS = 2
ACTION_KEEP   = 0  # Keep current green phase active
ACTION_SWITCH = 1  # Switch to next phase (triggers yellow then next green)

# Which phases are "green" phases (AI makes decisions here)
GREEN_PHASES = [0, 2]

# Which phases are "yellow" phases (automatic, AI skips these)
YELLOW_PHASES = [1, 3]

# How long yellow phases last (seconds) - matches our network.net.xml
YELLOW_DURATION = 3

# Phase transition map: when you "switch", what's the next GREEN phase?
# 0 (NS Green)  → switch → 1 (NS Yellow) → auto → 2 (EW Green)
# 2 (EW Green)  → switch → 3 (EW Yellow) → auto → 0 (NS Green)
NEXT_GREEN_PHASE = {
    0: 2,  # After NS Green comes EW Green
    2: 0,  # After EW Green comes NS Green
}


def build_action_space():
    """
    Creates the Gymnasium action space object.
    Discrete(2) means: the agent can output integer 0 or 1.
    """
    return gym.spaces.Discrete(NUM_ACTIONS)


def get_action_meaning(action):
    """
    Human-readable description of an action.
    Useful for logging and debugging.
    """
    meanings = {
        ACTION_KEEP:   "KEEP   — maintaining current phase",
        ACTION_SWITCH: "SWITCH — changing to next phase",
    }
    return meanings.get(action, "UNKNOWN")