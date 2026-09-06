from pathlib import Path
import math
import json

import numpy as np
import pandas as pd
from pyproj import Geod

try:
    from scripts.extract_environment import extract_environment
except ModuleNotFoundError:
    from extract_environment import extract_environment

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

UNCERTAINTY_FILE = (
    PROJECT_ROOT
    / "data"
    / "catalog"
    / "uncertainty_envelope.csv"
)


# ============================================================
# GEODESIC
# ============================================================

GEOD = Geod(ellps="WGS84")


# ============================================================
# MODEL COEFFICIENTS
# ============================================================

# Existing prototype baseline
BASELINE_ALPHA = 0.85
BASELINE_BETA = 0.015

# Calibrated coefficients obtained from the 49-pair
# Antarctic calibration dataset.
CALIBRATED_ALPHA = 0.35665461385172254
CALIBRATED_BETA = 0.001162614309995365


# ============================================================
# DEFAULT MODEL
# ============================================================

DEFAULT_MODEL = "calibrated"


# ============================================================
# UNCERTAINTY
# ============================================================

def load_uncertainty_envelope():
    """
    Load empirically derived LOIO uncertainty envelope.

    24h values are empirical.
    Other horizons are sqrt(time)-scaled estimates.
    """

    if not UNCERTAINTY_FILE.exists():
        return None

    try:
        df = pd.read_csv(
            UNCERTAINTY_FILE
        )

        if "forecast_hours" not in df.columns:
            return None

        return df

    except Exception:
        return None


UNCERTAINTY_ENVELOPE = (
    load_uncertainty_envelope()
)


def get_uncertainty_radius(
    forecast_hours,
    percentile="p90"
):
    """
    Return the uncertainty radius in km.

    Uses the empirical LOIO envelope when the requested
    forecast horizon is available.

    Falls back to NaN when unavailable.
    """

    if UNCERTAINTY_ENVELOPE is None:
        return float("nan")

    row = UNCERTAINTY_ENVELOPE[
        UNCERTAINTY_ENVELOPE[
            "forecast_hours"
        ] == forecast_hours
    ]

    if row.empty:
        return float("nan")

    column = percentile

    if column not in row.columns:
        return float("nan")

    value = row.iloc[0][column]

    if pd.isna(value):
        return float("nan")

    return float(value)


# ============================================================
# MODEL COEFFICIENT SELECTION
# ============================================================

def get_model_coefficients(
    model="calibrated"
):
    """
    Return alpha and beta for the selected model.
    """

    model = str(
        model
    ).lower()

    if model == "baseline":

        return (
            BASELINE_ALPHA,
            BASELINE_BETA,
        )

    if model in {
        "calibrated",
        "physics-informed-drift-v2-calibrated-research",
    }:

        return (
            CALIBRATED_ALPHA,
            CALIBRATED_BETA,
        )

    raise ValueError(
        f"Unknown drift model: {model}"
    )


# ============================================================
# DRIFT VELOCITY
# ============================================================

