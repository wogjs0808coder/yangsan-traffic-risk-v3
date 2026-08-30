from datetime import date, datetime

from pydantic import BaseModel


class PredictionLogItem(BaseModel):
    id: int
    region: str
    predicted_type: str | None
    confidence: float | None
    requested_at: datetime

    class Config:
        from_attributes = True


class PredictionHistoryResponse(BaseModel):
    items: list[PredictionLogItem]
    total: int
    page: int
    page_size: int


class RegionCount(BaseModel):
    region: str
    count: int


class TypeCount(BaseModel):
    predicted_type: str
    count: int


class DailyCount(BaseModel):
    day: date
    count: int


class PredictionStatsResponse(BaseModel):
    total_predictions: int
    avg_confidence: float | None
    by_region: list[RegionCount]
    by_type: list[TypeCount]
    daily_counts: list[DailyCount]
