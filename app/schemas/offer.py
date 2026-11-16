from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class StreamOfferResponse(BaseModel):
    id: int
    stream_id: int
    keitaro_offer_id: int
    name: Optional[str] = None
    share: int
    is_pinned: bool
    is_removed: bool
    is_new: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddOfferRequest(BaseModel):
    offer_id: int
    name: Optional[str] = None


class PinWeightRequest(BaseModel):
    is_pinned: bool
    share: Optional[int] = None
