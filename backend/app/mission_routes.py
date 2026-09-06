from backend.app.route_optimizer import optimize_route


def generate_mission_routes(
    start: dict,
    destination: dict,
    vessel_speed_knots: float = 10.0,
    sea_ice_data: list | None = None,
    iceberg_data: list | None = None,
    profile: str = "balanced",
) -> dict:
    """
    Generate three alternative routes for a mission.

    Profiles:
    - safest
    - balanced
    - fuel_optimized
    """

    if sea_ice_data is None:
        sea_ice_data = []

    if iceberg_data is None:
        iceberg_data = []

    start_lat = float(start["latitude"])
    start_lon = float(start["longitude"])

    destination_lat = float(
        destination["latitude"]
    )
    destination_lon = float(
        destination["longitude"]
    )

    results = {}

    for route_profile in (
        "safest",
        "balanced",
        "fuel_optimized",
    ):

        results[route_profile] = optimize_route(
            start_lat=start_lat,
            start_lon=start_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            icebergs=iceberg_data,
            profile=route_profile,
            sea_ice=sea_ice_data,
        )

    successful = [
        result
        for result in results.values()
        if isinstance(result, dict)
        and result.get("status") == "success"
    ]

    if not successful:
        return {
            "status": "failed",
            "recommended_profile": None,
            "routes": results,
        }

    # --------------------------------------------------------
    # Operational recommendation
    #
    # For the prototype, safest is the default recommendation
    # when it successfully produces a route.
    # --------------------------------------------------------

    if (
        profile in results
        and isinstance(results[profile], dict)
        and results[profile].get("status") == "success"
    ):
        recommended = profile

    elif (
        "safest" in results
        and isinstance(results["safest"], dict)
        and results["safest"].get("status") == "success"
    ):
        recommended = "safest"

    else:
        # Fallback to the first successful route.
        recommended = next(
            name
            for name, result in results.items()
            if isinstance(result, dict)
            and result.get("status") == "success"
        )

    return {
        "status": "success",
        "recommended_profile": recommended,
        "routes": results,
    }