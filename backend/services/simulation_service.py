# backend/services/simulation_service.py

"""
SIMULATION SERVICE — Manages the SUMO simulation

BUGFIXES IN THIS VERSION:
  1. Override state is cleared the MOMENT it expires, and again at the
     start of every new episode — so it can never "leak" into a future
     episode and get stuck forcing one phase forever.
  2. override_until is now compared against a GLOBAL step counter
     (one that never resets) instead of the per-episode step — so the
     comparison can never accidentally become true again after a reset.
  3. Every step now actually writes to the database (this was always
     missing — the tables existed but nothing ever filled them).
  4. A new `global_step` counter is added that NEVER resets across
     episodes — this becomes the single source of truth for the
     dashboard's STEP display and chart x-axis, so it can never go
     backwards or jump around.
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
    DELTA_TIME, USE_GUI, SUMO_HOME, STEP_REAL_SECONDS
)

if SUMO_HOME not in sys.path:
    tools = os.path.join(SUMO_HOME, 'tools')
    sys.path.append(tools)

from rl_engine.environment.observation_space import get_state, get_raw_state
from rl_engine.environment.action_space import (
    ACTION_KEEP, ACTION_SWITCH, GREEN_PHASES,
    YELLOW_PHASES, YELLOW_DURATION, NEXT_GREEN_PHASE,
    get_action_meaning, PHASE_NAMES
)
from rl_engine.environment.signal_program import install_clockwise_program
from rl_engine.constraints.fairness import FairnessConstraint
from rl_engine.environment.reward_function import calculate_reward

# ── NEW: database access for the background simulation thread ───────────────
# We can't use FastAPI's get_db() dependency here because this code runs in
# a plain background thread, not inside an HTTP request. SessionLocal lets
# us open/close our own session manually, which is exactly what a
# non-request context needs.
from backend.database.db import SessionLocal
from backend.database.crud import save_traffic_snapshot, save_signal_decision



os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

class SimulationState:
    """Shared state between the simulation thread and the API thread."""

    def __init__(self):
        self._lock = threading.Lock()

        self.traffic       = {}
        self.current_phase = 0
        self.time_in_phase = 0
        self.step          = 0     # resets every episode (used for episode length only)
        self.global_step   = 0     # NEW — never resets, drives the UI
        self.episode_count = 0
        self.timestamp      = datetime.utcnow().isoformat()

        self.last_action       = None
        self.last_reward       = 0.0
        self.ai_suggestion     = None
        self.ai_mode           = True

        self.override_phase    = None
        self.override_until    = None

        self.is_running        = False
        self.broadcast_callback = None

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self.timestamp = datetime.utcnow().isoformat()

    def get_snapshot(self):
        with self._lock:
            return {
                "traffic":       self.traffic,
                "current_phase": self.current_phase,
                "phase_name":    PHASE_NAMES.get(self.current_phase, "Unknown"),
                "time_in_phase": self.time_in_phase,
                "step":          self.global_step,   # dashboard now reads the GLOBAL counter
                "episode":       self.episode_count,
                "timestamp":     self.timestamp,
                "last_action":   self.last_action,
                "last_reward":   self.last_reward,
                "ai_suggestion": self.ai_suggestion,
                "ai_mode":       self.ai_mode,
                "is_running":    self.is_running,
            }


class SimulationService:

    def __init__(self, rl_service):
        self.rl_service  = rl_service
        self.state       = SimulationState()
        self.constraint  = FairnessConstraint()
        self._thread     = None
        self._stop_event = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            print("⚠️  Simulation already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="SimulationThread"
        )
        self._thread.start()
        print("🚀 Simulation thread started")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        print("🛑 Simulation stopped")

    def set_ai_mode(self, ai_mode: bool):
        self.state.update(ai_mode=ai_mode)
        print(f"🔄 Switched to {'AI' if ai_mode else 'Manual'} mode")

    def apply_override(self, phase: int, duration: int = None):
        """
        Forces a specific phase.

        BUGFIX: override_until is now measured against global_step
        (which never resets) instead of the per-episode step. This means
        an override can never accidentally "wake back up" after an
        episode restart.
        """
        steps = duration // DELTA_TIME if duration else 1
        with self.state._lock:
            self.state.override_phase = phase
            self.state.override_until = self.state.global_step + steps
        print(f"🔧 Override applied: Phase {phase} for {steps} step(s)")

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self._run_episode()
                self.state.episode_count += 1
                print(f"📊 Episode {self.state.episode_count} complete. Starting new episode...")
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                import traceback
                traceback.print_exc()
                try:
                    traci.getConnection("single").close()
                except Exception:
                    pass
                time.sleep(3)

    def _run_episode(self):

        # ── BUGFIX #1a: clear any leftover override from a previous episode ──
        self.state.update(override_phase=None, override_until=None)

        sumo_binary = "sumo-gui" if USE_GUI else "sumo"
        sumo_cmd = [
            sumo_binary,
            "--net-file",    NET_FILE,
            "--route-files", ROUTE_FILE,
            "--no-step-log", "true",
            "--waiting-time-memory", "300",
            "--time-to-teleport", "-1",
        ]
        traci.start(sumo_cmd, label="single")
        conn = traci.getConnection("single")
        self.conn = conn
        self.state.update(is_running=True)


        install_clockwise_program(TRAFFIC_LIGHT_ID)

        current_phase  = 0
        time_in_phase  = 0
        step           = 0
        conn.trafficlight.setPhase(TRAFFIC_LIGHT_ID, 0)

        for _ in range(5):
            conn.simulationStep()

        while step < 360 and not self._stop_event.is_set():

            state_vector = get_state(conn, current_phase, time_in_phase)
            raw_state    = get_raw_state(conn)

            with self.state._lock:
                override_active = (
                    self.state.override_phase is not None and
                    self.state.override_until is not None and
                    self.state.global_step < self.state.override_until
                )
                ai_mode = self.state.ai_mode

            phase_before = current_phase   # for the decision log

            # ── DECIDE ACTION ─────────────────────────────────────────────────
            if override_active:
                forced_phase = self.state.override_phase
                conn.trafficlight.setPhase(TRAFFIC_LIGHT_ID, forced_phase)
                current_phase = forced_phase
                time_in_phase = 0
                action        = ACTION_KEEP
                action_label  = "OVERRIDE"
            elif ai_mode and self.rl_service.is_loaded():
                action       = self.rl_service.predict(state_vector)
                action_label = get_action_meaning(action)
            else:
                # Fixed timer baseline: standard 30s per green phase
                if time_in_phase >= 30:
                    action       = ACTION_SWITCH
                    action_label = "FIXED_30S_SWITCH"
                else:
                    action       = ACTION_KEEP
                    action_label = "FIXED_30S_KEEP"

            # ── APPLY FAIRNESS CONSTRAINTS ────────────────────────────────────
            if not override_active:
                validated_action, override_reason = self.constraint.validate_action(
                    action, time_in_phase, current_phase
                )
            else:
                validated_action = ACTION_KEEP
                override_reason  = "manual_override"

            # ── BUGFIX #1b: the moment an override window expires, wipe it ───
            # immediately — don't wait for the next episode. This is the main
            # fix: a forgotten override can no longer outlive its window.
            if not override_active and self.state.override_phase is not None:
                self.state.update(override_phase=None, override_until=None)

            # ── APPLY TO TRAFFIC LIGHT ────────────────────────────────────────
            if validated_action == ACTION_SWITCH and current_phase in GREEN_PHASES:
                yellow_phase = current_phase + 1
                conn.trafficlight.setPhase(TRAFFIC_LIGHT_ID, yellow_phase)
                current_phase = yellow_phase
                time_in_phase = 0

            # ── ADVANCE SUMO ───────────────────────────────────────────────────
            for _ in range(DELTA_TIME):
                conn.simulationStep()
                time_in_phase += 1
                if current_phase in YELLOW_PHASES and time_in_phase >= YELLOW_DURATION:
                    green_before_yellow = current_phase - 1
                    next_green = NEXT_GREEN_PHASE[green_before_yellow]
                    conn.trafficlight.setPhase(TRAFFIC_LIGHT_ID, next_green)
                    current_phase = next_green
                    time_in_phase = 0

            # ── CALCULATE REWARD + SUGGESTION ─────────────────────────────────
            new_raw_state        = get_raw_state(conn)
            reward, reward_info  = calculate_reward(new_raw_state)

            suggestion = None
            if self.rl_service.is_loaded():
                suggestion = self.rl_service.get_suggestion(state_vector, new_raw_state)

            # ── NEW: advance the never-resetting global counter ──────────────
            new_global_step = self.state.global_step + 1

            # ── UPDATE SHARED STATE ────────────────────────────────────────────
            self.state.update(
                traffic        = new_raw_state,
                current_phase  = current_phase,
                time_in_phase  = time_in_phase,
                step           = step,
                global_step    = new_global_step,
                last_action    = action_label,
                last_reward    = reward,
                ai_suggestion  = suggestion,
            )

            # ── BUGFIX #2: actually persist this step to the database ────────
            # This was completely missing before — the tables existed but
            # nothing ever wrote to them, which is why Session Stats and the
            # Decision Log always showed zero/empty.
            db = SessionLocal()
            try:
                save_traffic_snapshot(
                    db, step=new_global_step, traffic_data=new_raw_state,
                    current_phase=current_phase, time_in_phase=time_in_phase
                )
                save_signal_decision(
                    db, step=new_global_step, action=validated_action,
                    action_label=action_label,
                    was_overridden=(action_label == "OVERRIDE"),
                    override_reason=override_reason,
                    phase_before=phase_before, phase_after=current_phase,
                    total_wait=reward_info["total_wait"], reward=reward,
                    ai_mode=ai_mode,
                )
            except Exception as db_err:
                print(f"⚠️  DB write failed: {db_err}")
            finally:
                db.close()

            # ── BROADCAST TO WEBSOCKET CLIENTS ────────────────────────────────
            if self.state.broadcast_callback:
                snapshot = self.state.get_snapshot()
                self.state.broadcast_callback(snapshot)

            # ── PACE THE LOOP FOR HUMAN-READABLE UPDATES ──────────────────────
            time.sleep(STEP_REAL_SECONDS)

            step += 1

        conn.close()
        self.state.update(is_running=False)