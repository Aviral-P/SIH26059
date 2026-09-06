from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import engine, get_db

from backend.app.drift_service import generate_forecast
from backend.app.sea_ice_service import get_sea_ice
from backend.app.mission_service import plan_mission
from backend.app.mission_intelligence import generate_mission_intelligence


app = FastAPI(
    title="Antarctic Navigation Intelligence System",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ForecastRequest(BaseModel):
    iceberg_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    forecast_hours: int = 24
    validation: bool = False


class MissionPoint(BaseModel):
    latitude: float
    longitude: float


class MissionPlanRequest(BaseModel):
    start: MissionPoint
    destination: MissionPoint
    departure_time: Optional[datetime] = None
    vessel_speed_knots: float = 10.0
    iceberg_date: Optional[str] = None
    icebergs: List[dict] = []
    profile: str = "balanced"


class MissionIntelligenceRequest(BaseModel):
    mission_data: dict


@app.get("/")
def root():
    return {
        "system": "Antarctic Navigation Intelligence System",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/health/database")
def database_health():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar()

    return {
        "database": "connected",
        "test": value,
    }


@app.post("/api/v1/forecast")
def create_forecast(
    request: ForecastRequest,
    db: Session = Depends(get_db),
):
    return generate_forecast(
        db=db,
        iceberg_id=request.iceberg_id,
        latitude=request.latitude,
        longitude=request.longitude,
        timestamp=request.timestamp,
        forecast_hours=request.forecast_hours,
        validation=request.validation,
    )


@app.post("/api/v1/mission/plan")
def create_mission_plan(request: MissionPlanRequest):

    # --------------------------------------------------------
    # Determine the date used for sea-ice data
    # --------------------------------------------------------

    if request.iceberg_date:
        iceberg_date = request.iceberg_date

    elif request.departure_time:
        iceberg_date = request.departure_time.strftime("%Y%m%d")

    else:
        iceberg_date = datetime.utcnow().strftime("%Y%m%d")


    # --------------------------------------------------------
    # Build a small spatial buffer around the mission corridor
    # --------------------------------------------------------

    min_lat = (
        min(
            request.start.latitude,
            request.destination.latitude,
        )
        - 2.0
    )

    max_lat = (
        max(
            request.start.latitude,
            request.destination.latitude,
        )
        + 2.0
    )

    min_lon = (
        min(
            request.start.longitude,
            request.destination.longitude,
        )
        - 2.0
    )

    max_lon = (
        max(
            request.start.longitude,
            request.destination.longitude,
        )
        + 2.0
    )


    # --------------------------------------------------------
    # Load sea-ice information
    # --------------------------------------------------------

    sea_ice = get_sea_ice(
        date=iceberg_date,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
    )


    # --------------------------------------------------------
    # Convert Pydantic points to dictionaries expected by
    # mission_service.py
    # --------------------------------------------------------

    start = {
        "latitude": request.start.latitude,
        "longitude": request.start.longitude,
    }

    destination = {
        "latitude": request.destination.latitude,
        "longitude": request.destination.longitude,
    }


    # --------------------------------------------------------
    # Generate mission routes
    # --------------------------------------------------------

    return plan_mission(
        start=start,
        destination=destination,
        vessel_speed_knots=request.vessel_speed_knots,
        sea_ice_data=sea_ice,
        iceberg_data=request.icebergs,
        profile=request.profile,
    )


@app.post("/api/v1/mission/intelligence")
def mission_intelligence(
    request: MissionIntelligenceRequest,
):
    return generate_mission_intelligence(
        mission_data=request.mission_data,
    )


@app.get("/api/v1/sea-ice")
def sea_ice(
    date: str = "20230721",
    min_lat: float = -67.0,
    max_lat: float = -60.0,
    min_lon: float = -50.0,
    max_lon: float = -44.0,
):
    return {
        "date": date,
        "cells": get_sea_ice(
            date=date,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        ),
    }


@app.get("/api/v1/icebergs")
def get_icebergs(
    date: str = "20230721",
    min_lat: float = -75.0,
    max_lat: float = -55.0,
    min_lon: float = -180.0,
    max_lon: float = 180.0,
    db: Session = Depends(get_db),
):
    query = text(
        """
        SELECT
            iceberg_id,
            observed_at,
            latitude,
            longitude,
            displacement_km,
            velocity_kmh,
            velocity_angle_deg
        FROM iceberg_trajectories
        WHERE observed_at::date = TO_DATE(:date, 'YYYYMMDD')
          AND latitude BETWEEN :min_lat AND :max_lat
          AND longitude BETWEEN :min_lon AND :max_lon
        ORDER BY iceberg_id, observed_at
        """
    )

    rows = db.execute(
        query,
        {
            "date": date,
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
        },
    ).mappings().all()

    return {
        "date": date,
        "count": len(rows),
        "icebergs": [dict(row) for row in rows],
    }