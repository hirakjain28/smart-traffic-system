# rl_engine/environment/observation_space.py

"""
OBSERVATION SPACE — What the AI sees every step

WHY THIS MATTERS:
The AI can only make good decisions if it sees the RIGHT information.
Too little info → AI makes blind decisions
Too much info  → AI takes longer to learn (harder to find patterns)

We need to give it exactly what it needs to answer:
"Should I switch the traffic light right now?"

OUR STATE VECTOR has 10 numbers:
┌─────────────────────────────────────────────────────────┐
│ Index │ What it is             │ Range      │ Why?       │
├─────────────────────────────────────────────────────────┤
│   0   │ Queue length - North   │ 0 to 30    │ How backed │
│   1   │ Queue length - South   │ 0 to 30    │ up each    │
│   2   │ Queue length - East    │ 0 to 30    │ direction  │
│   3   │ Queue length - West    │ 0 to 30    │ is         │
├─────────────────────────────────────────────────────────┤
│   4   │ Wait time - North      │ 0 to 300s  │ How urgent │
│   5   │ Wait time - South      │ 0 to 300s  │ each       │
│   6   │ Wait time - East       │ 0 to 300s  │ direction  │
│   7   │ Wait time - West       │ 0 to 300s  │ is         │
├─────────────────────────────────────────────────────────┤
│   8   │ Current phase (0-3)    │ 0 to 3     │ Which      │
│       │ 0=NS green, 2=EW green │            │ light is   │
│       │ 1=NS yellow,3=EW yellow│            │ active now │
├─────────────────────────────────────────────────────────┤
│   9   │ Time in current phase  │ 0 to 120s  │ How long   │
│       │                        │            │ since last │
│       │                        │            │ switch     │
└─────────────────────────────────────────────────────────┘

NORMALIZATION:
We divide all values by their max so everything is between 0 and 1.
Why? Neural networks learn better with small consistent numbers.
0.8 is better than 24 (queue of 24 out of max 30).
"""

import numpy as np
import gymnasium as gym


# The edges (road segments) going INTO the intersection
# These are the roads we monitor for queues
INCOMING_EDGES = {
    "north": "N2C",
    "south": "S2C",
    "east":  "E2C",
    "west":  "W2C"
}

# Maximum values for normalization
# These are realistic upper bounds for our simulation
MAX_QUEUE    = 30     # max cars we expect in queue per road
MAX_WAIT     = 300.0  # max total waiting time (seconds) per road
MAX_PHASE    = 3      # phases are 0,1,2,3
MAX_PHASE_TIME = 120.0  # max seconds we'd ever hold one phase


def build_observation_space():
    """
    Creates the Gymnasium observation space object.
    
    This tells the RL algorithm:
    "The AI will receive a numpy array of 10 floats,
     each between 0.0 and 1.0"
    
    gymnasium.spaces.Box = a continuous n-dimensional space
    low  = minimum value for each element
    high = maximum value for each element
    dtype = data type (float32 is standard for RL)
    """
    return gym.spaces.Box(
        low=np.zeros(10, dtype=np.float32),   # all minimums are 0
        high=np.ones(10, dtype=np.float32),   # all maximums are 1 (normalized)
        dtype=np.float32
    )


def get_state(traci, current_phase, time_in_phase):
    """
    Reads live data from SUMO via TraCI and returns a normalized state vector.
    
    Parameters:
        traci          - the active TraCI connection to SUMO
        current_phase  - which phase is currently active (0, 1, 2, or 3)
        time_in_phase  - how many seconds the current phase has been active
    
    Returns:
        numpy array of 10 floats, each between 0.0 and 1.0
    
    HOW NORMALIZATION WORKS:
        Raw queue = 15 cars
        MAX_QUEUE  = 30
        Normalized = 15/30 = 0.5
        
        Raw wait = 150 seconds
        MAX_WAIT  = 300
        Normalized = 150/300 = 0.5
    """
    
    # ── READ QUEUE LENGTHS ────────────────────────────────────────────────────
    # getLastStepHaltingNumber = vehicles nearly stopped (speed < 0.1 m/s)
    # This is our "queue length" — how many cars are waiting at the red light
    queue_n = traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["north"])
    queue_s = traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["south"])
    queue_e = traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["east"])
    queue_w = traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["west"])

    # ── READ WAITING TIMES ────────────────────────────────────────────────────
    # getWaitingTime = sum of waiting time of ALL vehicles on the edge
    # If 3 cars have each waited 10s → waiting time = 30s
    # Higher = more urgent to give this road green light
    wait_n = traci.edge.getWaitingTime(INCOMING_EDGES["north"])
    wait_s = traci.edge.getWaitingTime(INCOMING_EDGES["south"])
    wait_e = traci.edge.getWaitingTime(INCOMING_EDGES["east"])
    wait_w = traci.edge.getWaitingTime(INCOMING_EDGES["west"])

    # ── BUILD AND NORMALIZE STATE VECTOR ─────────────────────────────────────
    # np.clip ensures value never exceeds max (in case of traffic jam)
    # then we divide by max to normalize to [0, 1]
    state = np.array([
        np.clip(queue_n, 0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(queue_s, 0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(queue_e, 0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(queue_w, 0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(wait_n,  0, MAX_WAIT)      / MAX_WAIT,
        np.clip(wait_s,  0, MAX_WAIT)      / MAX_WAIT,
        np.clip(wait_e,  0, MAX_WAIT)      / MAX_WAIT,
        np.clip(wait_w,  0, MAX_WAIT)      / MAX_WAIT,
        current_phase                      / MAX_PHASE,
        np.clip(time_in_phase, 0, MAX_PHASE_TIME) / MAX_PHASE_TIME,
    ], dtype=np.float32)

    return state


def get_raw_state(traci):
    """
    Returns raw (non-normalized) traffic data as a dictionary.
    Used for logging, dashboard display, and reward calculation.
    We need the REAL numbers for reward — not normalized ones.
    """
    return {
        "queue": {
            "north": traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["north"]),
            "south": traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["south"]),
            "east":  traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["east"]),
            "west":  traci.edge.getLastStepHaltingNumber(INCOMING_EDGES["west"]),
        },
        "wait": {
            "north": traci.edge.getWaitingTime(INCOMING_EDGES["north"]),
            "south": traci.edge.getWaitingTime(INCOMING_EDGES["south"]),
            "east":  traci.edge.getWaitingTime(INCOMING_EDGES["east"]),
            "west":  traci.edge.getWaitingTime(INCOMING_EDGES["west"]),
        },
        "vehicles": {
            "north": traci.edge.getLastStepVehicleNumber(INCOMING_EDGES["north"]),
            "south": traci.edge.getLastStepVehicleNumber(INCOMING_EDGES["south"]),
            "east":  traci.edge.getLastStepVehicleNumber(INCOMING_EDGES["east"]),
            "west":  traci.edge.getLastStepVehicleNumber(INCOMING_EDGES["west"]),
        }
    }