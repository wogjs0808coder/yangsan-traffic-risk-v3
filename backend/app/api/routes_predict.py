from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.region_map import REGION_MAP
from app.db.models import PredictionLog
from app.db.session import get_db
from app.models.inference import predict
from app.schemas.predict_schema import PredictRequest, PredictResponse

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
def predict_accident_type(payload: PredictRequest, db: Session = Depends(get_db)):
    region_en = REGION_MAP.get(payload.region)
    if region_en is None:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 지역입니다: {payload.region}. 지원 지역: {list(REGION_MAP.keys())}",
        )

    try:
        predicted_type, confidence = predict(
            region_en, payload.weather_features, payload.user_inputs
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"{payload.region} 모델 아티팩트를 찾을 수 없습니다. migrate_v2_models.py 실행 여부를 확인하세요.",
        )

    log = PredictionLog(
        region=payload.region,
        request_payload={
            "weather_features": payload.weather_features,
            "user_inputs": payload.user_inputs,
        },
        predicted_type=predicted_type,
        confidence=confidence,
    )
    db.add(log)
    db.commit()

    return PredictResponse(
        region=payload.region,
        predicted_type=predicted_type,
        confidence=confidence,
    )
