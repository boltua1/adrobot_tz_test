from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.stream import StreamResponse
from app.schemas.offer import AddOfferRequest, PinWeightRequest
from app.services import stream_service
from app.services.keitaro_client import KeitaroAPIError

router = APIRouter(tags=["Streams & Offers"])


@router.post("/campaigns/{campaign_id}/fetch_streams", response_model=List[StreamResponse])
async def fetch_campaign_streams(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch and synchronize streams from Keitaro Tracker.
    """
    try:
        streams = await stream_service.fetch_streams(db, campaign_id)
        return streams
    except KeitaroAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Keitaro API error: {e.detail}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/{stream_id}/offers", response_model=StreamResponse)
async def add_offer(
    stream_id: int,
    payload: AddOfferRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Add an offer to a stream. Recalculates weights and turns the stream yellow.
    """
    try:
        stream = await stream_service.add_offer_to_stream(
            db=db,
            stream_id=stream_id,
            offer_id=payload.offer_id,
            offer_name=payload.name
        )
        return stream
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/streams/{stream_id}/offers/{offer_id}", response_model=StreamResponse)
async def remove_offer(
    stream_id: int,
    offer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Soft-delete an offer (gray status, share 0%, brings Bring Back button).
    """
    try:
        stream = await stream_service.remove_offer_from_stream(
            db=db,
            stream_id=stream_id,
            offer_id=offer_id
        )
        return stream
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/{stream_id}/offers/{offer_id}/bring_back", response_model=StreamResponse)
async def bring_back_offer(
    stream_id: int,
    offer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Restores a soft-deleted offer, rebalances weights, turns stream yellow.
    """
    try:
        stream = await stream_service.bring_back_offer(
            db=db,
            stream_id=stream_id,
            offer_id=offer_id
        )
        return stream
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/{stream_id}/offers/{offer_id}/pin", response_model=StreamResponse)
async def pin_weight(
    stream_id: int,
    offer_id: int,
    payload: PinWeightRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Pins or unpins the share for an offer.
    """
    try:
        stream = await stream_service.pin_offer_weight(
            db=db,
            stream_id=stream_id,
            offer_id=offer_id,
            is_pinned=payload.is_pinned,
            share=payload.share
        )
        return stream
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/{stream_id}/cancel", response_model=StreamResponse)
async def cancel_changes(
    stream_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancels unpushed changes and restores previous clean state.
    """
    try:
        stream = await stream_service.cancel_stream_changes(db, stream_id)
        return stream
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/{stream_id}/push", response_model=StreamResponse)
async def push_to_keitaro(
    stream_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Pushes active offers and calculated weights to Keitaro.
    """
    try:
        stream = await stream_service.push_stream_to_keitaro(db, stream_id)
        return stream
    except KeitaroAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Keitaro API error: {e.detail}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
