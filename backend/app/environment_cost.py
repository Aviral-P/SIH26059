def sea_ice_cost(
    concentration: float | None,
    profile: str = "balanced",
) -> float:
    """
    Convert sea-ice concentration [0, 1] into a route penalty.

    Prototype decision-support weights, not calibrated navigation rules.
    """

    if concentration is None:
        return 0.0

    concentration = max(0.0, min(1.0, concentration))

    weights = {
        "safest": 8.0,
        "balanced": 4.0,
        "fuel_optimized": 1.5,
    }

    weight = weights.get(profile, weights["balanced"])

    return concentration * weight