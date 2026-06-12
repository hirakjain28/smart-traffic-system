# backend/services/simulation_service.py

"""
SIMULATION SERVICE — Manages the SUMO simulation

This is the most complex service. It runs the simulation
in a continuous loop and makes data available to the API.

THREADING MODEL:
  The simulation runs in a BACKGROUND THREAD.
  The FastAPI server runs in the MAIN THREAD.
  They share data through a SimulationState object.
  
  Why threading?
  SUMO blocks while running (it needs to keep stepping).
  FastAPI needs to serve HTTP requests at the same time.
  Threading lets both run concurrently.
  
  Thread safety:
  We use threading.Lock() to prevent race conditions.
  "Only one thread can read/write state at a time."

SIMULATION LOOP:
  Every DELTA_TIME seconds:
    1. Read traffic state from SUMO
    2. Pass state to RL service → get action
    3. Apply action to traffic light
    4. Update shared state object
    5. Notify all WebSocket clients
"""

import os
import sys
import time
import threading
import traci
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from backend.config import (
    NET_FILE, ROUTE_FILE, TRAFFIC_LIGHT_ID,
    DELTA_TIME, USE_GUI, SUMO_HOME
)

# Setup SUMO path
if SUMO_HOME not in sys.path:
    tools = os.path.join(SUMO_HOME, 'tools')
    sys.path.append(tools)

from rl_engine.environment.observation_space import get_state, get_raw_state
from rl_engine.environment.action_space import (
    ACTION_KEEP, ACTION_SWITCH, GREEN_PHASES,
    YELLOW_PHASES, YELLOW_DURATION, get_action_meaning
)
from rl_engine.constraints.fairness import FairnessConstraint
from rl_engine.environment.reward_function import calculate_reward


# ── PHASE NAME MAP ─────────────────────────────────────────────────────────────
PHASE_NAMES = {
    0: "NS Green",
    1: "NS Yellow",
    2: "EW Green",
    3: "EW Yellow",
}


class SimulationState:
    """
    Shared state object between simulation thread and API thread.
    
    The simulation thread WRITES to this.
    The API routes READ from this.
    
    threading.Lock() ensures they don't conflict.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Traffic data
        self.traffic       = {}
        self.current_phase = 0
        self.time_in_phase = 0
        self.step          = 0
        self.timestamp     = datetime.utcnow().isoformat()

        # AI data
        self.last_action       = None
        self.last_reward       = 0.0
        self.ai_suggestion     = None
        self.ai_mode           = True    # True=AI in control, False=Manual

        # Override data
        self.override_phase    = None    # if set, force this phase
        self.override_until    = None    # step until which override lasts

        # Running state
        self.is_running        = False
        self.episode_count     = 0

        # WebSocket broadcast callback
        # Set by the WebSocket manager
        self.broadcast_callback = None

    def update(self, **kwargs):
        """Thread-safe update of state fields."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self.timestamp = datetime.utcnow().isoformat()

    def get_snapshot(self):
        """Thread-safe read of all state fields."""
        with self._lock:
            return {
                "traffic":       self.traffic,
                "current_phase": self.current_phase,
                "phase_name":    PHASE_NAMES.get(self.current_phase, "Unknown"),
                "time_in_phase": self.time_in_phase,
                "step":          self.step,
                "timestamp":     self.timestamp,
                "last_action":   self.last_action,
                "last_reward":   self.last_reward,
                "ai_suggestion": self.ai_suggestion,
                "ai_mode":       self.ai_mode,
                "is_running":    self.is_running,
            }


