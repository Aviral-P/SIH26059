from typing import List, Dict

from backend.app.risk_engine import haversine_km


def calculate_route_risk(
    route: List[Dict[str, float]],
    iceberg_trajectory: List[Dict[str, float]],
    uncertainty_radius_km: float = 0.0,
    corridor_width_km: float = 10.0,
) -> dict:
    """
    Estimate whether an iceberg trajectory threatens a vessel route.

    Prototype approach:
    - Sampled route points are compared with predicted iceberg positions.
    - Forecast uncertainty expands the effective danger region.
    - Returns minimum separation and risk level.

    This is a prototype proximity model, not a calibrated
    collision-probability model.
    """

    if not route or not iceberg_trajectory:
        raise ValueError(
            "Route and iceberg trajectory cannot be empty"
        )

    minimum_distance = float("inf")
    closest_route_index = None
    closest_iceberg_index = None

    for route_index, route_point in enumerate(route):

        for iceberg_index, iceberg_point in enumerate(
            iceberg_trajectory
        ):

            distance = haversine_km(
                route_point["latitude"],
                route_point["longitude"],
                iceberg_point["latitude"],
                iceberg_point["longitude"],
            )

            if distance < minimum_distance:
                minimum_distance = distance
                closest_route_index = route_index
                closest_iceberg_index = iceberg_index

    effective_distance = max(
        0.0,
        minimum_distance - uncertainty_radius_km,
    )

    danger_width = (
        corridor_width_km
        + uncertainty_radius_km
    )

    if effective_distance <= 5.0:
        risk_level = "HIGH"

    elif effective_distance <= danger_width:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    return {
        "risk_level": risk_level,
        "minimum_separation_km": round(
            minimum_distance,
            3,
        ),
        "uncertainty_radius_km": round(
            uncertainty_radius_km,
            3,
        ),
        "effective_separation_km": round(
            effective_distance,
            3,
        ),
        "corridor_width_km": corridor_width_km,
        "closest_route_index": closest_route_index,
        "closest_iceberg_index": closest_iceberg_index,
    }