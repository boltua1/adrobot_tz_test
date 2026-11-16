from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.services.campaign_service import create_campaign
from app.services.keitaro_client import KeitaroAPIError

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post("", response_model=CampaignResponse)
async def create_new_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Part 1: Campaign Creator.
    Creates a campaign in Keitaro with 2 flows:
      1. Flow 1: redirects traffic from specified countries to google.com
      2. Flow 2: redirects other traffic to the selected offer
    """
    try:
        campaign = await create_campaign(
            db=db,
            name=payload.name,
            geo=payload.geo,
            offer_id=payload.offer_id,
            domain_id=payload.domain_id,
            group_id=payload.group_id,
            traffic_source_id=payload.traffic_source_id
        )
        return campaign
    except KeitaroAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Keitaro API error: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    stmt = select(Campaign).options(
        selectinload(Campaign.streams).selectinload(Campaign.streams.property.mapper.class_.offers)
    ).order_by(Campaign.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Campaign).where(Campaign.id == campaign_id).options(
        selectinload(Campaign.streams).selectinload(Campaign.streams.property.mapper.class_.offers)
    )
    result = await db.execute(stmt)
    camp = result.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp
