# rl_engine/environment/neighbor_state.py

"""
NEIGHBOR STATE — Summarizes adjacent intersections for coordination

WHY THESE 4 NUMBERS?
Each agent needs to "see" enough about its neighbors to coordinate,
but not so much that the state space explodes. We give each agent:

  [neighbor_1_queue_normalized,
   neighbor_1_wait_normalized,
   neighbor_2_queue_normalized,
   neighbor_2_wait_normalized]

These 4 numbers answer the key coordination question:
"Is my neighbor currently overwhelmed? Should I hold back or push through?"

NEIGHBOR TOPOLOGY:
  A's neighbors: B (right), C (below)
  B's neighbors: A (left),  D (below)
  C's neighbors: A (above), D (right)
  D's neighbors: C (left),  B (above)

INCOMING EDGES per intersection:
  We read ALL edges coming into each intersection to get
  a total picture of how busy that intersection is.
"""

import numpy as np

# All edges feeding INTO each intersection
INTERSECTION_INCOMING = {
    "A": ["W12A", "N12A", "B2A",  "C2A"],
    "B": ["A2B",  "N22B", "E12B", "D2B"],
    "C": ["A2C",  "W22C", "D2C",  "S12C"],
    "D": ["C2D",  "B2D",  "E22D", "S22D"],
}

# Who are the two neighbors of each intersection?
NEIGHBORS = {
    "A": ["B", "C"],
    "B": ["A", "D"],
    "C": ["A", "D"],
    "D": ["C", "B"],
}

# Normalization caps — same philosophy as single-intersection observation_space
MAX_NEIGHBOR_QUEUE = 40    # neighbors have more incoming edges, expect larger queues
MAX_NEIGHBOR_WAIT  = 500.0


def get_neighbor_summary(traci, intersection_id: str) -> np.ndarray:
    """
    Reads TraCI data for the two neighbors of intersection_id
    and returns a 4-float normalized summary vector.

    Parameters:
        traci            - active TraCI connection
        intersection_id  - "A", "B", "C", or "D"

    Returns:
        numpy array of shape (4,), all values in [0, 1]
        [n1_queue, n1_wait, n2_queue, n2_wait]

    HOW TO READ THIS:
        If neighbor_summary = [0.8, 0.9, 0.1, 0.05]
        → neighbor 1 is heavily congested (queue=80% of max, wait=90% of max)
        → neighbor 2 is nearly empty
        → this agent should consider holding its green longer to
          help drain the traffic wave heading toward neighbor 1
    """
    neighbors = NEIGHBORS[intersection_id]
    summary = []

    for neighbor_id in neighbors:
        edges = INTERSECTION_INCOMING[neighbor_id]

        # Total queue (halting vehicles) across all incoming edges
        total_queue = sum(
            traci.edge.getLastStepHaltingNumber(e)
            for e in edges
        )

        # Total wait time across all incoming edges
        total_wait = sum(
            traci.edge.getWaitingTime(e)
            for e in edges
        )

        summary.append(
            np.clip(total_queue, 0, MAX_NEIGHBOR_QUEUE) / MAX_NEIGHBOR_QUEUE
        )
        summary.append(
            np.clip(total_wait, 0, MAX_NEIGHBOR_WAIT) / MAX_NEIGHBOR_WAIT
        )

    return np.array(summary, dtype=np.float32)


def get_all_neighbor_summaries(traci) -> dict:
    """
    Returns neighbor summaries for all 4 intersections at once.
    More efficient than calling get_neighbor_summary() 4 times separately
    because we read each edge only once.

    Returns:
        dict: { "A": array(4,), "B": array(4,), "C": array(4,), "D": array(4,) }
    """
    # Read all edge data once
    edge_queues = {}
    edge_waits  = {}

    all_edges = set()
    for edges in INTERSECTION_INCOMING.values():
        all_edges.update(edges)

    for edge in all_edges:
        try:
            edge_queues[edge] = traci.edge.getLastStepHaltingNumber(edge)
            edge_waits[edge]  = traci.edge.getWaitingTime(edge)
        except Exception:
            edge_queues[edge] = 0
            edge_waits[edge]  = 0.0

    # Build summaries from cached data
    summaries = {}
    for intersection_id in ["A", "B", "C", "D"]:
        neighbors = NEIGHBORS[intersection_id]
        summary   = []
        for neighbor_id in neighbors:
            edges = INTERSECTION_INCOMING[neighbor_id]
            q = sum(edge_queues.get(e, 0) for e in edges)
            w = sum(edge_waits.get(e, 0.0) for e in edges)
            summary.append(np.clip(q, 0, MAX_NEIGHBOR_QUEUE) / MAX_NEIGHBOR_QUEUE)
            summary.append(np.clip(w, 0, MAX_NEIGHBOR_WAIT) / MAX_NEIGHBOR_WAIT)
        summaries[intersection_id] = np.array(summary, dtype=np.float32)

    return summaries