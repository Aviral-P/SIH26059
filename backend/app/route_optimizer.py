from heapq import heappush, heappop
from math import sqrt
from typing import List, Dict, Tuple

from app.risk_engine import haversine_km
from app.environment_cost import sea_ice_cost


PROFILES = {
    "safest": {
        "distance": 1.0,
        "ice": 5.0,
        "iceberg": 8.0,
    },
    "balanced": {
        "distance": 2.0,
        "ice": 3.0,
        "iceberg": 5.0,
    },
    "fuel_optimized": {
        "distance": 6.0,
        "ice": 1.5,
        "iceberg": 2.0,
    },
}


def grid_key(lat: float, lon: float) -> Tuple[int, int]:
    return (
        round(lat * 20),
        round(lon * 20),
    )


def key_to_coord(key: Tuple[int, int]) -> Tuple[float, float]:
    return (
        key[0] / 20.0,
        key[1] / 20.0,
    )


def neighbors(
    key: Tuple[int, int],
) -> List[Tuple[int, int]]:

    lat, lon = key

    return [
        (lat + 1, lon),
        (lat - 1, lon),
        (lat, lon + 1),
        (lat, lon - 1),
        (lat + 1, lon + 1),
        (lat + 1, lon - 1),
        (lat - 1, lon + 1),
        (lat - 1, lon - 1),
    ]


def point_risk(
    lat: float,
    lon: float,
    icebergs: List[Dict[str, float]],
) -> float:

    if not icebergs:
        return 0.0

    risk = 0.0

    for iceberg in icebergs:

        distance = haversine_km(
            lat,
            lon,
            iceberg["latitude"],
            iceberg["longitude"],
        )

        uncertainty = iceberg.get(
            "uncertainty_radius_km",
            0.0,
        )

        effective_distance = max(
            0.1,
            distance - uncertainty,
        )

        # Strong penalty near an iceberg.
        risk += 1.0 / effective_distance

    return risk


def reconstruct_path(
    came_from: Dict,
    current: Tuple[int, int],
) -> List[Tuple[int, int]]:

    path = [current]

    while current in came_from:
        current = came_from[current]
        path.append(current)

    path.reverse()

    return path


def optimize_route(
    start_lat: float,
    start_lon: float,
    destination_lat: float,
    destination_lon: float,
    icebergs: List[Dict[str, float]],
    profile: str = "balanced",
    sea_ice: List[Dict[str, float]] | None = None,
    grid_resolution: float = 0.05,
    max_iterations: int = 50000,
) -> dict:

    if profile not in PROFILES:
        raise ValueError(
            f"Unknown profile: {profile}. "
            f"Choose from {list(PROFILES.keys())}"
        )

    weights = PROFILES[profile]

    start = grid_key(start_lat, start_lon)
    goal = grid_key(destination_lat, destination_lon)

    open_set = []

    heappush(
        open_set,
        (0.0, start),
    )

    came_from = {}

    g_score = {
        start: 0.0
    }

    iterations = 0

    while open_set and iterations < max_iterations:

        iterations += 1

        _, current = heappop(open_set)

        if current == goal:

            path = reconstruct_path(
                came_from,
                current,
            )

            coordinates = [
                {
                    "latitude": key_to_coord(point)[0],
                    "longitude": key_to_coord(point)[1],
                }
                for point in path
            ]

            total_distance = 0.0
            total_risk = 0.0

            for i in range(1, len(coordinates)):

                total_distance += haversine_km(
                    coordinates[i - 1]["latitude"],
                    coordinates[i - 1]["longitude"],
                    coordinates[i]["latitude"],
                    coordinates[i]["longitude"],
                )

                total_risk += point_risk(
                    coordinates[i]["latitude"],
                    coordinates[i]["longitude"],
                    icebergs,
                )

            return {
                "status": "success",
                "profile": profile,
                "distance_km": round(
                    total_distance,
                    3,
                ),
                "risk_score": round(
                    total_risk,
                    3,
                ),
                "points": coordinates,
                "iterations": iterations,
            }

        current_lat, current_lon = key_to_coord(current)

        for neighbor in neighbors(current):

            neighbor_lat, neighbor_lon = key_to_coord(
                neighbor
            )

            distance = haversine_km(
                current_lat,
                current_lon,
                neighbor_lat,
                neighbor_lon,
            )

            iceberg_risk = point_risk(
                neighbor_lat,
                neighbor_lon,
                icebergs,
            )
            ice_risk = 0.0

            if sea_ice:
                for ice_cell in sea_ice:
                    distance = haversine_km(
                        neighbor_lat,
                        neighbor_lon,
                        ice_cell["latitude"],
                        ice_cell["longitude"],
                    )

                    if distance <= 5.0:
                        ice_risk = max(
                            ice_risk,
                            sea_ice_cost(
                                ice_cell["concentration"],
                                profile,
                            ),
                        )

            movement_cost = (
                weights["distance"] * distance
                + weights["iceberg"] * iceberg_risk
                + weights["ice"] * ice_risk
            )

            tentative_g = (
                g_score[current]
                + movement_cost
            )

            if (
                neighbor not in g_score
                or tentative_g < g_score[neighbor]
            ):

                came_from[neighbor] = current
                g_score[neighbor] = tentative_g

                heuristic = haversine_km(
                    neighbor_lat,
                    neighbor_lon,
                    destination_lat,
                    destination_lon,
                )

                f_score = (
                    tentative_g
                    + weights["distance"] * heuristic
                )

                heappush(
                    open_set,
                    (f_score, neighbor),
                )

    return {
        "status": "failed",
        "profile": profile,
        "reason": "No route found within iteration limit.",
    }