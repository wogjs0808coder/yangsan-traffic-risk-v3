from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/accidents/stats")
def get_accident_stats(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT region, COUNT(*) AS count FROM accidents GROUP BY region")).all()
    return {"by_region": [{"region": r, "count": c} for r, c in rows]}
