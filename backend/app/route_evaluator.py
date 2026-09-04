from typing import Dict, List

from app.risk_engine import haversine_km


def evaluate_route(
    route: Dict,
    icebergs: List[Dict[str, float]],
    sea_ice: List[Dict[str, float]] | None = None,
    vessel_speed_knots: float = 10.0,
) -> Dict:
    """
    Evaluate a generated route using operational metrics.

    Prototype decision-support metrics.
    Not a certified navigation model.
    """

    points = route.get("points", [])

    if not points:
        return {
            "status": "invalid",
            "reason": "Route contains no points.",
        }

    # ---------------------------------------------------------
    # 1. Distance
    # ---------------------------------------------------------

    distance_km = 0.0

    for i in range(1, len(points)):
        distance_km += haversine_km(
            points[i - 1]["latitude"],
            points[i - 1]["longitude"],
            points[i]["latitude"],
            points[i]["longitude"],
        )

    # ---------------------------------------------------------
    # 2. Estimated travel time
    # ---------------------------------------------------------

    speed_kmh = vessel_speed_knots * 1.852

    estimated_hours = (
        distance_km / speed_kmh
        if speed_kmh > 0
        else None
    )

    # ---------------------------------------------------------
    # 3. Iceberg exposure
    # ---------------------------------------------------------

    iceberg_exposure = 0.0
    minimum_iceberg_distance = float("inf")

    for point in points:

        for iceberg in icebergs:

            distance = haversine_km(
                point["latitude"],
                point["longitude"],
                iceberg["latitude"],
                iceberg["longitude"],
            )

            uncertainty = iceberg.get(
                "uncertainty_radius_km",
                0.0,
            )

            effective_distance = max(
                0.0,
                distance - uncertainty,
            )

            minimum_iceberg_distance = min(
                minimum_iceberg_distance,
                effective_distance,
            )

            if effective_distance < 20:
                iceberg_exposure += (
                    (20 - effective_distance) / 20
                )

    # ---------------------------------------------------------
    # 4. Sea-ice exposure
    # ---------------------------------------------------------

    sea_ice_exposure = 0.0

    if sea_ice:

        for point in points:

            for cell in sea_ice:

                distance = haversine_km(
                    point["latitude"],
                    point["longitude"],
                    cell["latitude"],
                    cell["longitude"],
                )

                if distance <= 5.0:

                    concentration = cell.get(
                        "concentration",
                        0.0,
                    )

                    sea_ice_exposure += concentration

    # ---------------------------------------------------------
    # 5. Overall operational score
    # ---------------------------------------------------------

    # Lower is better.
    overall_score = (
        distance_km * 0.05
        + iceberg_exposure * 2.0
        + sea_ice_exposure * 0.5
    )

    if minimum_iceberg_distance <= 5:
        risk_level = "HIGH"
    elif minimum_iceberg_distance <= 15:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "status": "success",
        "distance_km": round(distance_km, 3),
        "estimated_hours": round(
            estimated_hours,
            2,
        ) if estimated_hours is not None else None,
        "vessel_speed_knots": vessel_speed_knots,
        "iceberg_exposure": round(
            iceberg_exposure,
            3,
        ),
        "sea_ice_exposure": round(
            sea_ice_exposure,
            3,
        ),
        "minimum_iceberg_separation_km": round(
            minimum_iceberg_distance,
            3,
        ),
        "risk_level": risk_level,
        "overall_score": round(
            overall_score,
            3,
        ),
    }