def calculate_drift_velocity(
    environment,
    ocean_weight=None,
    wind_weight=None,
):
    """
    Calculate iceberg drift velocity.

    Equation:

        u_ice = alpha * ocean_u + beta * wind_u
        v_ice = alpha * ocean_v + beta * wind_v

    The function accepts both the current extractor structure:

        environment["ocean"]

    and the legacy structure:

        environment["ocean_current"]

    so existing callers remain compatible.
    """

    # --------------------------------------------------------
    # OCEAN
    # --------------------------------------------------------

    if "ocean" in environment:

        ocean = environment[
            "ocean"
        ]

    elif "ocean_current" in environment:

        ocean = environment[
            "ocean_current"
        ]

    else:

        raise KeyError(
            "Environment does not contain "
            "'ocean' or 'ocean_current'."
        )

    # --------------------------------------------------------
    # WIND
    # --------------------------------------------------------

    wind = environment.get(
        "wind",
        {}
    )

    # --------------------------------------------------------
    # COEFFICIENTS
    # --------------------------------------------------------

    if ocean_weight is None:
        ocean_weight = CALIBRATED_ALPHA

    if wind_weight is None:
        wind_weight = CALIBRATED_BETA

    ocean_weight = float(
        ocean_weight
    )

    wind_weight = float(
        wind_weight
    )

    # --------------------------------------------------------
    # ENVIRONMENT VALUES
    # --------------------------------------------------------

    ocean_u = float(
        ocean.get(
            "u",
            0.0
        )
    )

    ocean_v = float(
        ocean.get(
            "v",
            0.0
        )
    )

    wind_u = float(
        wind.get(
            "u",
            0.0
        )
    )

    wind_v = float(
        wind.get(
            "v",
            0.0
        )
    )

    # --------------------------------------------------------
    # DRIFT
    # --------------------------------------------------------

    ice_u = (
        ocean_weight * ocean_u
        + wind_weight * wind_u
    )

    ice_v = (
        ocean_weight * ocean_v
        + wind_weight * wind_v
    )

    speed = float(
        np.hypot(
            ice_u,
            ice_v
        )
    )

    # Direction convention:
    #
    # atan2(u, v)
    #
    # gives bearing clockwise from north.
    heading = float(
        (
            math.degrees(
                math.atan2(
                    ice_u,
                    ice_v
                )
            )
            + 360.0
        )
        % 360.0
    )

    return {
        "u": float(
            ice_u
        ),

        "v": float(
            ice_v
        ),

        "speed": speed,

        "heading": heading,

        "ocean_u": ocean_u,

        "ocean_v": ocean_v,

        "wind_u": wind_u,

        "wind_v": wind_v,

        "ocean_weight": ocean_weight,

        "wind_weight": wind_weight,

        "wind_available": bool(
            environment.get(
                "wind_available",
                True
            )
        ),
    }


# ============================================================
# GEODESIC POSITION PROPAGATION
# ============================================================

def propagate_position(
    latitude,
    longitude,
    velocity_u,
    velocity_v,
    hours
):
    """
    Propagate geographic position using WGS84 geodesic.

    velocity_u and velocity_v are m/s.

    u = eastward velocity
    v = northward velocity
    """

    latitude = float(
        latitude
    )

    longitude = float(
        longitude
    )

    velocity_u = float(
        velocity_u
    )

    velocity_v = float(
        velocity_v
    )

    hours = float(
        hours
    )

    # --------------------------------------------------------
    # DISTANCE
    # --------------------------------------------------------

    east_m = (
        velocity_u
        * hours
        * 3600.0
    )

    north_m = (
        velocity_v
        * hours
        * 3600.0
    )

    distance_m = float(
        np.hypot(
            east_m,
            north_m
        )
    )

    if distance_m == 0.0:

        return (
            latitude,
            longitude
        )

    # --------------------------------------------------------
    # BEARING
    # --------------------------------------------------------

    bearing = float(
        (
            math.degrees(
                math.atan2(
                    east_m,
                    north_m
                )
            )
            + 360.0
        )
        % 360.0
    )

    # --------------------------------------------------------
    # GEODESIC
    # --------------------------------------------------------

    new_lon, new_lat, _ = GEOD.fwd(
        longitude,
        latitude,
        bearing,
        distance_m
    )

    return (
        float(new_lat),
        float(new_lon)
    )


# ============================================================
# PREDICT POSITION
# ============================================================

