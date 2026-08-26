from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    region: str = Field(..., examples=["경상남도 양산시"])
    weather_features: dict[str, float] = Field(
        default_factory=dict,
        description="기온, 강수량 등 수치형 기상 피처. 학습 컬럼명과 일치해야 반영됩니다.",
    )
    user_inputs: dict[str, str] = Field(
        default_factory=dict,
        description="차종, 연령대 등 사용자 선택값. 예: {'가해운전자 차종': '이륜차'}",
    )


class PredictResponse(BaseModel):
    region: str
    predicted_type: str
    confidence: float
