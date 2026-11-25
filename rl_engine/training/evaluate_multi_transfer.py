# rl_engine/training/evaluate_multi_transfer.py

"""
MULTI-INTERSECTION EVALUATION — 2x2 Grid

FAIR COMPARISON:
  Both controllers use the SAME India-style 8-phase clockwise program.
  The only difference is HOW LONG each phase lasts:

  Controller 1 (Fixed):    every phase = exactly 30 seconds
  Controller 2 (Pressure): phase duration = 15-60s based on traffic pressure

  This isolates the effect of adaptive timing vs fixed timing,
  which is exactly what we want to demonstrate.
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import traci
from rl_engine.environment.signal_program import install_clockwise_program

NET_FILE   = "simulation/nets/grid_2x2/network.net.xml"
ROUTE_FILE = "simulation/nets/grid_2x2/routes.rou.xml"

INTERSECTIONS = ["A", "B", "C", "D"]

# CORRECT incoming edges — traffic ARRIVING at each intersection
INCOMING = {
    "A": {"north": "N12A", "east": "B2A",  "south": "C2A", "west": "W12A"},
    "B": {"north": "N22B", "east": "E12B", "south": "D2B", "west": "A2B"},
    "C": {"north": "A2C",  "east": "D2C",  "south": "S12C","west": "W22C"},
    "D": {"north": "B2D",  "east": "E22D", "south": "S22D","west": "C2D"},
}

GREEN_PHASES    = [0, 2, 4, 6]
PHASE_DIRECTION = {0: "north", 2: "east", 4: "south", 6: "west"}
NEXT_GREEN      = {0: 2, 2: 4, 4: 6, 6: 0}

DELTA_TIME      = 10
FIXED_GREEN     = 30   # fixed timer holds every direction for exactly this long
MIN_GREEN       = 10   # pressure controller minimum
MAX_GREEN       = 60   # pressure controller maximum


def sumo_start():
    """Start SUMO and install India-style clockwise program on all 4 junctions."""
    traci.start([
        "sumo", "--net-file", NET_FILE,
        "--route-files", ROUTE_FILE,
        "--no-step-log", "true",
        "--waiting-time-memory", "1000",
        "--time-to-teleport", "-1",
    ])
    for tl_id in INTERSECTIONS:
        install_clockwise_program(tl_id, incoming_edges=INCOMING[tl_id])
    for _ in range(5):
        traci.simulationStep()


def total_wait():
    total = 0.0
    for tl_id in INTERSECTIONS:
        for edge in INCOMING[tl_id].values():
            total += traci.edge.getWaitingTime(edge)
    return total


def get_pressure(tl_id, direction):
    """queue × (1 + wait/60) — weights urgent queues higher."""
    edge  = INCOMING[tl_id][direction]
    queue = traci.edge.getLastStepHaltingNumber(edge)
    wait  = traci.edge.getWaitingTime(edge)
    return queue * (1.0 + wait / 60.0)


def run_controller(mode="fixed", num_episodes=3):
    """
    Runs either fixed or pressure controller — same program, same loop.

    mode="fixed":
      setPhaseDuration(FIXED_GREEN) every step → 30s per direction always

    mode="pressure":
      Compare current vs next direction pressure every DELTA_TIME seconds
      Extend if current pressure >= next, expire if next has 30%+ more
    """
    label = "Fixed 30s/direction" if mode == "fixed" else "Pressure-Based Adaptive"
    print(f"\n📊 Controller: {label}")
    avgs = []

    for ep in range(num_episodes):
        sumo_start()

        green_timer      = {tl: 0  for tl in INTERSECTIONS}
        last_green_phase = {tl: -1 for tl in INTERSECTIONS}
        waits            = []

        for step in range(360):

            for tl_id in INTERSECTIONS:
                phase = traci.trafficlight.getPhase(tl_id)

                if phase not in GREEN_PHASES:
                    continue   # yellow — SUMO handles it

                # Detect new green phase
                if phase != last_green_phase[tl_id]:
                    green_timer[tl_id]      = 0
                    last_green_phase[tl_id] = phase

                green_timer[tl_id] += DELTA_TIME
                t = green_timer[tl_id]

                if mode == "fixed":
                    # Fixed: always hold for FIXED_GREEN seconds
                    if t < FIXED_GREEN:
                        traci.trafficlight.setPhaseDuration(
                            tl_id, (FIXED_GREEN - t) + DELTA_TIME
                        )
                    else:
                        traci.trafficlight.setPhaseDuration(tl_id, 1)
                        green_timer[tl_id]      = 0
                        last_green_phase[tl_id] = -1

                else:  # pressure
                    # Min green guard
                    if t < MIN_GREEN:
                        traci.trafficlight.setPhaseDuration(
                            tl_id, (MIN_GREEN - t) + DELTA_TIME
                        )
                        continue

                    # Max green force-switch
                    if t >= MAX_GREEN:
                        traci.trafficlight.setPhaseDuration(tl_id, 1)
                        green_timer[tl_id]      = 0
                        last_green_phase[tl_id] = -1
                        continue

                    # Pressure comparison: current vs next direction
                    curr_dir = PHASE_DIRECTION[phase]
                    next_dir = PHASE_DIRECTION[NEXT_GREEN[phase]]
                    curr_p   = get_pressure(tl_id, curr_dir)
                    next_p   = get_pressure(tl_id, next_dir)

                    if next_p > curr_p * 1.3 and next_p > 0:
                        # Next direction needs it more — switch
                        traci.trafficlight.setPhaseDuration(tl_id, 1)
                        green_timer[tl_id]      = 0
                        last_green_phase[tl_id] = -1
                    else:
                        # Current direction still productive — extend
                        traci.trafficlight.setPhaseDuration(
                            tl_id, DELTA_TIME + 3
                        )

            for _ in range(DELTA_TIME):
                traci.simulationStep()

            waits.append(total_wait())

        traci.close()
        avg = np.mean(waits)
        avgs.append(avg)
        print(f"   Episode {ep+1}: avg_wait = {avg:.1f}s")

    return np.mean(avgs)


if __name__ == "__main__":
    print("=" * 68)
    print("  2×2 GRID — India-Style Clockwise: Fixed vs Adaptive Timing")
    print("  Both controllers use the same N→E→S→W one-direction rotation")
    print("=" * 68)

    fixed_avg    = run_controller(mode="fixed",    num_episodes=3)
    pressure_avg = run_controller(mode="pressure", num_episodes=3)

    pct = (fixed_avg - pressure_avg) / fixed_avg * 100 if fixed_avg > 0 else 0

    print("\n" + "=" * 68)
    print(f"  {'Controller':<32} {'Total Wait':>12} {'Per Junction':>14}")
    print("  " + "-" * 64)
    print(f"  {'India Fixed (30s per direction)':<32} "
          f"{fixed_avg:>11.1f}s {fixed_avg/4:>13.1f}s")
    print(f"  {'India Pressure-Adaptive':<32} "
          f"{pressure_avg:>11.1f}s {pressure_avg/4:>13.1f}s  "
          f"({pct:+.1f}%)")
    print("=" * 68)

    if pct > 0:
        print(f"\n  ✅ Adaptive timing reduced system wait by {pct:.1f}%")
        print(f"     vs the same fixed clockwise program.")
        print(f"\n  Summary across both phases of the project:")
        print(f"  Phase 3 (single junction, DQN):      91.1% reduction")
        print(f"  Phase 6 (2×2 grid, pressure-based): {pct:.1f}% reduction")
    else:
        print(f"\n  Fixed: {fixed_avg:.1f}s  Pressure: {pressure_avg:.1f}s")