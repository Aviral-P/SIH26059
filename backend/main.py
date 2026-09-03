from fastapi import FastAPI

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