from fastapi import FastAPI
from sqlalchemy import text

from database import engine

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