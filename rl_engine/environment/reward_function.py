# rl_engine/environment/reward_function.py

"""
REWARD FUNCTION — How we score the AI's decisions

THIS IS THE MOST IMPORTANT FILE IN RL.
The reward function literally defines what "good" means.
Get this wrong → AI learns the wrong behavior.

OUR REWARD DESIGN:

Base reward:
    reward = -(total waiting time across all roads)
    
    Why negative? We want to MINIMIZE waiting.
    Minimizing waiting = maximizing negative waiting = maximizing reward.
    
    Example:
    N=113s + S=145s + E=0s + W=0s → reward = -258  (bad, AI learns to avoid)
    N=5s   + S=8s   + E=3s + W=3s → reward = -19   (good, AI learns to repeat)

Fairness penalty:
    If ANY road's wait time exceeds FAIRNESS_THRESHOLD,
    apply an extra penalty. This prevents the AI from
    ignoring one direction completely.
    
    Without this, AI might learn:
    "NS has more cars, so give EW almost no time → NS happy, EW starving"
    With this, AI learns:
    "I need to balance ALL directions"

Efficiency bonus:
    Small bonus for keeping queue lengths LOW overall.
    Encourages the AI to be proactive, not just reactive.

WHY NOT JUST USE QUEUE LENGTH AS REWARD?
    Queue length = number of stopped cars
    Wait time = total seconds all cars have been waiting
    
    Wait time is BETTER because it captures urgency:
    - 3 cars waiting 50s each = 150s wait (very urgent!)
    - 10 cars waiting 5s each = 50s wait (less urgent)
    Queue length would say "10 cars is worse" but wait time
    correctly says "3 very patient cars is more urgent"
"""

# ── REWARD HYPERPARAMETERS ────────────────────────────────────────────────────
# These numbers are tunable — we may adjust them during training

# Weight for the base waiting time penalty
WAIT_PENALTY_WEIGHT = 0.001  

# If a road's total wait exceeds this threshold, apply extra penalty
# 100 seconds = roughly 3-4 cars waiting for 2 full cycles
FAIRNESS_THRESHOLD = 100.0

# Extra penalty applied when fairness threshold is breached
FAIRNESS_PENALTY = 5.0

# Small bonus per road that has zero queue
ZERO_QUEUE_BONUS = 0.5
# ─────────────────────────────────────────────────────────────────────────────


def calculate_reward(raw_state):
    """
    Calculates the reward for the current simulation state.
    
    Parameters:
        raw_state  - dictionary from observation_space.get_raw_state()
                     contains: queue{N,S,E,W}, wait{N,S,E,W}, vehicles{N,S,E,W}
    
    Returns:
        reward      - float (negative is bad, less negative is better)
        info_dict   - dictionary with reward breakdown (for debugging)
    
    EXAMPLE CALCULATION:
        raw_state = {
            "wait":  {"north": 113, "south": 145, "east": 0, "west": 0},
            "queue": {"north": 6,   "south": 8,   "east": 0, "west": 0}
        }
        
        total_wait = 113 + 145 + 0 + 0 = 258
        base_reward = -258 × 0.001 = -0.258
        
        fairness check: north=113 > 100 → penalty = -5.0
                        south=145 > 100 → penalty = -5.0
        
        zero queue bonus: east=0 → +0.5, west=0 → +0.5
        
        final reward = -0.258 - 5.0 - 5.0 + 0.5 + 0.5 = -9.258
    """

    wait  = raw_state["wait"]
    queue = raw_state["queue"]

    # ── BASE REWARD: penalize total waiting time ──────────────────────────────
    total_wait = sum(wait.values())  # sum of all 4 roads
    base_reward = -total_wait * WAIT_PENALTY_WEIGHT

    # ── FAIRNESS PENALTY: punish if any road is being starved ─────────────────
    fairness_penalty = 0.0
    for direction, wait_time in wait.items():
        if wait_time > FAIRNESS_THRESHOLD:
            fairness_penalty -= FAIRNESS_PENALTY
            # Extra severity: more penalty for extreme starvation
            if wait_time > FAIRNESS_THRESHOLD * 2:
                fairness_penalty -= FAIRNESS_PENALTY  # double penalty

    # ── EFFICIENCY BONUS: reward clear roads ─────────────────────────────────
    efficiency_bonus = 0.0
    for direction, q in queue.items():
        if q == 0:
            efficiency_bonus += ZERO_QUEUE_BONUS

    # ── TOTAL REWARD ─────────────────────────────────────────────────────────
    reward = base_reward + fairness_penalty + efficiency_bonus

    # ── INFO DICT: for logging and debugging ─────────────────────────────────
    info = {
        "total_wait":        total_wait,
        "base_reward":       base_reward,
        "fairness_penalty":  fairness_penalty,
        "efficiency_bonus":  efficiency_bonus,
        "final_reward":      reward,
    }

    return reward, info