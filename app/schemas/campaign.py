from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.stream import StreamResponse


class CampaignCreate(BaseModel):
    name: str
    geo: str
    offer_id: int
    domain_id: Optional[int] = None
    group_id: Optional[int] = None
    traffic_source_id: Optional[int] = None


class CampaignResponse(BaseModel):
    id: int
    keitaro_id: int
    name: str
    alias: str
    geo: str
    domain_id: Optional[int] = None
    group_id: Optional[int] = None
    traffic_source_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    streams: List[StreamResponse] = []

    model_config = ConfigDict(from_attributes=True)
