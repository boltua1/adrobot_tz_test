from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.offer import StreamOfferResponse


class StreamResponse(BaseModel):
    id: int
    campaign_id: int
    keitaro_stream_id: int
    name: str
    position: int
    schema_type: str = Field(alias="schema")
    action_type: str
    action_options: Optional[str] = None
    filters: Optional[str] = None
    is_dirty: bool
    created_at: datetime
    updated_at: datetime
    offers: List[StreamOfferResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
