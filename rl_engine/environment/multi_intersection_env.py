# rl_engine/environment/multi_intersection_env.py

"""
MULTI-INTERSECTION ENVIRONMENT

This is the Gym environment for all 4 intersections together.

ARCHITECTURE:
  4 independent agents share one environment.
  Each agent gets its own observation and produces its own action.
  Rewards are computed per-agent (local) + a coordination bonus (shared).

  This is called "Centralized Training, Decentralized Execution" (CTDE):
  - During training: all agents train together in the same simulation
  - During deployment: each agent runs independently on its own intersection

KEY DIFFERENCE FROM SINGLE-INTERSECTION ENV:
  Single: obs(10,)  →  action(1,)  →  reward(1,)
  Multi:  obs(4, 14,) → action(4,) → reward(4,)

OBSERVATION (14 features per agent):
  [0-9]   own 10-feature state (identical to single-intersection)
  [10-13] neighbor summary (4 features from neighbor_state.py)

REWARD:
  Each agent gets:
    local_reward   = -(own_total_wait × 0.001) + fairness + efficiency
    coord_bonus    = small bonus if through-traffic is flowing smoothly
                     (detected by checking if internal edges have vehicles
                     moving at > 50% of max speed)

  Final reward = local_reward + coord_weight × coord_bonus

EPISODE:
  Same as single: 360 steps × 10s = 1 hour of simulated traffic
  But now all 4 intersections run simultaneously in ONE SUMO instance.
"""

import os
import sys
import numpy as np
import gymnasium as gym
import traci

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

from rl_engine.environment.signal_program import install_clockwise_program
from rl_engine.environment.action_space import (
    ACTION_KEEP, ACTION_SWITCH, GREEN_PHASES,
    YELLOW_PHASES, YELLOW_DURATION, NEXT_GREEN_PHASE,
    get_action_meaning
)
from rl_engine.environment.observation_space import get_raw_state
from rl_engine.environment.reward_function import calculate_reward
from rl_engine.constraints.fairness import FairnessConstraint
from rl_engine.environment.neighbor_state import (
    get_all_neighbor_summaries, INTERSECTION_INCOMING
)

# ── CONFIG ─────────────────────────────────────────────────────────────────────
INTERSECTIONS = ["A", "B", "C", "D"]
DELTA_TIME    = 10
MAX_STEPS     = 360

NET_FILE   = os.path.join(
    os.path.dirname(__file__),
    "../../simulation/nets/grid_2x2/network.net.xml"
)
ROUTE_FILE = os.path.join(
    os.path.dirname(__file__),
    "../../simulation/nets/grid_2x2/routes.rou.xml"
)

# Internal edges between intersections — used for coordination bonus
INTERNAL_EDGES = ["A2B", "B2A", "C2D", "D2C", "A2C", "C2A", "B2D", "D2B"]
COORD_BONUS_WEIGHT = 0.3
MAX_SPEED = 13.89

# Incoming edges per intersection (for own observation)
OWN_INCOMING = {
    "A": {"north": "N12A", "east": "A2B",  "south": "A2C", "west": "W12A"},
    "B": {"north": "N22B", "east": "E12B", "south": "B2D", "west": "A2B"},
    "C": {"north": "A2C",  "east": "C2D",  "south": "S12C","west": "W22C"},
    "D": {"north": "B2D",  "east": "E22D", "south": "S22D","west": "C2D"},
}

# Normalization constants (same as single-intersection)
MAX_QUEUE    = 30
MAX_WAIT     = 300.0
MAX_PHASE    = 7
MAX_PHASE_TIME = 120.0
# ─────────────────────────────────────────────────────────────────────────────


