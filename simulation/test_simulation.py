"""
test_simulation.py

PURPOSE:
This script tests that Python can talk to SUMO using TraCI.
TraCI = Traffic Control Interface

Think of TraCI as a remote control for SUMO.
With TraCI you can:
- Read how many cars are waiting at each signal
- Read vehicle speeds and positions
- Change traffic light phases IN REAL TIME

This is the foundation of our entire AI system.
"""

import os
import sys
import traci  # TraCI library — installed with SUMO

# ─── IMPORTANT ────────────────────────────────────────────────────────────────
# Tell Python where SUMO is installed.
# SUMO_HOME is the environment variable we set during installation.
# The 'tools' folder inside SUMO_HOME has helper Python scripts.
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please set the SUMO_HOME environment variable.")
# ──────────────────────────────────────────────────────────────────────────────


def run_simulation():
    """
    Starts SUMO, runs it for 200 steps, and prints traffic data.
    
    WHAT IS A SIMULATION STEP?
    Each step = 1 second of simulated time.
    In each step, all vehicles move, signals change, etc.
    Our AI will make a decision every N steps (e.g., every 10 seconds).
    """

    # Path to our config file
    config_path = "nets/single_intersection/simulation.sumocfg"

    # sumoCmd = the command to start SUMO
    # We use "sumo" (no GUI) for speed. Use "sumo-gui" to see it visually.
    sumo_binary = "sumo"   # Change to "sumo-gui" to see the visual simulation
    sumo_cmd = [sumo_binary, "-c", config_path]

    # ── START SUMO ────────────────────────────────────────────────────────────
    # traci.start() launches SUMO as a subprocess
    # and opens a communication channel between Python and SUMO
    traci.start(sumo_cmd)
    print("✅ SUMO started successfully!")

    # The traffic light ID at our intersection (matches node id="C" in network.xml)
    traffic_light_id = "C"

    # ── RUN SIMULATION LOOP ───────────────────────────────────────────────────
    step = 0
    while step < 200:  # Run for 200 seconds

        # simulationStep() advances time by 1 second
        # All vehicles move, lights tick, etc.
        traci.simulationStep()

        # Every 10 steps, print traffic information
        if step % 10 == 0:
            print(f"\n--- Step {step} ---")

            # ── READ TRAFFIC LIGHT STATE ──────────────────────────────────────
            # getCurrentPhase() returns which phase the light is in (0, 1, 2, 3)
            # Recall from network.xml: phase 0=NS green, 2=EW green
            current_phase = traci.trafficlight.getPhase(traffic_light_id)
            phase_names = {0: "NS Green", 1: "NS Yellow", 2: "EW Green", 3: "EW Yellow"}
            print(f"  Traffic Light Phase: {phase_names.get(current_phase, current_phase)}")

            # ── READ QUEUE LENGTHS ────────────────────────────────────────────
            # getLastStepHaltingNumber() = number of cars nearly stopped
            # on a specific road edge (speed < 0.1 m/s)
            for edge_id in ["N2C", "S2C", "E2C", "W2C"]:
                queue = traci.edge.getLastStepHaltingNumber(edge_id)
                vehicles = traci.edge.getLastStepVehicleNumber(edge_id)
                wait = traci.edge.getWaitingTime(edge_id)
                print(f"  {edge_id}: {vehicles} vehicles, {queue} queued, {wait:.1f}s total wait")

        step += 1

    # ── STOP SUMO ─────────────────────────────────────────────────────────────
    # Always close the connection when done!
    traci.close()
    print("\n✅ Simulation finished!")


if __name__ == "__main__":
    run_simulation()