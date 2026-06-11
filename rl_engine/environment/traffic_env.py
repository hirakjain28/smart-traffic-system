# rl_engine/environment/traffic_env.py

"""
TRAFFIC ENVIRONMENT — The main RL Gym environment

This file is the heart of Phase 2. It implements the standard
OpenAI Gymnasium interface which every RL algorithm expects:

    env.reset()          → Start a new episode, get initial state
    env.step(action)     → Take action, get (next_state, reward, done, info)
    env.close()          → Shut down SUMO cleanly

WHAT IS AN EPISODE?
An episode = one complete run of the simulation (e.g., 1 hour of traffic).
The AI runs many episodes during training.
Each episode: SUMO starts fresh → AI makes decisions → SUMO ends → repeat.

WHAT HAPPENS IN step():
    1. Validate action against fairness constraints
    2. Apply action to SUMO (change traffic light if switching)
    3. Advance SUMO by DELTA_TIME seconds
    4. Read new traffic state from SUMO
    5. Calculate reward
    6. Check if episode is done
    7. Return everything to the AI

THE STEP INTERVAL (DELTA_TIME):
    We don't make a decision every second — that's too fast.
    We make a decision every DELTA_TIME=10 seconds.
    
    Why 10 seconds?
    - Realistic: real controllers don't change every second
    - Enough time to see effect of previous decision
    - Fast enough to be responsive to traffic
"""

import os
import sys
import numpy as np
import gymnasium as gym
import traci

# ── SETUP SUMO PATH ───────────────────────────────────────────────────────────
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please set the SUMO_HOME environment variable.")
# ─────────────────────────────────────────────────────────────────────────────

from rl_engine.environment.observation_space import (
    build_observation_space, get_state, get_raw_state
)
from rl_engine.environment.action_space import (
    build_action_space, get_action_meaning,
    ACTION_KEEP, ACTION_SWITCH,
    GREEN_PHASES, YELLOW_PHASES, YELLOW_DURATION,
    NEXT_GREEN_PHASE
)
from rl_engine.environment.reward_function import calculate_reward
from rl_engine.constraints.fairness import FairnessConstraint


# ── ENVIRONMENT SETTINGS ──────────────────────────────────────────────────────
TRAFFIC_LIGHT_ID = "C"          # ID of our intersection in SUMO
DELTA_TIME       = 10           # Seconds between AI decisions
MAX_STEPS        = 360          # Steps per episode (360 × 10s = 3600s = 1 hour)

# Path to SUMO config files
NET_FILE   = os.path.join(
    os.path.dirname(__file__), "../../simulation/nets/single_intersection/network.net.xml"
)
ROUTE_FILE = os.path.join(
    os.path.dirname(__file__), "../../simulation/nets/single_intersection/routes.rou.xml"
)
# ─────────────────────────────────────────────────────────────────────────────


