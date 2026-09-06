from pathlib import Path
import sys
import math

import numpy as np
import pandas as pd
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

# Import our environmental extractor
sys.path.append(str(ROOT))

from scripts.extract_environment import extract_environment


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# These are BASELINE parameters.
# They are deliberately configurable and should NOT be
# presented as learned/scientifically calibrated values.

OCEAN_WEIGHT = 0.85
WIND_WEIGHT = 0.015

EARTH = Geod(ellps="WGS84")


# ---------------------------------------------------------
# Vector utilities
# ---------------------------------------------------------

def vector_speed(u, v):
    return math.sqrt(u * u + v * v)


def calculate_drift_velocity(environment):
    """
    Physics-informed baseline.

    V_ice = alpha * V_ocean + beta * V_wind

    Ocean current is the dominant driver.
    Wind contribution is represented separately.

    Returns velocity in m/s.
    """

    ocean = environment["ocean_current"]
    wind = environment["wind"]

    if not ocean["available"]:
        raise RuntimeError(
            "Ocean current unavailable. "
            "Cannot calculate drift."
        )

    if not wind["available"]:
        raise RuntimeError(
            "Wind unavailable. "
            "Cannot calculate drift."
        )

    u = (
        OCEAN_WEIGHT * ocean["u"]
        +
        WIND_WEIGHT * wind["u"]
    )

    v = (
        OCEAN_WEIGHT * ocean["v"]
        +
        WIND_WEIGHT * wind["v"]
    )

    return {
        "u": u,
        "v": v,
        "speed": vector_speed(u, v)
    }


# ---------------------------------------------------------
# Position propagation
# ---------------------------------------------------------

def propagate_position(
    latitude,
    longitude,
    u,
    v,
    duration_hours
):
    """
    Move an iceberg using an east/north velocity vector.

    u = eastward velocity [m/s]
    v = northward velocity [m/s]
    """

    duration_seconds = duration_hours * 3600

    east_distance = u * duration_seconds
    north_distance = v * duration_seconds

    distance = math.sqrt(
        east_distance ** 2 +
        north_distance ** 2
    )

    # Bearing:
    # atan2(East, North)
    bearing = math.degrees(
        math.atan2(
            east_distance,
            north_distance
        )
    )

    bearing = bearing % 360

    new_lon, new_lat, _ = EARTH.fwd(
        longitude,
        latitude,
        bearing,
        distance
    )

    return new_lat, new_lon


# ---------------------------------------------------------
# Single deterministic forecast
# ---------------------------------------------------------

def predict_position(
    latitude,
    longitude,
    timestamp,
    forecast_hours=24,
    validation=False
):
    """
    Generate a deterministic iceberg drift forecast.

    validation=False
        Uses production environmental datasets.

    validation=True
        Uses historical validation datasets.
    """

    environment = extract_environment(
        timestamp,
        latitude,
        longitude,
        validation=validation
    )

    velocity = calculate_drift_velocity(
        environment
    )

    predicted_lat, predicted_lon = propagate_position(
        latitude,
        longitude,
        velocity["u"],
        velocity["v"],
        forecast_hours
    )

    return {
        "initial_latitude": latitude,
        "initial_longitude": longitude,

        "forecast_hours": forecast_hours,

        "predicted_latitude": predicted_lat,
        "predicted_longitude": predicted_lon,

        "velocity_u": velocity["u"],
        "velocity_v": velocity["v"],
        "velocity_speed": velocity["speed"],

        "environment": environment
    }


# ---------------------------------------------------------
# Time-integrated deterministic forecast
# ---------------------------------------------------------

def integrated_predict_position(
    latitude,
    longitude,
    timestamp,
    forecast_hours=24,
    step_hours=6,
    validation=False
):
    """
    Time-integrated physics-informed iceberg forecast.

    Instead of assuming that environmental forcing remains
    constant for the entire forecast horizon, the model
    repeatedly samples the environmental fields and updates
    the iceberg velocity.

    Historical validation:
        step_hours=6

    This matches the temporal resolution of the historical
    ERA5 validation dataset.

    Example for a 24-hour forecast:

        t+00h -> environment -> move 6h
        t+06h -> environment -> move 6h
        t+12h -> environment -> move 6h
        t+18h -> environment -> move 6h
        t+24h -> final position
    """

    if forecast_hours <= 0:
        raise ValueError(
            "forecast_hours must be greater than zero."
        )

    if step_hours <= 0:
        raise ValueError(
            "step_hours must be greater than zero."
        )

    if step_hours > forecast_hours:
        step_hours = forecast_hours

    current_lat = latitude
    current_lon = longitude
    current_time = pd.Timestamp(timestamp)

    steps = []

    elapsed_hours = 0

    # Cache the environment at the current forecast state.
    # This avoids extracting the same dataset point twice:
    # the endpoint environment of one step becomes the forcing
    # environment for the next step.
    environment = extract_environment(
        current_time,
        current_lat,
        current_lon,
        validation=validation
    )

    while elapsed_hours < forecast_hours:

        current_step_hours = min(
            step_hours,
            forecast_hours - elapsed_hours
        )

        print(
            f"\nIntegrated step "
            f"{elapsed_hours:02d}h -> "
            f"{elapsed_hours + current_step_hours:02d}h"
        )

        forcing_environment = environment

        velocity = calculate_drift_velocity(
            forcing_environment
        )

        next_lat, next_lon = propagate_position(
            current_lat,
            current_lon,
            velocity["u"],
            velocity["v"],
            current_step_hours
        )

        next_time = (
            current_time
            + pd.Timedelta(hours=current_step_hours)
        )

        # Extract the actual environmental state at the forecast
        # endpoint. This is what the UI should display for T+6/T+12/T+24.
        endpoint_environment = extract_environment(
            next_time,
            next_lat,
            next_lon,
            validation=validation
        )

        steps.append({
            "step_start": current_time.isoformat(),
            "step_hours": current_step_hours,

            "start_latitude": current_lat,
            "start_longitude": current_lon,

            "end_latitude": next_lat,
            "end_longitude": next_lon,

            "velocity_u": velocity["u"],
            "velocity_v": velocity["v"],
            "velocity_speed": velocity["speed"],

            # Environment that drove this movement.
            "environment": forcing_environment,

            # Environment actually present at this forecast point.
            "endpoint_environment": endpoint_environment
        })

        current_lat = next_lat
        current_lon = next_lon
        current_time = next_time
        environment = endpoint_environment

        elapsed_hours += current_step_hours

    return {
        "initial_latitude": latitude,
        "initial_longitude": longitude,

        "initial_timestamp": pd.Timestamp(
            timestamp
        ).isoformat(),

        "forecast_hours": forecast_hours,
        "step_hours": step_hours,

        "predicted_latitude": current_lat,
        "predicted_longitude": current_lon,

        "steps": steps
    }


