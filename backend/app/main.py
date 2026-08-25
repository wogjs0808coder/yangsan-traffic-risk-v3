from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.api.routes_regions import router as regions_router

app = FastAPI(title="Yangsan Traffic Risk API", version="0.1.0")

app.include_router(health_router)
app.include_router(regions_router)


@app.get("/")
def root():
    return {"message": "Yangsan Traffic Risk API v3"}
