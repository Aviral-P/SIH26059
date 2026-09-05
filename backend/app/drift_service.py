from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

# Project root
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from scripts.drift_engine import (
    integrated_predict_position,
    ensemble_forecast,
)

MODEL_NAME = "physics-informed-drift-v2"


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
    Save deterministic forecast to PostgreSQL/PostGIS.
    """

    query = text("""
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
    """)

    result = db.execute(
        query,
        {
            "iceberg_id": iceberg_id,
            "forecast_time": forecast_time,
            "latitude": latitude,
            "longitude": longitude,
            "speed": predicted_speed_kmh,
            "heading": predicted_heading_deg,
            "uncertainty": uncertainty_radius_km,
            "model_name": MODEL_NAME,
        },
    )

    db.commit()

    return result.scalar_one()


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

    1. Run integrated deterministic forecast.
    2. Run ensemble uncertainty forecast.
    3. Calculate speed + heading.
    4. Persist forecast.
    5. Return API-ready result.
    """

    # --------------------------------------------------------
    # Deterministic forecast
    # --------------------------------------------------------

    deterministic = integrated_predict_position(
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        forecast_hours=forecast_hours,
        step_hours=6,
        validation=validation,
    )

    predicted_lat = deterministic["predicted_latitude"]

    predicted_lon = deterministic["predicted_longitude"]

    # --------------------------------------------------------
    # Ensemble
    # --------------------------------------------------------

    ensemble = ensemble_forecast(
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        forecast_hours=forecast_hours,
        ensemble_size=100,
        validation=validation,
    )

    center_lat = ensemble["center_latitude"]

    center_lon = ensemble["center_longitude"]

    uncertainty_km = ensemble["uncertainty_radius_m"] / 1000.0

    base_velocity = ensemble["base_velocity"]

    u = base_velocity["u"]
    v = base_velocity["v"]

    # --------------------------------------------------------
    # Speed
    # --------------------------------------------------------

    speed_mps = (u * u + v * v) ** 0.5

    speed_kmh = speed_mps * 3.6

    # --------------------------------------------------------
    # Heading
    # --------------------------------------------------------

    import math

    heading = (math.degrees(math.atan2(u, v)) + 360) % 360

    # --------------------------------------------------------
    # Forecast timestamp
    # --------------------------------------------------------

    forecast_time = timestamp + __import__("datetime").timedelta(hours=forecast_hours)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # API response
    # --------------------------------------------------------

    return {
        "forecast_id": forecast_id,
        "iceberg_id": iceberg_id,
        "model": MODEL_NAME,
        "initial_position": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "forecast": {
            "hours": forecast_hours,
            "latitude": predicted_lat,
            "longitude": predicted_lon,
            "speed_kmh": speed_kmh,
            "heading_deg": heading,
        },
        "ensemble": {
            "members": ensemble["ensemble_size"],
            "center_latitude": center_lat,
            "center_longitude": center_lon,
            "uncertainty_radius_km": uncertainty_km,
        },
        "base_velocity": {
            "u_mps": u,
            "v_mps": v,
        },
        "integration": {
            "step_hours": deterministic["step_hours"],
            "steps": len(deterministic["steps"]),
        },
        "trajectory": [
            {
                "hours": (index + 1) * step["step_hours"],
                "latitude": step["end_latitude"],
                "longitude": step["end_longitude"],
            }
            for index, step in enumerate(deterministic["steps"])
        ],
    }