class TrafficEnv(gym.Env):
    """
    Custom Gymnasium environment for traffic signal control.
    
    Inherits from gym.Env which requires us to implement:
        - reset()
        - step()
        - close()
    And define:
        - observation_space
        - action_space
    
    Parameters:
        use_gui      - True = show SUMO window (visual), False = headless (faster)
        delta_time   - seconds between AI decisions
        max_steps    - how many steps per episode
    """

    def __init__(self,
                 use_gui=False,
                 delta_time=DELTA_TIME,
                 max_steps=MAX_STEPS):

        super().__init__()

        self.use_gui      = use_gui
        self.delta_time   = delta_time
        self.max_steps    = max_steps

        # ── GYM REQUIRED ATTRIBUTES ───────────────────────────────────────────
        self.observation_space = build_observation_space()
        self.action_space      = build_action_space()

        # ── INTERNAL STATE TRACKING ───────────────────────────────────────────
        self.current_phase  = 0    # which traffic light phase is active
        self.time_in_phase  = 0    # how long current phase has been active
        self.step_count     = 0    # how many steps in this episode
        self.episode_reward = 0.0  # cumulative reward this episode
        self.sumo_running   = False

        # ── FAIRNESS CONSTRAINT ───────────────────────────────────────────────
        self.constraint = FairnessConstraint()

        # ── EPISODE HISTORY (for logging/dashboard later) ─────────────────────
        self.history = []

    # ═══════════════════════════════════════════════════════════════════════════
    # reset() — Start a new episode
    # ═══════════════════════════════════════════════════════════════════════════
    def reset(self, seed=None, options=None):
        """
        Called at the beginning of each training episode.
        Restarts SUMO with a fresh simulation.
        
        Returns:
            observation  - the initial state (numpy array)
            info         - empty dict (Gymnasium requirement)
        """
        super().reset(seed=seed)

        # Close previous SUMO instance if running
        if self.sumo_running:
            traci.close()
            self.sumo_running = False

        # ── START SUMO ────────────────────────────────────────────────────────
        sumo_binary = "sumo-gui" if self.use_gui else "sumo"
        sumo_cmd = [
            sumo_binary,
            "--net-file",    NET_FILE,
            "--route-files", ROUTE_FILE,
            "--no-step-log", "true",    # suppress step-by-step output
            "--waiting-time-memory", "1000",  # remember wait times longer
            "--time-to-teleport", "-1",  # disable teleporting stuck cars
        ]
        traci.start(sumo_cmd)
        self.sumo_running = True

        # ── RESET INTERNAL STATE ──────────────────────────────────────────────
        self.current_phase  = 0
        self.time_in_phase  = 0
        self.step_count     = 0
        self.episode_reward = 0.0
        self.history        = []

        # Set traffic light to phase 0 (NS Green) at start
        traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, 0)

        # Advance simulation a few steps to let vehicles enter
        for _ in range(5):
            traci.simulationStep()

        # ── GET INITIAL STATE ─────────────────────────────────────────────────
        initial_state = get_state(traci, self.current_phase, self.time_in_phase)

        return initial_state, {}

    # ═══════════════════════════════════════════════════════════════════════════
    # step() — Take one action and advance the simulation
    # ═══════════════════════════════════════════════════════════════════════════
    def step(self, action):
        """
        The main function — called every DELTA_TIME seconds.
        
        Parameters:
            action  - 0 (keep) or 1 (switch), chosen by the AI
        
        Returns:
            observation  - new state after taking action
            reward       - how good or bad this step was
            terminated   - True if episode ended naturally (max steps)
            truncated    - True if episode ended early (we don't use this)
            info         - dictionary with extra details for logging
        
        WHAT HAPPENS EACH STEP:
        
        ┌─────────────────────────────────────────────────────────┐
        │ 1. Constraint check: is AI's action valid?              │
        │ 2. Apply action to traffic light                         │
        │ 3. Run SUMO for DELTA_TIME seconds                      │
        │ 4. Read new traffic data                                │
        │ 5. Calculate reward                                     │
        │ 6. Check if episode is done                             │
        │ 7. Return (state, reward, done, info)                   │
        └─────────────────────────────────────────────────────────┘
        """

        # ── STEP 1: VALIDATE ACTION (fairness constraint) ─────────────────────
        validated_action, override_reason = self.constraint.validate_action(
            action, self.time_in_phase, self.current_phase
        )

        # ── STEP 2: APPLY ACTION TO TRAFFIC LIGHT ─────────────────────────────
        if validated_action == ACTION_SWITCH:
            self._switch_phase()
        # if ACTION_KEEP, we do nothing — light stays as is

        # ── STEP 3: ADVANCE SUMO BY DELTA_TIME SECONDS ───────────────────────
        # We run SUMO for delta_time steps (1 step = 1 second)
        for _ in range(self.delta_time):
            traci.simulationStep()
            self.time_in_phase += 1  # count up time in current phase

            # Handle automatic yellow phase transition
            # If we're in a yellow phase and time is up → switch to next green
            if self.current_phase in YELLOW_PHASES:
                if self.time_in_phase >= YELLOW_DURATION:
                    next_green = NEXT_GREEN_PHASE.get(
                        self.current_phase - 1,  # yellow 1 → came from green 0
                        0
                    )
                    # Yellow phase 1 → next green is 2
                    # Yellow phase 3 → next green is 0
                    next_green = 2 if self.current_phase == 1 else 0
                    traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, next_green)
                    self.current_phase = next_green
                    self.time_in_phase = 0

        # ── STEP 4: READ NEW STATE ────────────────────────────────────────────
        raw_state = get_raw_state(traci)
        new_state  = get_state(traci, self.current_phase, self.time_in_phase)

        # ── STEP 5: CALCULATE REWARD ──────────────────────────────────────────
        reward, reward_info = calculate_reward(raw_state)
        self.episode_reward += reward

        # ── STEP 6: CHECK IF EPISODE IS DONE ─────────────────────────────────
        self.step_count += 1
        terminated = (self.step_count >= self.max_steps)
        truncated  = False

        # ── STEP 7: BUILD INFO DICT ───────────────────────────────────────────
        info = {
            "step":            self.step_count,
            "action_taken":    get_action_meaning(validated_action),
            "action_overridden": override_reason is not None,
            "override_reason": override_reason,
            "current_phase":   self.current_phase,
            "time_in_phase":   self.time_in_phase,
            "episode_reward":  self.episode_reward,
            "traffic":         raw_state,
            **reward_info,
        }

        # Save to history for logging
        self.history.append({
            "step": self.step_count,
            "reward": reward,
            "total_wait": reward_info["total_wait"],
            "phase": self.current_phase,
        })

        return new_state, reward, terminated, truncated, info

    # ═══════════════════════════════════════════════════════════════════════════
    # Helper: _switch_phase()
    # ═══════════════════════════════════════════════════════════════════════════
    def _switch_phase(self):
        """
        Transitions traffic light from current GREEN phase to YELLOW,
        then environment automatically transitions to next GREEN in step loop.
        
        GREEN → YELLOW → (auto) → next GREEN
        
        Example:
        Phase 0 (NS Green) → switch → Phase 1 (NS Yellow) → Phase 2 (EW Green)
        Phase 2 (EW Green) → switch → Phase 3 (EW Yellow) → Phase 0 (NS Green)
        """
        if self.current_phase in GREEN_PHASES:
            yellow_phase = self.current_phase + 1  # green 0 → yellow 1, green 2 → yellow 3
            traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, yellow_phase)
            self.current_phase = yellow_phase
            self.time_in_phase = 0

    # ═══════════════════════════════════════════════════════════════════════════
    # close() — Shut down SUMO
    # ═══════════════════════════════════════════════════════════════════════════
    def close(self):
        """
        Cleanly shuts down SUMO.
        Always call this when done — otherwise SUMO processes hang in memory.
        """
        if self.sumo_running:
            traci.close()
            self.sumo_running = False