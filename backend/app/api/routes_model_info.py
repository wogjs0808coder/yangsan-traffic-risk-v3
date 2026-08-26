from fastapi import APIRouter, HTTPException

from app.core.region_map import REGION_MAP
from app.models.inference import get_region_schema

router = APIRouter()


@router.get("/model-info/{region}")
def model_info(region: str):
    """프론트엔드가 지역별 입력 폼을 자동으로 구성할 수 있도록 스키마를 제공합니다."""
    region_en = REGION_MAP.get(region)
    if region_en is None:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 지역입니다: {region}. 지원 지역: {list(REGION_MAP.keys())}",
        )

    try:
        schema = get_region_schema(region_en)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"{region} 모델 아티팩트를 찾을 수 없습니다.",
        )

    return schema
