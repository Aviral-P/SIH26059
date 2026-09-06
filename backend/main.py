from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from database import engine, get_db
from app.drift_service import generate_forecast
from typing import List
from app.sea_ice_service import get_sea_ice

from app.mission_service import plan_mission
from app.mission_intelligence import generate_mission_intelligence



app = FastAPI(
    title="Antarctic Navigation Intelligence System",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
    vessel_speed_knots: float = 10.0
    iceberg_date: str = "20230721"
    icebergs: List[dict] = []

class MissionIntelligenceRequest(BaseModel):
    mission_data: dict


@app.get("/")
def root():
    return {
        "system": "Antarctic Navigation Intelligence System",
        "status": "online"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/health/database")
def database_health():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar()

    return {
        "database": "connected",
        "test": value
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
def create_mission_plan(
    request: MissionPlanRequest,
):
    sea_ice = get_sea_ice(
        date=request.iceberg_date,
        min_lat=min(
            request.start.latitude,
            request.destination.latitude,
        ) - 2.0,
        max_lat=max(
            request.start.latitude,
            request.destination.latitude,
        ) + 2.0,
        min_lon=min(
            request.start.longitude,
            request.destination.longitude,
        ) - 2.0,
        max_lon=max(
            request.start.longitude,
            request.destination.longitude,
        ) + 2.0,
    )

    return plan_mission(
        start_lat=request.start.latitude,
        start_lon=request.start.longitude,
        destination_lat=request.destination.latitude,
        destination_lon=request.destination.longitude,
        icebergs=request.icebergs,
        sea_ice=sea_ice,
        vessel_speed_knots=request.vessel_speed_knots,
    )
    
    
@app.post("/api/v1/mission/intelligence")
def mission_intelligence(
    request: MissionIntelligenceRequest,
):
    return generate_mission_intelligence(
        mission_data=request.mission_data
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
    query = text("""
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
    """)

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