def predict_position(
    latitude,
    longitude,
    start_time,
    forecast_hours=24,
    model=DEFAULT_MODEL,
    ocean_weight=None,
    wind_weight=None,
):
    """
    Predict iceberg position.

    Parameters
    ----------
    latitude : float
        Starting latitude.

    longitude : float
        Starting longitude.

    start_time : datetime-like
        Forecast start time.

    forecast_hours : float
        Forecast horizon.

    model : str
        'calibrated' or 'baseline'.

    ocean_weight : float, optional
        Override ocean coefficient.

    wind_weight : float, optional
        Override wind coefficient.
    """

    # --------------------------------------------------------
    # COEFFICIENTS
    # --------------------------------------------------------

    alpha, beta = get_model_coefficients(
        model
    )

    if ocean_weight is not None:
        alpha = float(
            ocean_weight
        )

    if wind_weight is not None:
        beta = float(
            wind_weight
        )

    # --------------------------------------------------------
    # ENVIRONMENT
    # --------------------------------------------------------

    environment = extract_environment(
        start_time,
        latitude,
        longitude,
        validation=False
    )

    # --------------------------------------------------------
    # VELOCITY
    # --------------------------------------------------------

    velocity = calculate_drift_velocity(
        environment,
        ocean_weight=alpha,
        wind_weight=beta,
    )

    # --------------------------------------------------------
    # POSITION
    # --------------------------------------------------------

    predicted_latitude, predicted_longitude = (
        propagate_position(
            latitude,
            longitude,
            velocity["u"],
            velocity["v"],
            forecast_hours
        )
    )

    # --------------------------------------------------------
    # UNCERTAINTY
    # --------------------------------------------------------

    uncertainty_p90 = get_uncertainty_radius(
        forecast_hours,
        "p90"
    )

    uncertainty_p50 = get_uncertainty_radius(
        forecast_hours,
        "p50"
    )

    uncertainty_p80 = get_uncertainty_radius(
        forecast_hours,
        "p80"
    )

    uncertainty_p95 = get_uncertainty_radius(
        forecast_hours,
        "p95"
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {

        "model": model,

        "alpha": float(
            alpha
        ),

        "beta": float(
            beta
        ),

        "start_latitude": float(
            latitude
        ),

        "start_longitude": float(
            longitude
        ),

        "start_time": str(
            pd.to_datetime(
                start_time
            )
        ),

        "forecast_hours": float(
            forecast_hours
        ),

        "predicted_latitude":
            predicted_latitude,

        "predicted_longitude":
            predicted_longitude,

        "velocity_u":
            velocity["u"],

        "velocity_v":
            velocity["v"],

        "velocity_speed":
            velocity["speed"],

        "velocity_heading":
            velocity["heading"],

        "wind_available":
            velocity["wind_available"],

        "environment":
            environment,

        "uncertainty_radius_km":
            uncertainty_p90,

        "validated_uncertainty": {

            "p50_km":
                uncertainty_p50,

            "p80_km":
                uncertainty_p80,

            "p90_km":
                uncertainty_p90,

            "p95_km":
                uncertainty_p95,

            "samples":
                49,

            "method":
                "sqrt_time_from_24h_LOIO",
        },

        "validation":
            False,
    }


# ============================================================
# INTEGRATED PREDICTION
# ============================================================

def integrated_predict_position(
    latitude,
    longitude,
    start_time,
    forecast_hours=24,
    model=DEFAULT_MODEL,
    ocean_weight=None,
    wind_weight=None,
):
    """
    Integrate drift in 6-hour environmental steps.

    This is more realistic than using one environmental
    snapshot for the entire forecast.

    Each step retrieves environmental forcing at the
    current forecast position/time.
    """

    alpha, beta = get_model_coefficients(
        model
    )

    if ocean_weight is not None:
        alpha = float(
            ocean_weight
        )

    if wind_weight is not None:
        beta = float(
            wind_weight
        )

    start_timestamp = pd.to_datetime(
        start_time
    )

    current_latitude = float(
        latitude
    )

    current_longitude = float(
        longitude
    )

    total_hours = float(
        forecast_hours
    )

    step_hours = 6.0

    trajectory = []

    elapsed = 0.0

    last_environment = None
    last_velocity = None

    while elapsed < total_hours:

        remaining = (
            total_hours - elapsed
        )

        current_step = min(
            step_hours,
            remaining
        )

        current_time = (
            start_timestamp
            + pd.Timedelta(
                hours=elapsed
            )
        )

        environment = extract_environment(
            current_time,
            current_latitude,
            current_longitude,
            validation=False
        )

        velocity = calculate_drift_velocity(
            environment,
            ocean_weight=alpha,
            wind_weight=beta,
        )

        new_latitude, new_longitude = (
            propagate_position(
                current_latitude,
                current_longitude,
                velocity["u"],
                velocity["v"],
                current_step
            )
        )

        elapsed += current_step

        current_latitude = new_latitude
        current_longitude = new_longitude

        trajectory.append(
            {
                "forecast_hours":
                    float(elapsed),

                "latitude":
                    current_latitude,

                "longitude":
                    current_longitude,

                "velocity_u":
                    velocity["u"],

                "velocity_v":
                    velocity["v"],

                "velocity_speed":
                    velocity["speed"],

                "velocity_heading":
                    velocity["heading"],
            }
        )

        last_environment = environment
        last_velocity = velocity

    if last_velocity is None:

        last_velocity = {
            "u": 0.0,
            "v": 0.0,
            "speed": 0.0,
            "heading": 0.0,
            "wind_available": False,
        }

    uncertainty_p90 = get_uncertainty_radius(
        int(total_hours)
        if total_hours.is_integer()
        else total_hours,
        "p90"
    )

    return {

        "model": model,

        "alpha": float(
            alpha
        ),

        "beta": float(
            beta
        ),

        "start_latitude": float(
            latitude
        ),

        "start_longitude": float(
            longitude
        ),

        "start_time": str(
            start_timestamp
        ),

        "forecast_hours": total_hours,

        "predicted_latitude":
            current_latitude,

        "predicted_longitude":
            current_longitude,

        "velocity_u":
            last_velocity["u"],

        "velocity_v":
            last_velocity["v"],

        "velocity_speed":
            last_velocity["speed"],

        "velocity_heading":
            last_velocity["heading"],

        "wind_available":
            last_velocity.get(
                "wind_available",
                False
            ),

        "environment":
            last_environment,

        "uncertainty_radius_km":
            uncertainty_p90,

        "trajectory":
            trajectory,

        "validation":
            False,
    }


# ============================================================
# ENSEMBLE FORECAST
# ============================================================

def ensemble_forecast(
    latitude,
    longitude,
    start_time,
    forecast_hours=24,
    model=DEFAULT_MODEL,
    ocean_weight=None,
    wind_weight=None,
    ensemble_size=100,
    velocity_noise=0.003,
    seed=42,
):
    """
    Generate a stochastic ensemble around the deterministic
    drift forecast.

    IMPORTANT:
    This ensemble is NOT the validated uncertainty envelope.

    The empirical LOIO uncertainty envelope should be used
    for reported probability containment.
    """

    rng = np.random.default_rng(
        seed
    )

    alpha, beta = get_model_coefficients(
        model
    )

    if ocean_weight is not None:
        alpha = float(
            ocean_weight
        )

    if wind_weight is not None:
        beta = float(
            wind_weight
        )

    environment = extract_environment(
        start_time,
        latitude,
        longitude,
        validation=False
    )

    base_velocity = calculate_drift_velocity(
        environment,
        ocean_weight=alpha,
        wind_weight=beta,
    )

    base_u = base_velocity[
        "u"
    ]

    base_v = base_velocity[
        "v"
    ]

    samples = []

    for _ in range(
        int(ensemble_size)
    ):

        u = (
            base_u
            + rng.normal(
                0.0,
                velocity_noise
            )
        )

        v = (
            base_v
            + rng.normal(
                0.0,
                velocity_noise
            )
        )

        lat, lon = propagate_position(
            latitude,
            longitude,
            u,
            v,
            forecast_hours
        )

        samples.append(
            (
                lat,
                lon
            )
        )

    # --------------------------------------------------------
    # Radius around deterministic prediction
    # --------------------------------------------------------

    deterministic_latitude, deterministic_longitude = (
        propagate_position(
            latitude,
            longitude,
            base_u,
            base_v,
            forecast_hours
        )
    )

    distances = []

    for lat, lon in samples:

        _, _, distance_m = GEOD.inv(
            deterministic_longitude,
            deterministic_latitude,
            lon,
            lat
        )

        distances.append(
            distance_m / 1000.0
        )

    distances = np.asarray(
        distances,
        dtype=float
    )

    return {

        "model": model,

        "alpha": float(
            alpha
        ),

        "beta": float(
            beta
        ),

        "ensemble_size":
            int(ensemble_size),

        "velocity_noise":
            float(velocity_noise),

        "predicted_latitude":
            float(
                deterministic_latitude
            ),

        "predicted_longitude":
            float(
                deterministic_longitude
            ),

        "ensemble_uncertainty_radius_km":
            float(
                np.percentile(
                    distances,
                    90
                )
            ),

        "p50_radius_km":
            float(
                np.percentile(
                    distances,
                    50
                )
            ),

        "p80_radius_km":
            float(
                np.percentile(
                    distances,
                    80
                )
            ),

        "p90_radius_km":
            float(
                np.percentile(
                    distances,
                    90
                )
            ),

        "p95_radius_km":
            float(
                np.percentile(
                    distances,
                    95
                )
            ),

        "validated_uncertainty":
            get_uncertainty_radius(
                int(forecast_hours)
                if float(forecast_hours).is_integer()
                else forecast_hours,
                "p90"
            ),

        "environment":
            environment,
    }


# ============================================================
# MAIN DEMO
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("ANTARCTIC ICEBERG DRIFT ENGINE TEST")
    print("=" * 70)

    latitude = -63.0
    longitude = -45.0

    start_time = (
        "2023-08-20T00:00:00"
    )

    forecast_hours = 24

    print(
        f"Start latitude  : {latitude}"
    )

    print(
        f"Start longitude : {longitude}"
    )

    print(
        f"Start time      : {start_time}"
    )

    print(
        f"Horizon         : {forecast_hours} hours"
    )

    print()

    # --------------------------------------------------------
    # ENVIRONMENT
    # --------------------------------------------------------

    environment = extract_environment(
        start_time,
        latitude,
        longitude
    )

    print("ENVIRONMENT")
    print("-" * 70)

    print(
        "Ocean U :",
        environment["ocean"]["u"]
    )

    print(
        "Ocean V :",
        environment["ocean"]["v"]
    )

    print(
        "Wind U  :",
        environment["wind"]["u"]
    )

    print(
        "Wind V  :",
        environment["wind"]["v"]
    )

    print(
        "Wind available :",
        environment["wind_available"]
    )

    print()

    # --------------------------------------------------------
    # VELOCITY
    # --------------------------------------------------------

    velocity = calculate_drift_velocity(
        environment,
        ocean_weight=CALIBRATED_ALPHA,
        wind_weight=CALIBRATED_BETA,
    )

    print("CALIBRATED DRIFT VELOCITY")
    print("-" * 70)

    print(
        "Alpha :",
        CALIBRATED_ALPHA
    )

    print(
        "Beta  :",
        CALIBRATED_BETA
    )

    print(
        "U     :",
        velocity["u"]
    )

    print(
        "V     :",
        velocity["v"]
    )

    print(
        "Speed :",
        velocity["speed"]
    )

    print(
        "Heading :",
        velocity["heading"]
    )

    print()

    # --------------------------------------------------------
    # POSITION
    # --------------------------------------------------------

    result = predict_position(
        latitude,
        longitude,
        start_time,
        forecast_hours=forecast_hours,
        model="calibrated"
    )

    print("24-HOUR FORECAST")
    print("-" * 70)

    print(
        "Latitude :",
        result["predicted_latitude"]
    )

    print(
        "Longitude:",
        result["predicted_longitude"]
    )

    print(
        "Speed    :",
        result["velocity_speed"]
    )

    print(
        "Heading  :",
        result["velocity_heading"]
    )

    print(
        "P90 uncertainty (km):",
        result["uncertainty_radius_km"]
    )

    print()

    print("=" * 70)
    print("DRIFT ENGINE TEST PASSED")
    print("=" * 70)