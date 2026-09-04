from math import radians, sin, cos, sqrt, atan2


# Risk thresholds
HIGH_RISK_KM = 5.0
MEDIUM_RISK_KM = 15.0


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Great-circle distance between two WGS84 coordinates.
    """

    R = 6371.0

    lat1 = radians(lat1)
    lat2 = radians(lat2)

    dlat = lat2 - lat1
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def classify_risk(distance_km: float) -> str:
    """
    Classify iceberg proximity risk.

    These thresholds are operational prototype thresholds,
    not scientifically calibrated collision probabilities.
    """

    if distance_km <= HIGH_RISK_KM:
        return "HIGH"

    if distance_km <= MEDIUM_RISK_KM:
        return "MEDIUM"

    return "LOW"


def calculate_risk(
    vessel_lat: float,
    vessel_lon: float,
    iceberg_lat: float,
    iceberg_lon: float,
    uncertainty_radius_km: float = 0.0,
) -> dict:

    center_distance = haversine_km(
        vessel_lat,
        vessel_lon,
        iceberg_lat,
        iceberg_lon,
    )

    # Conservative distance: account for forecast uncertainty.
    effective_distance = max(
        0.0,
        center_distance - uncertainty_radius_km,
    )

    risk_level = classify_risk(effective_distance)

    return {
        "center_distance_km": round(center_distance, 3),
        "uncertainty_radius_km": round(
            uncertainty_radius_km,
            3,
        ),
        "effective_distance_km": round(
            effective_distance,
            3,
        ),
        "risk_level": risk_level,
    }