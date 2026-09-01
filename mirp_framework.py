"""
MIRP Decomposition Framework — Reference Implementation
========================================================

A three-stage decomposition approach for the Maritime Inventory Routing Problem
(MIRP) with cargo space utilisation for archipelagic bulk distribution.

Stage 1: K-Means clustering of destination ports + TSP for intra-cluster route
Stage 2: Integrated MILP for fleet sizing, voyage scheduling, cargo allocation,
         and inventory tracking (requires Gurobi or OR-Tools)
Stage 3: Inventory-aware supplementary voyage charter MILP

Reference:
    [Author names and paper citation to be inserted upon acceptance.]

Licence: MIT
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys
from typing import Any

# ---- Optional solver imports ----------------------------------------------
try:
    import gurobipy as gp  # type: ignore
    from gurobipy import GRB  # type: ignore
    _HAS_GUROBI = True
except ImportError:
    _HAS_GUROBI = False

try:
    from ortools.linear_solver import pywraplp  # type: ignore
    _HAS_ORTOOLS = True
except ImportError:
    _HAS_ORTOOLS = False

# ---- Constants ------------------------------------------------------------
EARTH_RADIUS_NM = 3440.065
DEFAULT_SEED = 42


# =============================================================================
# 1. INSTANCE LOADING
# =============================================================================

def load_instance(path: str) -> dict[str, Any]:
    """Load a JSON instance file and return the parsed dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# 2. UTILITIES
# =============================================================================

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return EARTH_RADIUS_NM * 2 * math.asin(math.sqrt(a))


# =============================================================================
# 3. STAGE 1a: K-MEANS CLUSTERING OF DESTINATION PORTS
# =============================================================================

