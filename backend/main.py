from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from database import engine, get_db
from app.drift_service import generate_forecast
from typing import List

from app.mission_service import plan_mission



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

    icebergs: List[dict] = []
    sea_ice: List[dict] = []


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
    return plan_mission(
        start_lat=request.start.latitude,
        start_lon=request.start.longitude,
        destination_lat=request.destination.latitude,
        destination_lon=request.destination.longitude,
        icebergs=request.icebergs,
        sea_ice=request.sea_ice,
        vessel_speed_knots=request.vessel_speed_knots,
    )