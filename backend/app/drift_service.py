from datetime import datetime, timedelta
from pathlib import Path
import math
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from scripts.drift_engine import (
    integrated_predict_position,
    ensemble_forecast,
)


MODEL_NAME = "physics-informed-drift-v2"


def _clean_value(value):
    """
    Convert values into JSON-safe values.

    NaN and +/-inf are converted to None because
    JSON does not support them.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    if hasattr(value, "item"):
        try:
            return _clean_value(value.item())
        except Exception:
            pass

    if isinstance(value, dict):
        return {
            str(key): _clean_value(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _clean_value(item)
            for item in value
        ]

    return value


def save_forecast(
    db: Session,
    iceberg_id: str,
    forecast_time: datetime,
    latitude: float,
    longitude: float,
    predicted_speed_kmh: float,
    predicted_heading_deg: float,
    uncertainty_radius_km: float,
):
    """
    Save forecast to PostgreSQL/PostGIS.
    """

    query = text(
        """
        INSERT INTO iceberg_drift_forecasts (
            iceberg_id,
            forecast_time,
            latitude,
            longitude,
            predicted_speed_kmh,
            predicted_heading_deg,
            uncertainty_radius_km,
            model_name,
            geometry
        )
        VALUES (
            :iceberg_id,
            :forecast_time,
            :latitude,
            :longitude,
            :speed,
            :heading,
            :uncertainty,
            :model_name,
            ST_SetSRID(
                ST_MakePoint(:longitude, :latitude),
                4326
            )
        )
        RETURNING id
        """
    )

    result = db.execute(
        query,
        {
            "iceberg_id": iceberg_id,
            "forecast_time": forecast_time,
            "latitude": _clean_value(latitude),
            "longitude": _clean_value(longitude),
            "speed": _clean_value(predicted_speed_kmh),
            "heading": _clean_value(predicted_heading_deg),
            "uncertainty": _clean_value(uncertainty_radius_km),
            "model_name": MODEL_NAME,
        },
    )

    db.commit()

    return result.scalar_one()


def _serialize_environment(environment):
    """
    Convert environmental data into a compact JSON-safe structure.
    """

    if not environment:
        return None

    ocean = (
        environment.get("ocean_current")
        or environment.get("ocean")
        or {}
    )

    wind = environment.get("wind") or {}
    sea_ice = environment.get("sea_ice") or {}

    concentration = sea_ice.get("concentration")

    if concentration is not None:
        try:
            sea_ice_percent = float(concentration) * 100.0
        except Exception:
            sea_ice_percent = None
    else:
        sea_ice_percent = None

    return {
        "timestamp": _clean_value(
            environment.get("timestamp")
        ),
        "latitude": _clean_value(
            environment.get("latitude")
        ),
        "longitude": _clean_value(
            environment.get("longitude")
        ),
        "sea_ice_percent": _clean_value(
            sea_ice_percent
        ),
        "wind_mps": _clean_value(
            wind.get("speed")
        ),
        "current_mps": _clean_value(
            ocean.get("speed")
        ),
        "sea_ice_available": bool(
            sea_ice.get("available")
        ),
        "wind_available": bool(
            wind.get("available")
        ),
        "current_available": bool(
            ocean.get("available")
        ),
        "wind_time_difference_hours": _clean_value(
            wind.get("time_difference_hours")
        ),
        "current_time_difference_hours": _clean_value(
            ocean.get("time_difference_hours")
        ),
        "wind_data_gap_warning": bool(
            wind.get("data_gap_warning", False)
        ),
        "current_data_gap_warning": bool(
            ocean.get("data_gap_warning", False)
        ),
    }


def generate_forecast(
    db: Session,
    iceberg_id: str,
    latitude: float,
    longitude: float,
    timestamp: datetime,
    forecast_hours: int = 24,
    validation: bool = False,
):
    """
    Main drift intelligence service.

    Uses the existing calibrated drift engine.

    The validation parameter is retained at the API layer for
    compatibility, but is not passed into the current drift engine
    because the engine does not accept it.
    """

    if forecast_hours <= 0:
        raise ValueError(
            "forecast_hours must be greater than 0"
        )

    if forecast_hours > 168:
        raise ValueError(
            "forecast_hours cannot exceed 168 hours"
        )

    # ---------------------------------------------------------
    # 1. DETERMINISTIC FORECAST
    # ---------------------------------------------------------

    deterministic = integrated_predict_position(
        latitude=latitude,
        longitude=longitude,
        start_time=timestamp,
        forecast_hours=forecast_hours,
        model="calibrated",
    )

    predicted_lat = deterministic.get(
        "predicted_latitude"
    )

    predicted_lon = deterministic.get(
        "predicted_longitude"
    )

    # ---------------------------------------------------------
    # 2. ENSEMBLE FORECAST
    # ---------------------------------------------------------

    ensemble = ensemble_forecast(
        latitude=latitude,
        longitude=longitude,
        start_time=timestamp,
        forecast_hours=forecast_hours,
        model="calibrated",
        ensemble_size=100,
        velocity_noise=0.003,
        seed=42,
    )

    center_lat = ensemble.get(
        "predicted_latitude"
    )

    center_lon = ensemble.get(
        "predicted_longitude"
    )

    ensemble_radius_km = ensemble.get(
        "ensemble_uncertainty_radius_km"
    )

    # ---------------------------------------------------------
    # 3. VALIDATED UNCERTAINTY
    # ---------------------------------------------------------

    uncertainty_km = deterministic.get(
        "uncertainty_radius_km"
    )

    if uncertainty_km is None:
        uncertainty_km = ensemble_radius_km

    # ---------------------------------------------------------
    # 4. VELOCITY
    # ---------------------------------------------------------

    u = deterministic.get("velocity_u")
    v = deterministic.get("velocity_v")

    speed_mps = None
    speed_kmh = None
    heading = None

    if u is not None and v is not None:
        try:
            u = float(u)
            v = float(v)

            if math.isfinite(u) and math.isfinite(v):

                speed_mps = math.sqrt(
                    (u * u) + (v * v)
                )

                speed_kmh = speed_mps * 3.6

                heading = (
                    math.degrees(
                        math.atan2(u, v)
                    )
                    + 360
                ) % 360

        except (TypeError, ValueError):
            speed_mps = None
            speed_kmh = None
            heading = None

    # ---------------------------------------------------------
    # 5. SAVE FORECAST
    # ---------------------------------------------------------

    forecast_time = (
        timestamp
        + timedelta(hours=forecast_hours)
    )

    forecast_id = save_forecast(
        db=db,
        iceberg_id=iceberg_id,
        forecast_time=forecast_time,
        latitude=predicted_lat,
        longitude=predicted_lon,
        predicted_speed_kmh=speed_kmh,
        predicted_heading_deg=heading,
        uncertainty_radius_km=uncertainty_km,
    )

    # ---------------------------------------------------------
    # 6. TRAJECTORY
    # ---------------------------------------------------------

    trajectory = []

    for step in deterministic.get(
        "trajectory",
        []
    ):
        trajectory.append(
            {
                "hours": _clean_value(
                    step.get("forecast_hours")
                ),
                "latitude": _clean_value(
                    step.get("latitude")
                ),
                "longitude": _clean_value(
                    step.get("longitude")
                ),
                "velocity_u_mps": _clean_value(
                    step.get("velocity_u")
                ),
                "velocity_v_mps": _clean_value(
                    step.get("velocity_v")
                ),
                "speed_mps": _clean_value(
                    step.get("velocity_speed")
                ),
                "heading_deg": _clean_value(
                    step.get("velocity_heading")
                ),
            }
        )

    # ---------------------------------------------------------
    # 7. ENVIRONMENT
    # ---------------------------------------------------------

    environment = _serialize_environment(
        deterministic.get("environment")
    )

    ensemble_environment = _serialize_environment(
        ensemble.get("environment")
    )

    # ---------------------------------------------------------
    # 8. RESPONSE
    # ---------------------------------------------------------

    response = {
        "forecast_id": forecast_id,
        "iceberg_id": iceberg_id,
        "model": MODEL_NAME,

        "initial_position": {
            "latitude": _clean_value(latitude),
            "longitude": _clean_value(longitude),
            "timestamp": timestamp.isoformat(),
        },

        "forecast": {
            "hours": forecast_hours,
            "latitude": _clean_value(
                predicted_lat
            ),
            "longitude": _clean_value(
                predicted_lon
            ),
            "speed_kmh": _clean_value(
                speed_kmh
            ),
            "heading_deg": _clean_value(
                heading
            ),
        },

        "ensemble": {
            "members": ensemble.get(
                "ensemble_size"
            ),
            "center_latitude": _clean_value(
                center_lat
            ),
            "center_longitude": _clean_value(
                center_lon
            ),
            "stochastic_uncertainty_radius_km": _clean_value(
                ensemble_radius_km
            ),
        },

        "validated_uncertainty": {
            "p90_radius_km": _clean_value(
                uncertainty_km
            ),
            "method": (
                "LOIO empirical envelope"
            ),
        },

        "base_velocity": {
            "u_mps": _clean_value(u),
            "v_mps": _clean_value(v),
            "speed_mps": _clean_value(
                speed_mps
            ),
        },

        "environment": environment,

        "ensemble_environment": ensemble_environment,

        "integration": {
            "step_hours": 6,
            "steps": len(trajectory),
        },

        "trajectory": trajectory,

        "validation": bool(validation),
    }

    return _clean_value(response)