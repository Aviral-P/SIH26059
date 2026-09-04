from fastapi import FastAPI, Depends
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from database import engine, get_db
from app.drift_service import generate_forecast

app = FastAPI(
    title="Antarctic Navigation Intelligence System",
    version="0.1.0"
)


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
    
class ForecastRequest(BaseModel):
    iceberg_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    forecast_hours: int = 24
    validation: bool = False


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