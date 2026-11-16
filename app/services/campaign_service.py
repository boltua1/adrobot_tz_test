import re
import json
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign
from app.models.stream import Stream
from app.models.offer import StreamOffer
from app.services.keitaro_client import keitaro_client, KeitaroAPIError
from app.config import settings


def _generate_alias(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    if not cleaned:
        cleaned = "campaign"
    return f"{cleaned[:25]}-{uuid.uuid4().hex[:6]}"


def _parse_geo_list(geo: str) -> List[str]:
    return [c.strip().upper() for c in geo.replace(";", ",").split(",") if c.strip()]


async def create_campaign(
    db: AsyncSession,
    name: str,
    geo: str,
    offer_id: int,
    domain_id: Optional[int] = None,
    group_id: Optional[int] = None,
    traffic_source_id: Optional[int] = None
) -> Campaign:
    """
    Part 1: Campaign Creator.
    Creates a campaign in Keitaro with:
      - 2 streams:
        * Flow 1: redirects traffic from specified countries to https://google.com
        * Flow 2: redirects other traffic to the selected offer
      - Configured domain, group, and traffic source.
    Stores the campaign and streams in the local database.
    """
    domain_id = domain_id or settings.KEITARO_DEFAULT_DOMAIN_ID
    group_id = group_id or settings.KEITARO_DEFAULT_GROUP_ID
    traffic_source_id = traffic_source_id or settings.KEITARO_DEFAULT_TRAFFIC_SOURCE_ID

    alias = _generate_alias(name)
    geo_list = _parse_geo_list(geo)
    if not geo_list:
        geo_list = ["AU"]

    # 1. Fetch offer info for display name
    offer_name = f"Offer #{offer_id}"
    try:
        offer_data = await keitaro_client.get_offer(offer_id)
        if isinstance(offer_data, dict) and "name" in offer_data:
            offer_name = offer_data["name"]
    except Exception:
        pass

    # 2. Create campaign in Keitaro
    keitaro_campaign = await keitaro_client.create_campaign(
        name=name,
        alias=alias,
        domain_id=domain_id,
        group_id=group_id,
        traffic_source_id=traffic_source_id
    )
    k_campaign_id = keitaro_campaign["id"]

    # 3. Create Stream 1 (Geo filter -> google.com)
    s1_filters = [{"name": "country", "mode": "accept", "payload": geo_list}]
    s1_options = {"url": "https://google.com"}
    k_stream_1 = await keitaro_client.create_stream(
        campaign_id=k_campaign_id,
        name="Flow 1 (Google)",
        type="regular",
        position=1,
        schema="redirect",
        action_type="http",
        action_options=s1_options,
        filters=s1_filters
    )

    # 4. Create Stream 2 (Offers)
    s2_offers = [{"offer_id": offer_id, "share": 100, "state": "active"}]
    k_stream_2 = await keitaro_client.create_stream(
        campaign_id=k_campaign_id,
        name="Flow 2 (Offers)",
        type="regular",
        position=2,
        schema="landings",
        action_type="http",
        offers=s2_offers
    )

    # 5. Save to local DB
    db_campaign = Campaign(
        keitaro_id=k_campaign_id,
        name=name,
        alias=alias,
        geo=",".join(geo_list),
        domain_id=domain_id,
        group_id=group_id,
        traffic_source_id=traffic_source_id
    )
    db.add(db_campaign)
    await db.flush()

    db_stream_1 = Stream(
        campaign_id=db_campaign.id,
        keitaro_stream_id=k_stream_1["id"],
        name="Flow 1 (Google)",
        position=1,
        schema="redirect",
        action_type="http",
        action_options=json.dumps(s1_options),
        filters=json.dumps(s1_filters),
        is_dirty=False
    )
    db.add(db_stream_1)

    db_stream_2 = Stream(
        campaign_id=db_campaign.id,
        keitaro_stream_id=k_stream_2["id"],
        name="Flow 2 (Offers)",
        position=2,
        schema="landings",
        action_type="http",
        action_options=None,
        filters=None,
        is_dirty=False
    )
    db.add(db_stream_2)
    await db.flush()

    db_offer = StreamOffer(
        stream_id=db_stream_2.id,
        keitaro_offer_id=offer_id,
        name=offer_name,
        share=100,
        is_pinned=False,
        is_removed=False,
        is_new=False
    )
    db.add(db_offer)
    await db.commit()

    # Re-fetch fully loaded campaign with all relationships
    stmt = (
        select(Campaign)
        .where(Campaign.id == db_campaign.id)
        .options(selectinload(Campaign.streams).selectinload(Stream.offers))
    )
    res = await db.execute(stmt)
    return res.scalar_one()
