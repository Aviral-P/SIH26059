from app.route_optimizer import optimize_route


def generate_mission_routes(
    start_lat: float,
    start_lon: float,
    destination_lat: float,
    destination_lon: float,
    icebergs: list,
    sea_ice: list | None = None,
) -> dict:
    """
    Generate three alternative routes for a mission.

    Profiles:
    - safest
    - balanced
    - fuel_optimized
    """

    results = {}

    for profile in (
        "safest",
        "balanced",
        "fuel_optimized",
    ):
        results[profile] = optimize_route(
            start_lat=start_lat,
            start_lon=start_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            icebergs=icebergs,
            profile=profile,
            sea_ice=sea_ice,
        )

    successful = [
        result
        for result in results.values()
        if result["status"] == "success"
    ]

    if not successful:
        return {
            "status": "failed",
            "routes": results,
        }

    # Prototype recommendation:
    # safest profile is the default operational recommendation.
    recommended = "safest"

    return {
        "status": "success",
        "recommended_profile": recommended,
        "routes": results,
    }