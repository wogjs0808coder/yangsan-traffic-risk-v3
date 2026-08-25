from sqlalchemy import BigInteger, Column, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.session import Base


class Accident(Base):
    __tablename__ = "accidents"

    id = Column(BigInteger, primary_key=True)
    accident_dt = Column(DateTime, nullable=False)
    region = Column(String(30), nullable=False)
    accident_type = Column(String(30), nullable=False)
    vehicle_type = Column(String(20))
    age_group = Column(String(20))
    weather = Column(String(20))
    violation = Column(String(30))
    road_condition = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id = Column(BigInteger, primary_key=True)
    region = Column(String(30), nullable=False)
    model_version = Column(String(20), nullable=False)
    algorithm = Column(String(30), nullable=False)
    weighted_f1 = Column(Numeric(5, 4))
    trained_at = Column(DateTime, server_default=func.now())
    artifact_path = Column(String(255), nullable=False)


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(BigInteger, primary_key=True)
    region = Column(String(30), nullable=False)
    request_payload = Column(JSONB, nullable=False)
    predicted_type = Column(String(30))
    confidence = Column(Numeric(5, 4))
    requested_at = Column(DateTime, server_default=func.now())