def _get_own_state(tl_id: str, current_phase: int, time_in_phase: float) -> np.ndarray:
    """Builds the 10-feature own state for one intersection."""
    edges = OWN_INCOMING[tl_id]
    state = np.array([
        np.clip(traci.edge.getLastStepHaltingNumber(edges["north"]), 0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(traci.edge.getLastStepHaltingNumber(edges["south"]), 0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(traci.edge.getLastStepHaltingNumber(edges["east"]),  0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(traci.edge.getLastStepHaltingNumber(edges["west"]),  0, MAX_QUEUE)     / MAX_QUEUE,
        np.clip(traci.edge.getWaitingTime(edges["north"]), 0, MAX_WAIT) / MAX_WAIT,
        np.clip(traci.edge.getWaitingTime(edges["south"]), 0, MAX_WAIT) / MAX_WAIT,
        np.clip(traci.edge.getWaitingTime(edges["east"]),  0, MAX_WAIT) / MAX_WAIT,
        np.clip(traci.edge.getWaitingTime(edges["west"]),  0, MAX_WAIT) / MAX_WAIT,
        current_phase                                                   / MAX_PHASE,
        np.clip(time_in_phase, 0, MAX_PHASE_TIME)                       / MAX_PHASE_TIME,
    ], dtype=np.float32)
    return state


def _get_raw_state_for(tl_id: str) -> dict:
    """Builds the raw (unnormalized) state dict for reward calculation."""
    edges = OWN_INCOMING[tl_id]
    return {
        "queue": {
            "north": traci.edge.getLastStepHaltingNumber(edges["north"]),
            "south": traci.edge.getLastStepHaltingNumber(edges["south"]),
            "east":  traci.edge.getLastStepHaltingNumber(edges["east"]),
            "west":  traci.edge.getLastStepHaltingNumber(edges["west"]),
        },
        "wait": {
            "north": traci.edge.getWaitingTime(edges["north"]),
            "south": traci.edge.getWaitingTime(edges["south"]),
            "east":  traci.edge.getWaitingTime(edges["east"]),
            "west":  traci.edge.getWaitingTime(edges["west"]),
        },
        "vehicles": {
            "north": traci.edge.getLastStepVehicleNumber(edges["north"]),
            "south": traci.edge.getLastStepVehicleNumber(edges["south"]),
            "east":  traci.edge.getLastStepVehicleNumber(edges["east"]),
            "west":  traci.edge.getLastStepVehicleNumber(edges["west"]),
        }
    }


def _coordination_bonus() -> float:
    """
    Computes a small shared bonus when through-traffic flows freely.

    Logic: Check the average speed on internal edges (between intersections).
    If vehicles are moving at > 50% of max speed → coordination is working.
    If vehicles are stopped on internal edges → signals are out of sync.

    This bonus is shared across all agents — it rewards the TEAM,
    not just individual intersections.
    """
    speeds = []
    for edge in INTERNAL_EDGES:
        try:
            mean_speed = traci.edge.getLastStepMeanSpeed(edge)
            speeds.append(mean_speed)
        except Exception:
            speeds.append(0.0)

    if not speeds:
        return 0.0

    avg_speed     = sum(speeds) / len(speeds)
    speed_ratio   = avg_speed / MAX_SPEED  # 0 = stopped, 1 = full speed
    bonus         = max(0, speed_ratio - 0.5) * 2  # only positive above 50% speed
    return bonus


class MultiIntersectionEnv:
    """
    Multi-agent traffic environment for a 2x2 grid.

    NOT a standard gym.Env — instead it has a step() that accepts
    a dict of actions (one per intersection) and returns dicts of
    observations, rewards, and info.

    This pattern is called a "MARL environment" — it's the standard
    way to handle multi-agent RL when agents share a simulator.

    Usage:
        env = MultiIntersectionEnv()
        obs = env.reset()               # dict: {A: array(14,), B: ..., ...}
        actions = {A: 0, B: 1, C: 0, D: 1}
        obs, rewards, done, info = env.step(actions)
    """

    def __init__(self, use_gui=False, delta_time=DELTA_TIME, max_steps=MAX_STEPS):
        self.use_gui    = use_gui
        self.delta_time = delta_time
        self.max_steps  = max_steps

        # Per-intersection state trackers
        self.phases         = {i: 0   for i in INTERSECTIONS}
        self.time_in_phase  = {i: 0   for i in INTERSECTIONS}
        self.step_count     = 0
        self.sumo_running   = False

        self.constraints = {i: FairnessConstraint() for i in INTERSECTIONS}

        # Gymnasium spaces (used by the DQN agent manager)
        self.observation_space = gym.spaces.Box(
            low=np.zeros(14,  dtype=np.float32),
            high=np.ones(14,  dtype=np.float32),
            dtype=np.float32
        )
        self.action_space = gym.spaces.Discrete(2)

    def reset(self):
        if self.sumo_running:
            traci.close()

        sumo_binary = "sumo-gui" if self.use_gui else "sumo"
        sumo_cmd = [
            sumo_binary,
            "--net-file",    NET_FILE,
            "--route-files", ROUTE_FILE,
            "--no-step-log", "true",
            "--waiting-time-memory", "1000",
            "--time-to-teleport", "-1",
        ]
        traci.start(sumo_cmd)
        self.sumo_running = True

        # Install India-style clockwise program on ALL 4 intersections
        for tl_id in INTERSECTIONS:
            install_clockwise_program(tl_id)

        # Reset trackers
        self.phases        = {i: 0 for i in INTERSECTIONS}
        self.time_in_phase = {i: 0 for i in INTERSECTIONS}
        self.step_count    = 0

        # Warm up
        for _ in range(5):
            traci.simulationStep()

        return self._get_all_observations()

    def step(self, actions: dict):
        """
        Takes one action per intersection and advances the simulation.

        Parameters:
            actions  - dict {tl_id: 0_or_1} for each intersection

        Returns:
            observations  - dict of new 14-feature state per intersection
            rewards       - dict of float reward per intersection
            done          - True if episode ended
            info          - dict of debug info per intersection
        """
        # ── VALIDATE + APPLY ACTIONS ────────────────────────────────────────
        for tl_id in INTERSECTIONS:
            action = actions.get(tl_id, ACTION_KEEP)

            validated, _ = self.constraints[tl_id].validate_action(
                action, self.time_in_phase[tl_id], self.phases[tl_id]
            )

            if validated == ACTION_SWITCH and self.phases[tl_id] in GREEN_PHASES:
                yellow_phase = self.phases[tl_id] + 1
                traci.trafficlight.setPhase(tl_id, yellow_phase)
                self.phases[tl_id]        = yellow_phase
                self.time_in_phase[tl_id] = 0

        # ── ADVANCE SUMO ─────────────────────────────────────────────────────
        for _ in range(self.delta_time):
            traci.simulationStep()

            # Handle yellow → green transitions for all intersections
            for tl_id in INTERSECTIONS:
                self.time_in_phase[tl_id] += 1
                if (self.phases[tl_id] in YELLOW_PHASES and
                        self.time_in_phase[tl_id] >= YELLOW_DURATION):
                    green_before = self.phases[tl_id] - 1
                    next_green   = NEXT_GREEN_PHASE[green_before]
                    traci.trafficlight.setPhase(tl_id, next_green)
                    self.phases[tl_id]        = next_green
                    self.time_in_phase[tl_id] = 0

        # ── COMPUTE REWARDS ──────────────────────────────────────────────────
        coord_bonus = _coordination_bonus()
        rewards     = {}
        raw_states  = {}

        for tl_id in INTERSECTIONS:
            raw   = _get_raw_state_for(tl_id)
            r, _  = calculate_reward(raw)
            rewards[tl_id]    = r + COORD_BONUS_WEIGHT * coord_bonus
            raw_states[tl_id] = raw

        # ── GET NEW OBSERVATIONS ──────────────────────────────────────────────
        observations = self._get_all_observations()

        # ── DONE? ─────────────────────────────────────────────────────────────
        self.step_count += 1
        done = self.step_count >= self.max_steps

        info = {
            tl_id: {
                "phase":        self.phases[tl_id],
                "time_in_phase":self.time_in_phase[tl_id],
                "coord_bonus":  coord_bonus,
                "raw_state":    raw_states[tl_id],
            }
            for tl_id in INTERSECTIONS
        }

        return observations, rewards, done, info

    def _get_all_observations(self) -> dict:
        """Builds the 14-feature observation for every intersection."""
        neighbor_summaries = get_all_neighbor_summaries(traci)
        observations = {}
        for tl_id in INTERSECTIONS:
            own_state    = _get_own_state(tl_id, self.phases[tl_id], self.time_in_phase[tl_id])
            neighbor_obs = neighbor_summaries[tl_id]
            observations[tl_id] = np.concatenate([own_state, neighbor_obs])
        return observations

    def close(self):
        if self.sumo_running:
            traci.close()
            self.sumo_running = False

class SingleAgentWrapper(gym.Env):
    """
    Wraps MultiIntersectionEnv so one specific intersection looks like
    a standard gym.Env to SB3's DQN.

    WHY THIS PATTERN?
    SB3 was designed for single-agent RL. It expects:
      - env.observation_space
      - env.action_space
      - env.reset() → single observation
      - env.step(action) → (obs, reward, terminated, truncated, info)

    MultiIntersectionEnv handles ALL 4 intersections together.
    This wrapper makes intersection tl_id look like its own env,
    while the OTHER 3 intersections take random actions — that's fine
    for training because each agent independently learns its own policy.
    """

    def __init__(self, multi_env: MultiIntersectionEnv, tl_id: str):
        super().__init__()
        self.multi_env = multi_env
        self.tl_id     = tl_id

        self.observation_space = gym.spaces.Box(
            low=np.zeros(14,  dtype=np.float32),
            high=np.ones(14,  dtype=np.float32),
            dtype=np.float32
        )
        self.action_space = gym.spaces.Discrete(2)
        self._current_obs = None   # cache of last observations dict

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        obs_dict = self.multi_env.reset()
        self._current_obs = obs_dict
        return obs_dict[self.tl_id], {}

    def step(self, action):
        # Build full action dict: this agent's real action + random for others
        actions = {}
        for tid in INTERSECTIONS:
            if tid == self.tl_id:
                actions[tid] = int(action)
            else:
                actions[tid] = self.multi_env.action_space.sample()

        obs_dict, rewards, done, info = self.multi_env.step(actions)
        self._current_obs = obs_dict

        obs      = obs_dict[self.tl_id]
        reward   = rewards[self.tl_id]
        terminated = done
        truncated  = False

        return obs, reward, terminated, truncated, info.get(self.tl_id, {})

    def close(self):
        # Don't close the shared multi_env here — let MultiAgentManager do it
        pass