from fastapi import APIRouter, HTTPException

from app.core.region_map import REGION_MAP
from app.models.inference import get_region_schema
from app.services.weather_service import get_current_weather, map_weather_to_features

router = APIRouter()


@router.get("/weather/{region}")
def weather(region: str):
    """
    실시간 기상 데이터와, 해당 지역 모델이 바로 쓸 수 있는 형태로 매핑된
    model_features를 함께 반환합니다. 프론트엔드는 이 값을 입력 폼 기본값으로 채웁니다.
    """
    region_en = REGION_MAP.get(region)
    if region_en is None:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 지역입니다: {region}. 지원 지역: {list(REGION_MAP.keys())}",
        )

    weather_data = get_current_weather(region_en)

    try:
        schema = get_region_schema(region_en)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"{region} 모델 아티팩트를 찾을 수 없습니다.")

    model_features = map_weather_to_features(weather_data, schema["numeric_features"])

    return {
        "weather": weather_data,
        "model_features": model_features,
    }