class SimulationService:
    """
    Manages the SUMO simulation lifecycle and the main control loop.
    
    Usage:
        service = SimulationService(rl_service)
        service.start()        # starts background thread
        service.stop()         # stops gracefully
        service.state          # access current state
    """

    def __init__(self, rl_service):
        self.rl_service  = rl_service
        self.state       = SimulationState()
        self.constraint  = FairnessConstraint()
        self._thread     = None
        self._stop_event = threading.Event()

    def start(self):
        """Starts the simulation in a background thread."""
        if self._thread and self._thread.is_alive():
            print("⚠️  Simulation already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,   # dies when main thread dies
            name="SimulationThread"
        )
        self._thread.start()
        print("🚀 Simulation thread started")

    def stop(self):
        """Signals the simulation to stop gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        print("🛑 Simulation stopped")

    def set_ai_mode(self, ai_mode: bool):
        """Toggle between AI mode and Manual mode."""
        self.state.update(ai_mode=ai_mode)
        mode_name = "AI" if ai_mode else "Manual"
        print(f"🔄 Switched to {mode_name} mode")

    def apply_override(self, phase: int, duration: int = None):
        """
        Operator manually forces a specific phase.
        
        Parameters:
            phase     - which phase to force (0-3)
            duration  - how many steps to hold it (None = 1 step)
        """
        steps = duration // DELTA_TIME if duration else 1
        with self.state._lock:
            self.state.override_phase = phase
            self.state.override_until = self.state.step + steps
        print(f"🔧 Override applied: Phase {phase} for {steps} steps")

    # ═══════════════════════════════════════════════════════════════════════════
    # THE MAIN SIMULATION LOOP
    # ═══════════════════════════════════════════════════════════════════════════
    def _run_loop(self):
        """
        The heart of the backend. Runs continuously in background thread.
        
        Loop structure:
            while not stopped:
                1. Start new SUMO episode
                2. Run episode step by step
                3. At each step:
                   a. Get AI action (or check for override)
                   b. Apply to traffic light
                   c. Advance SUMO
                   d. Read new state
                   e. Save to DB
                   f. Broadcast to WebSocket clients
        """
        while not self._stop_event.is_set():
            try:
                self._run_episode()
                self.state.episode_count += 1
                print(f"📊 Episode {self.state.episode_count} complete. Starting new episode...")
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                import traceback
                traceback.print_exc()
                # Try to close SUMO if it's open
                try:
                    traci.close()
                except:
                    pass
                # Wait before retrying
                time.sleep(3)

    def _run_episode(self):
        """Runs one complete simulation episode (1 hour of traffic)."""

        # ── START SUMO ────────────────────────────────────────────────────────
        sumo_binary = "sumo-gui" if USE_GUI else "sumo"
        sumo_cmd = [
            sumo_binary,
            "--net-file",    NET_FILE,
            "--route-files", ROUTE_FILE,
            "--no-step-log", "true",
            "--waiting-time-memory", "1000",
            "--time-to-teleport", "-1",
        ]
        traci.start(sumo_cmd)
        self.state.update(is_running=True)

        # Reset episode state
        current_phase  = 0
        time_in_phase  = 0
        step           = 0
        traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, 0)

        # Warm up: let vehicles enter
        for _ in range(5):
            traci.simulationStep()

        # ── EPISODE LOOP ──────────────────────────────────────────────────────
        while step < 360 and not self._stop_event.is_set():

            # ── GET CURRENT STATE ─────────────────────────────────────────────
            state_vector = get_state(traci, current_phase, time_in_phase)
            raw_state    = get_raw_state(traci)

            # ── DECIDE ACTION ─────────────────────────────────────────────────
            # Check for active override first
            with self.state._lock:
                override_active = (
                    self.state.override_phase is not None and
                    self.state.override_until is not None and
                    step < self.state.override_until
                )
                ai_mode = self.state.ai_mode

            if override_active:
                # Operator override: force the specified phase
                forced_phase = self.state.override_phase
                traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, forced_phase)
                current_phase = forced_phase
                time_in_phase = 0
                action        = ACTION_KEEP
                action_label  = "OVERRIDE"
            elif ai_mode and self.rl_service.is_loaded():
                # AI mode: ask the RL model for an action
                action = self.rl_service.predict(state_vector)
                action_label = get_action_meaning(action)
            else:
                # Manual mode: just keep current phase
                action       = ACTION_KEEP
                action_label = "MANUAL_KEEP"

            # ── APPLY FAIRNESS CONSTRAINTS ────────────────────────────────────
            if not override_active:
                validated_action, override_reason = self.constraint.validate_action(
                    action, time_in_phase, current_phase
                )
            else:
                validated_action = ACTION_KEEP
                override_reason  = "manual_override"

            # ── APPLY TO TRAFFIC LIGHT ────────────────────────────────────────
            if validated_action == ACTION_SWITCH and current_phase in GREEN_PHASES:
                yellow_phase = current_phase + 1
                traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, yellow_phase)
                current_phase = yellow_phase
                time_in_phase = 0

            # ── ADVANCE SUMO ──────────────────────────────────────────────────
            for _ in range(DELTA_TIME):
                traci.simulationStep()
                time_in_phase += 1

                # Handle yellow → green transition
                if current_phase in YELLOW_PHASES and time_in_phase >= YELLOW_DURATION:
                    next_green    = 2 if current_phase == 1 else 0
                    traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, next_green)
                    current_phase = next_green
                    time_in_phase = 0

            # ── CALCULATE REWARD ──────────────────────────────────────────────
            new_raw_state        = get_raw_state(traci)
            reward, reward_info  = calculate_reward(new_raw_state)

            # ── GET AI SUGGESTION (for dashboard, even in manual mode) ────────
            suggestion = None
            if self.rl_service.is_loaded():
                suggestion = self.rl_service.get_suggestion(
                    state_vector, new_raw_state
                )

            # ── UPDATE SHARED STATE ───────────────────────────────────────────
            self.state.update(
                traffic        = new_raw_state,
                current_phase  = current_phase,
                time_in_phase  = time_in_phase,
                step           = step,
                last_action    = action_label,
                last_reward    = reward,
                ai_suggestion  = suggestion,
            )

            # ── BROADCAST TO WEBSOCKET CLIENTS ────────────────────────────────
            if self.state.broadcast_callback:
                snapshot = self.state.get_snapshot()
                self.state.broadcast_callback(snapshot)

            step += 1

        # ── CLOSE SUMO ────────────────────────────────────────────────────────
        traci.close()
        self.state.update(is_running=False)