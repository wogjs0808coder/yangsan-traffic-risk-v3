from fastapi import APIRouter

from app.schemas.region_schema import RegionResponse

router = APIRouter()

# TODO: ml/data/real/ 실제 데이터 적재 후에는
# accidents 테이블에서 SELECT DISTINCT region 으로 대체
SUPPORTED_REGIONS = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "대전광역시",
    "경상남도 양산시",
]


@router.get("/regions", response_model=RegionResponse)
def get_regions():
    return RegionResponse(regions=SUPPORTED_REGIONS)
