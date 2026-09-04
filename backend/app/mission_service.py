from typing import List, Dict

from app.mission_routes import generate_mission_routes
from app.route_evaluator import evaluate_route


def plan_mission(
    start_lat: float,
    start_lon: float,
    destination_lat: float,
    destination_lon: float,
    icebergs: List[Dict],
    sea_ice: List[Dict] | None = None,
    vessel_speed_knots: float = 10.0,
) -> dict:
    """
    End-to-end Antarctic mission planning.

    Combines:
        iceberg information
        sea-ice information
        route optimization
        route evaluation

    Prototype decision-support system.
    """

    route_result = generate_mission_routes(
        start_lat=start_lat,
        start_lon=start_lon,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
        icebergs=icebergs,
        sea_ice=sea_ice,
    )

    if route_result["status"] != "success":
        return route_result

    evaluated_routes = {}

    for profile, route in route_result["routes"].items():

        if route["status"] != "success":
            evaluated_routes[profile] = route
            continue

        evaluation = evaluate_route(
            route=route,
            icebergs=icebergs,
            sea_ice=sea_ice,
            vessel_speed_knots=vessel_speed_knots,
        )

        evaluated_routes[profile] = {
            "route": route,
            "evaluation": evaluation,
        }

    # ---------------------------------------------------------
    # Recommendation
    # ---------------------------------------------------------

    successful = {
        profile: result
        for profile, result in evaluated_routes.items()
        if result.get("evaluation", {}).get("status") == "success"
    }

    if not successful:
        return {
            "status": "failed",
            "reason": "No valid route evaluations.",
        }

    recommended_profile = min(
        successful,
        key=lambda profile:
            successful[profile]["evaluation"]["overall_score"]
    )

    return {
        "status": "success",
        "recommended_profile": recommended_profile,
        "routes": evaluated_routes,
    }