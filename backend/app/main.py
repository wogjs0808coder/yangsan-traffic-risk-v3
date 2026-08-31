from fastapi import FastAPI

from app.api.routes_accidents import router as accidents_router
from app.api.routes_health import router as health_router
from app.api.routes_history import router as history_router
from app.api.routes_model_info import router as model_info_router
from app.api.routes_predict import router as predict_router
from app.api.routes_regions import router as regions_router
from app.api.routes_weather import router as weather_router

app = FastAPI(title="Yangsan Traffic Risk API", version="0.1.0")

app.include_router(health_router)
app.include_router(regions_router)
app.include_router(predict_router)
app.include_router(model_info_router)
app.include_router(weather_router)
app.include_router(history_router)
app.include_router(accidents_router)


@app.get("/")
def root():
    return {"message": "Yangsan Traffic Risk API v3"}