# ---------------------------------------------------------
# Ensemble forecast
# ---------------------------------------------------------

def ensemble_forecast(
    latitude,
    longitude,
    timestamp,
    forecast_hours=24,
    ensemble_size=100,
    velocity_noise=0.003,
    validation=False
):
    """
    Generate an ensemble of possible iceberg trajectories.

    The stochastic component represents unresolved
    processes / uncertainty.

    velocity_noise is expressed in m/s.
    """

    environment = extract_environment(
        timestamp,
        latitude,
        longitude,
        validation=validation
    )

    base_velocity = calculate_drift_velocity(
        environment
    )

    rng = np.random.default_rng(42)

    trajectories = []

    for i in range(ensemble_size):

        noise_u = rng.normal(
            0,
            velocity_noise
        )

        noise_v = rng.normal(
            0,
            velocity_noise
        )

        u = base_velocity["u"] + noise_u
        v = base_velocity["v"] + noise_v

        pred_lat, pred_lon = propagate_position(
            latitude,
            longitude,
            u,
            v,
            forecast_hours
        )

        trajectories.append({
            "member": i,
            "latitude": pred_lat,
            "longitude": pred_lon,
            "u": u,
            "v": v
        })

    df = pd.DataFrame(trajectories)

    center_lat = df["latitude"].median()
    center_lon = df["longitude"].median()

    # Approximate uncertainty radius using
    # great-circle distance from ensemble median.

    distances = []

    for _, row in df.iterrows():

        _, _, distance = EARTH.inv(
            center_lon,
            center_lat,
            row["longitude"],
            row["latitude"]
        )

        distances.append(distance)

    df["distance_from_center_m"] = distances

    uncertainty_radius_m = float(
        np.percentile(
            distances,
            90
        )
    )

    return {
        "center_latitude": center_lat,
        "center_longitude": center_lon,

        "ensemble_size": ensemble_size,

        "uncertainty_radius_m": uncertainty_radius_m,

        "members": df.to_dict(
            orient="records"
        ),

        "environment": environment,

        "base_velocity": base_velocity
    }


# ---------------------------------------------------------
# Demo
# ---------------------------------------------------------

if __name__ == "__main__":

    timestamp = pd.Timestamp(
        "2023-10-01T12:00:00"
    )

    latitude = -65.0
    longitude = 40.0

    print()
    print("=" * 70)
    print("ANTARCTIC ICEBERG DRIFT ENGINE")
    print("=" * 70)

    # -----------------------------------------------------
    # V1: Snapshot forecast
    # -----------------------------------------------------

    result = predict_position(
        latitude,
        longitude,
        timestamp,
        forecast_hours=24
    )

    print()
    print("DETERMINISTIC FORECAST — V1 SNAPSHOT")
    print("-" * 70)

    print(
        f"Initial position : "
        f"{result['initial_latitude']:.5f}, "
        f"{result['initial_longitude']:.5f}"
    )

    print(
        f"Forecast horizon : "
        f"{result['forecast_hours']} hours"
    )

    print(
        f"Predicted position: "
        f"{result['predicted_latitude']:.5f}, "
        f"{result['predicted_longitude']:.5f}"
    )

    print(
        f"Drift velocity    : "
        f"{result['velocity_speed']:.5f} m/s"
    )

    # -----------------------------------------------------
    # Ensemble
    # -----------------------------------------------------

    print()
    print("ENSEMBLE FORECAST")
    print("-" * 70)

    ensemble = ensemble_forecast(
        latitude,
        longitude,
        timestamp,
        forecast_hours=24,
        ensemble_size=100
    )

    print(
        f"Ensemble members   : "
        f"{ensemble['ensemble_size']}"
    )

    print(
        f"Median position    : "
        f"{ensemble['center_latitude']:.5f}, "
        f"{ensemble['center_longitude']:.5f}"
    )

    print(
        f"90% uncertainty radius: "
        f"{ensemble['uncertainty_radius_m'] / 1000:.3f} km"
    )

    print()
    print("BASELINE VELOCITY")
    print("-" * 70)

    print(
        f"U (east) : "
        f"{ensemble['base_velocity']['u']:.6f} m/s"
    )

    print(
        f"V (north): "
        f"{ensemble['base_velocity']['v']:.6f} m/s"
    )

    print()
    print("=" * 70)