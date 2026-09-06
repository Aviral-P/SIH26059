from typing import Any, Dict, List

from backend.app.mission_routes import generate_mission_routes


def plan_mission(
    start: Dict[str, float],
    destination: Dict[str, float],
    vessel_speed_knots: float = 10.0,
    sea_ice_data: Any = None,
    iceberg_data: List[Dict[str, Any]] | None = None,
    profile: str = "balanced",
) -> Dict[str, Any]:
    """
    Generate and evaluate mission routes.

    This service acts as the orchestration layer between
    the API and the route-generation engine.
    """

    if iceberg_data is None:
        iceberg_data = []

    if sea_ice_data is None:
        sea_ice_data = []

    if not start or not destination:
        raise ValueError(
            "start and destination are required"
        )

    if (
        "latitude" not in start
        or "longitude" not in start
    ):
        raise ValueError(
            "start must contain latitude and longitude"
        )

    if (
        "latitude" not in destination
        or "longitude" not in destination
    ):
        raise ValueError(
            "destination must contain latitude and longitude"
        )

    if vessel_speed_knots <= 0:
        raise ValueError(
            "vessel_speed_knots must be greater than 0"
        )

    routes = generate_mission_routes(
        start=start,
        destination=destination,
        vessel_speed_knots=vessel_speed_knots,
        sea_ice_data=sea_ice_data,
        iceberg_data=iceberg_data,
        profile=profile,
    )

    if not routes:
        return {
            "status": "no_route",
            "message": "No feasible route could be generated.",
            "routes": [],
        }

    # --------------------------------------------------------
    # generate_mission_routes() returns a structured response
    # containing the route alternatives.
    # --------------------------------------------------------

    if routes.get("status") != "success":
        return {
            "status": "no_route",
            "message": "No feasible route could be generated.",
            "routes": routes.get("routes", {}),
        }

    route_options = routes.get("routes", {})

    successful_routes = [
        route
        for route in route_options.values()
        if isinstance(route, dict)
        and route.get("status") == "success"
    ]

    if not successful_routes:
        return {
            "status": "no_route",
            "message": "No feasible route could be generated.",
            "routes": route_options,
        }

    # --------------------------------------------------------
    # Use the route-generation layer's recommendation when
    # available.
    # --------------------------------------------------------

    recommended_profile = routes.get(
        "recommended_profile",
        profile,
    )

    recommended_route = route_options.get(
        recommended_profile
    )

    # Fallback if the recommended profile failed.
    if not isinstance(recommended_route, dict) or (
        recommended_route.get("status") != "success"
    ):

        recommended_route = min(
            successful_routes,
            key=lambda route: route.get(
                "overall_score",
                float("inf"),
            ),
        )

        for name, route in route_options.items():

            if route is recommended_route:
                recommended_profile = name
                break

    return {
        "status": "success",
        "selected_profile": recommended_profile,
        "recommended_route": recommended_route,
        "routes": route_options,
        "route_count": len(successful_routes),
    }