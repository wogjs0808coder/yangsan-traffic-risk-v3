from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.region_schema import RegionResponse

router = APIRouter()

# DB에 데이터가 없는 초기 상태를 대비한 fallback (accidents 테이블이 비어있을 경우)
FALLBACK_REGIONS = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "대전광역시",
    "경상남도 양산시",
]


@router.get("/regions", response_model=RegionResponse)
def get_regions(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT DISTINCT region FROM accidents ORDER BY region"))
    regions = [row[0] for row in result]

    if not regions:
        return RegionResponse(regions=FALLBACK_REGIONS)

    return RegionResponse(regions=regions)
