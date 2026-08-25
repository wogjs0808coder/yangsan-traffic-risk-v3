from pydantic import BaseModel


class RegionResponse(BaseModel):
    regions: list[str]


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
