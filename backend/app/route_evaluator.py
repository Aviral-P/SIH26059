from typing import Dict, List
from backend.app.risk_engine import haversine_km


SEA_ICE_SEARCH_RADIUS_KM = 18.0
ICEBERG_HAZARD_RADIUS_KM = 20.0


def evaluate_route(
    route,
    icebergs,
    sea_ice=None,
    vessel_speed_knots=10.0,
) -> Dict:
    """
    Evaluate a generated route against environmental hazards.

    Existing route-level metrics are preserved.

    Additional output:
        iceberg_hazards:
            Per-iceberg proximity information used by the
            Global Route Hazard Watch.

    NOTE:
        The iceberg hazard calculation is a proximity-based
        operational indicator. It is NOT a calibrated collision
        probability.
    """

    points = route.get("points", [])

    if not points:
        return {
            "status": "invalid",
            "message": "Route contains no points",
        }

    # ---------------------------------------------------------
    # 1. ROUTE DISTANCE
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
    # 2. ETA
    # ---------------------------------------------------------

    speed_kmh = vessel_speed_knots * 1.852

    estimated_hours = (
        distance_km / speed_kmh
        if speed_kmh > 0
        else 0.0
    )

    # ---------------------------------------------------------
    # 3. ICEBERG EXPOSURE
    # ---------------------------------------------------------

    iceberg_exposure = 0.0
    minimum_iceberg_distance = float("inf")

    # New:
    # Keep a separate record for every iceberg so the frontend
    # can identify hazards that are not the selected iceberg.
    iceberg_hazards: List[Dict] = []

    for iceberg in icebergs:
        iceberg_id = str(
            iceberg.get("iceberg_id")
            or iceberg.get("id")
            or iceberg.get("source_id")
            or "UNKNOWN"
        )

        uncertainty = float(
            iceberg.get("uncertainty_radius_km", 0.0) or 0.0
        )

        iceberg_minimum_distance = float("inf")

        # Find the closest point on the route to this iceberg.
        for point in points:
            current_distance = haversine_km(
                point["latitude"],
                point["longitude"],
                iceberg["latitude"],
                iceberg["longitude"],
            )

            iceberg_minimum_distance = min(
                iceberg_minimum_distance,
                current_distance,
            )

            minimum_iceberg_distance = min(
                minimum_iceberg_distance,
                current_distance,
            )

            # Preserve existing exposure logic.
            effective_distance = max(
                0.0,
                current_distance - uncertainty,
            )

            if effective_distance < ICEBERG_HAZARD_RADIUS_KM:
                iceberg_exposure += (
                    ICEBERG_HAZARD_RADIUS_KM
                    - effective_distance
                ) / ICEBERG_HAZARD_RADIUS_KM

        # -----------------------------------------------------
        # Per-iceberg operational assessment
        # -----------------------------------------------------

        if iceberg_minimum_distance == float("inf"):
            continue

        effective_separation = max(
            0.0,
            iceberg_minimum_distance - uncertainty,
        )

        if effective_separation <= 5.0:
            risk_level = "HIGH"
        elif effective_separation <= 15.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        iceberg_hazards.append(
            {
                "iceberg_id": iceberg_id,
                "minimum_separation_km": round(
                    iceberg_minimum_distance,
                    2,
                ),
                "uncertainty_radius_km": round(
                    uncertainty,
                    2,
                ),
                "effective_separation_km": round(
                    effective_separation,
                    2,
                ),
                "risk_level": risk_level,
                "is_route_hazard": (
                    effective_separation
                    <= ICEBERG_HAZARD_RADIUS_KM
                ),
            }
        )

    # Closest hazards first.
    iceberg_hazards.sort(
        key=lambda item: item["effective_separation_km"]
    )

    # ---------------------------------------------------------
    # 4. SEA ICE EXPOSURE
    # ---------------------------------------------------------

    sea_ice_exposure = 0.0
    max_sea_ice_concentration = 0.0

    if sea_ice:
        for point in points:
            for cell in sea_ice:
                cell_lat = cell.get("lat")
                cell_lon = cell.get("lon")
                concentration = cell.get(
                    "concentration",
                    0.0,
                )

                if (
                    cell_lat is None
                    or cell_lon is None
                ):
                    continue

                cell_distance = haversine_km(
                    point["latitude"],
                    point["longitude"],
                    cell_lat,
                    cell_lon,
                )

                if cell_distance <= SEA_ICE_SEARCH_RADIUS_KM:
                    concentration = float(
                        concentration or 0.0
                    )

                    max_sea_ice_concentration = max(
                        max_sea_ice_concentration,
                        concentration,
                    )

                    sea_ice_exposure += concentration

                    break

    # ---------------------------------------------------------
    # 5. OVERALL SCORE
    # ---------------------------------------------------------

    overall_score = (
        distance_km * 0.05
        + iceberg_exposure * 2.0
        + sea_ice_exposure * 0.5
    )

    # ---------------------------------------------------------
    # 6. ROUTE-LEVEL RISK
    # ---------------------------------------------------------

    if minimum_iceberg_distance == float("inf"):
        minimum_iceberg_distance = None
        risk_level = "LOW"

    elif minimum_iceberg_distance <= 5.0:
        risk_level = "HIGH"

    elif minimum_iceberg_distance <= 15.0:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    # ---------------------------------------------------------
    # 7. RESULT
    # ---------------------------------------------------------

    return {
        "status": "success",

        # Existing fields
        "distance_km": round(distance_km, 2),
        "estimated_hours": round(estimated_hours, 2),
        "vessel_speed_knots": vessel_speed_knots,

        "iceberg_exposure": round(
            iceberg_exposure,
            3,
        ),

        "sea_ice_exposure": round(
            sea_ice_exposure,
            3,
        ),

        "max_sea_ice_concentration": round(
            max_sea_ice_concentration,
            3,
        ),

        "minimum_iceberg_separation_km": (
            round(minimum_iceberg_distance, 2)
            if minimum_iceberg_distance is not None
            else None
        ),

        "risk_level": risk_level,

        "overall_score": round(
            overall_score,
            3,
        ),

        # -----------------------------------------------------
        # NEW
        # -----------------------------------------------------
        # Used by Global Route Hazard Watch.
        #
        # Contains all icebergs, sorted by effective
        # separation from the route.
        "iceberg_hazards": iceberg_hazards,
    }