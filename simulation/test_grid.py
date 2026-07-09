"""
test_grid.py

Verifies that TraCI can connect to the 2x2 grid simulation
and read data from all 4 intersections simultaneously.

This is the exact same pattern as test_simulation.py from Phase 1,
but now we loop over 4 traffic light IDs instead of 1.
"""

import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci

TRAFFIC_LIGHTS = ["A", "B", "C", "D"]

INCOMING_EDGES = {
    "A": ["W12A", "N12A", "B2A", "C2A"],
    "B": ["A2B",  "N22B", "E12B", "D2B"],
    "C": ["A2C",  "W22C", "D2C", "S12C"],
    "D": ["C2D",  "B2D",  "E22D", "S22D"],
}

def run():
    config = "nets/grid_2x2/simulation.sumocfg"
    traci.start(["sumo", "-c", config])
    print("✅ Grid simulation started")

    for step in range(150):
        traci.simulationStep()

        if step % 30 == 0:
            print(f"\n── Step {step} ──────────────────────────")
            for tl_id in TRAFFIC_LIGHTS:
                phase = traci.trafficlight.getPhase(tl_id)
                total_queue = sum(
                    traci.edge.getLastStepHaltingNumber(e)
                    for e in INCOMING_EDGES[tl_id]
                )
                total_wait = sum(
                    traci.edge.getWaitingTime(e)
                    for e in INCOMING_EDGES[tl_id]
                )
                print(f"  [{tl_id}] phase={phase:>2}  "
                      f"queue={total_queue:>3}  "
                      f"wait={total_wait:>7.1f}s")

    traci.close()
    print("\n✅ Grid test complete!")

if __name__ == "__main__":
    run()