def kmeans_cluster(
    destinations: list[dict[str, Any]],
    k: int,
    n_init: int = 20,
    max_iter: int = 100,
    seed: int = DEFAULT_SEED,
) -> list[list[str]]:
    """
    Partition destination ports into ``k`` clusters by K-Means (Lloyd's
    algorithm) on their (latitude, longitude) coordinates, with K-Means++
    initialisation and ``n_init`` random restarts.

    Returns
    -------
    list of list of str
        Each inner list contains the names of the ports assigned to that
        cluster.
    """
    random.seed(seed)
    names = [p["name"] for p in destinations]
    coords = [(p["lat"], p["lon"]) for p in destinations]
    n = len(coords)

    def eucl(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    best_sse = float("inf")
    best_labels: list[int] | None = None

    for _ in range(n_init):
        # K-Means++ initialisation
        centroids = [coords[random.randint(0, n - 1)]]
        for _ in range(1, k):
            dists = [min(eucl(c, ct) ** 2 for ct in centroids) for c in coords]
            total = sum(dists)
            if total == 0:
                centroids.append(coords[random.randint(0, n - 1)])
                continue
            r = random.random() * total
            cum = 0.0
            for idx, d in enumerate(dists):
                cum += d
                if cum >= r:
                    centroids.append(coords[idx])
                    break

        # Lloyd's iterations
        for _ in range(max_iter):
            labels = [
                min(range(k), key=lambda c: eucl(coords[i], centroids[c]))
                for i in range(n)
            ]
            new_centroids: list[tuple[float, float]] = []
            for c in range(k):
                members = [coords[i] for i in range(n) if labels[i] == c]
                if members:
                    new_centroids.append((
                        sum(m[0] for m in members) / len(members),
                        sum(m[1] for m in members) / len(members),
                    ))
                else:
                    new_centroids.append(centroids[c])
            if new_centroids == centroids:
                break
            centroids = new_centroids

        sse = sum(eucl(coords[i], centroids[labels[i]]) ** 2 for i in range(n))
        if sse < best_sse:
            best_sse = sse
            best_labels = labels[:]

    assert best_labels is not None
    clusters: dict[int, list[str]] = {}
    for i, lbl in enumerate(best_labels):
        clusters.setdefault(lbl, []).append(names[i])
    return [clusters[c] for c in sorted(clusters.keys())]


# =============================================================================
# 4. STAGE 1b: TSP PER CLUSTER (complete enumeration)
# =============================================================================

def solve_tsp(
    cluster_ports: list[str],
    origin: dict[str, Any],
    destinations: list[dict[str, Any]],
) -> list[str]:
    """
    Solve the Travelling Salesman Problem for a single cluster by complete
    enumeration of all permutations. Returns the visit sequence that
    minimises total round-trip sailing distance (origin -> cluster ports ->
    origin).
    """
    if len(cluster_ports) == 1:
        return cluster_ports[:]

    dest_by_name = {d["name"]: d for d in destinations}
    best_dist = float("inf")
    best_order: list[str] | None = None

    for perm in itertools.permutations(cluster_ports):
        total = 0.0
        prev_lat, prev_lon = origin["lat"], origin["lon"]
        for p_name in perm:
            p = dest_by_name[p_name]
            total += haversine_nm(prev_lat, prev_lon, p["lat"], p["lon"])
            prev_lat, prev_lon = p["lat"], p["lon"]
        total += haversine_nm(prev_lat, prev_lon, origin["lat"], origin["lon"])
        if total < best_dist:
            best_dist = total
            best_order = list(perm)

    assert best_order is not None
    return best_order


# =============================================================================
# 5. STAGE 2 & STAGE 3: MILP FORMULATIONS
# =============================================================================
# The full Stage 2 MILP formulation and Stage 3 inventory-aware supplementary
# charter MILP are described in detail in the associated paper (see reference
# above). Implementations require a mixed-integer programming solver such as
# Gurobi 11+ or Google OR-Tools.
#
# Skeleton function signatures are provided below. The full implementation is
# omitted from this public reference release; researchers wishing to reproduce
# the published computational results on the real industrial instance should
# contact the corresponding author (see data/DATA_LICENSE.md for details).
# =============================================================================

def solve_stage2_milp(
    instance: dict[str, Any],
    clusters: list[list[str]],
    routes: dict[int, list[str]],
    time_limit_sec: int = 3600,
    mip_gap: float = 0.02,
) -> dict[str, Any]:
    """
    Stage 2 integrated MILP:
      Objective: min TCH + VC + CHC + HC + SO + OC
      Decision variables: y_v, a_{v,c}, z_{v,c,t}, q_{v,c,p,t}, s_{p,t}, so_{p,t}
      Full formulation: see Appendix A of the associated paper.
    """
    if not (_HAS_GUROBI or _HAS_ORTOOLS):
        raise RuntimeError(
            "No MILP solver detected. Install Gurobi (pip install gurobipy) "
            "or OR-Tools (pip install ortools)."
        )
    raise NotImplementedError(
        "Stage 2 MILP implementation is available upon request. "
        "See data/DATA_LICENSE.md."
    )


def solve_stage3_supplementary(
    instance: dict[str, Any],
    stage2_solution: dict[str, Any],
    time_limit_sec: int = 1200,
) -> dict[str, Any]:
    """
    Stage 3 inventory-aware supplementary voyage charter MILP.
    Full formulation: see Appendix A of the associated paper.
    """
    raise NotImplementedError(
        "Stage 3 MILP implementation is available upon request. "
        "See data/DATA_LICENSE.md."
    )


# =============================================================================
# 6. COMMAND-LINE ENTRY POINT
# =============================================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MIRP decomposition framework — reference implementation"
    )
    parser.add_argument(
        "--instance",
        default="data/synthetic_instance.json",
        help="Path to the instance JSON file",
    )
    parser.add_argument(
        "-k", "--clusters", type=int, default=6,
        help="Number of clusters for Stage 1 (K-Means)",
    )
    parser.add_argument(
        "--stage",
        choices=["1", "2", "3", "all"],
        default="1",
        help="Which stages to run (Stage 2 and 3 require a MILP solver)",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help="Random seed for K-Means initialisation",
    )
    args = parser.parse_args(argv)

    print(f"Loading instance from: {args.instance}")
    instance = load_instance(args.instance)
    print(
        f"Instance summary: {len(instance['destinations'])} destination ports, "
        f"{len(instance['vessels'])} candidate vessels, "
        f"{instance['meta']['planning_horizon_days']}-day horizon."
    )

    # -- Stage 1a: clustering --
    print(f"\n[Stage 1a] K-Means clustering (k = {args.clusters})...")
    clusters = kmeans_cluster(
        instance["destinations"], k=args.clusters, seed=args.seed
    )
    for i, cl in enumerate(clusters, 1):
        print(f"  Cluster C{i}: {cl}")

    # -- Stage 1b: TSP per cluster --
    print(f"\n[Stage 1b] TSP per cluster...")
    routes = {}
    for i, cl_ports in enumerate(clusters):
        route = solve_tsp(cl_ports, instance["origin"], instance["destinations"])
        routes[i] = route
        print(f"  Cluster C{i+1} route: origin -> {' -> '.join(route)} -> origin")

    if args.stage == "1":
        print("\nStage 1 complete. Use --stage all to attempt Stages 2 and 3.")
        return 0

    # -- Stage 2: MILP --
    print(f"\n[Stage 2] Integrated MILP (fleet sizing + scheduling)...")
    try:
        stage2 = solve_stage2_milp(instance, clusters, routes)
        print(f"  Stage 2 objective: {stage2.get('objective', 'N/A')}")
    except NotImplementedError as e:
        print(f"  {e}")
        return 1

    if args.stage in ("2",):
        return 0

    # -- Stage 3: Supplementary charter --
    print(f"\n[Stage 3] Inventory-aware supplementary charter MILP...")
    try:
        stage3 = solve_stage3_supplementary(instance, stage2)
        print(f"  Stage 3 objective: {stage3.get('objective', 'N/A')}")
    except NotImplementedError as e:
        print(f"  {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
