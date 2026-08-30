from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import PredictionLog
from app.db.session import get_db
from app.schemas.history_schema import (
    DailyCount,
    PredictionHistoryResponse,
    PredictionLogItem,
    PredictionStatsResponse,
    RegionCount,
    TypeCount,
)

router = APIRouter()


def apply_filters(query, region: str | None, date_from: date | None, date_to: date | None):
    if region:
        query = query.filter(PredictionLog.region == region)
    if date_from:
        query = query.filter(func.date(PredictionLog.requested_at) >= date_from)
    if date_to:
        query = query.filter(func.date(PredictionLog.requested_at) <= date_to)
    return query


@router.get("/history", response_model=PredictionHistoryResponse)
def get_history(
    region: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = apply_filters(db.query(PredictionLog), region, date_from, date_to)
    total = query.count()

    items = (
        query.order_by(PredictionLog.requested_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PredictionHistoryResponse(
        items=[PredictionLogItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/history/stats", response_model=PredictionStatsResponse)
def get_history_stats(
    region: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    base_query = apply_filters(db.query(PredictionLog), region, date_from, date_to)

    total_predictions = base_query.count()
    avg_confidence = base_query.with_entities(func.avg(PredictionLog.confidence)).scalar()

    by_region_rows = (
        apply_filters(db.query(PredictionLog.region, func.count(PredictionLog.id)), region, date_from, date_to)
        .group_by(PredictionLog.region)
        .all()
    )
    by_type_rows = (
        apply_filters(
            db.query(PredictionLog.predicted_type, func.count(PredictionLog.id)), region, date_from, date_to
        )
        .filter(PredictionLog.predicted_type.isnot(None))
        .group_by(PredictionLog.predicted_type)
        .all()
    )
    daily_rows = (
        apply_filters(
            db.query(func.date(PredictionLog.requested_at), func.count(PredictionLog.id)),
            region,
            date_from,
            date_to,
        )
        .group_by(func.date(PredictionLog.requested_at))
        .order_by(func.date(PredictionLog.requested_at))
        .all()
    )

    return PredictionStatsResponse(
        total_predictions=total_predictions,
        avg_confidence=round(float(avg_confidence), 4) if avg_confidence is not None else None,
        by_region=[RegionCount(region=r, count=c) for r, c in by_region_rows],
        by_type=[TypeCount(predicted_type=t, count=c) for t, c in by_type_rows],
        daily_counts=[DailyCount(day=d, count=c) for d, c in daily_rows],
    )
