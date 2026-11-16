import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.stream import Stream
from app.models.offer import StreamOffer
from app.models.campaign import Campaign
from app.services.keitaro_client import keitaro_client, KeitaroAPIError
from app.services.weight_calculator import calculate_weights

logger = logging.getLogger(__name__)


def _rebalance_stream_offers(offers: List[StreamOffer]):
    """
    Adapts StreamOffer models to dicts, calculates new weights,
    and assigns shares back to the models.
    """
    dict_offers = [
        {
            "model": o,
            "is_removed": o.is_removed,
            "is_pinned": o.is_pinned,
            "share": o.share
        }
        for o in offers
    ]
    calculate_weights(dict_offers)
    for d in dict_offers:
        d["model"].share = d["share"]


async def _get_fully_loaded_stream(db: AsyncSession, stream_id: int) -> Stream:
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.offers))
    res = await db.execute(stmt)
    return res.scalar_one()


async def fetch_streams(db: AsyncSession, campaign_id: int) -> List[Stream]:
    """
    Fetches streams from Keitaro and syncs them into the local DB.
    - Preserves streams without offers without deep parsing.
    - Synchronizes offers: active in Keitaro stay active, removed in Keitaro become soft-deleted (is_removed=True).
    - Clears dirty flag.
    """
    camp_stmt = select(Campaign).where(Campaign.id == campaign_id).options(
        selectinload(Campaign.streams).selectinload(Stream.offers)
    )
    result = await db.execute(camp_stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found")

    keitaro_streams = await keitaro_client.get_campaign_streams(campaign.keitaro_id)
    existing_streams_map = {s.keitaro_stream_id: s for s in campaign.streams}

    for k_stream in keitaro_streams:
        k_stream_id = k_stream["id"]
        schema = k_stream.get("schema", "landings")
        position = k_stream.get("position", 1)
        name = k_stream.get("name", f"Stream {position}")
        action_type = k_stream.get("action_type", "http")
        action_options = json.dumps(k_stream.get("action_options")) if k_stream.get("action_options") else None
        filters = json.dumps(k_stream.get("filters")) if k_stream.get("filters") else None

        if k_stream_id in existing_streams_map:
            db_stream = existing_streams_map[k_stream_id]
            db_stream.name = name
            db_stream.position = position
            db_stream.schema = schema
            db_stream.action_type = action_type
            db_stream.action_options = action_options
            db_stream.filters = filters
            db_stream.is_dirty = False
        else:
            db_stream = Stream(
                campaign_id=campaign.id,
                keitaro_stream_id=k_stream_id,
                name=name,
                position=position,
                schema=schema,
                action_type=action_type,
                action_options=action_options,
                filters=filters,
                is_dirty=False
            )
            db.add(db_stream)
            await db.flush()
            existing_streams_map[k_stream_id] = db_stream

        # If stream has offers or is a landings stream
        k_offers = k_stream.get("offers", [])
        if k_offers or schema == "landings":
            k_offers_map = {o["offer_id"]: o for o in k_offers}
            existing_offers_map = {o.keitaro_offer_id: o for o in db_stream.offers}

            for k_off_id, k_off_data in k_offers_map.items():
                if k_off_id in existing_offers_map:
                    db_off = existing_offers_map[k_off_id]
                    db_off.share = k_off_data.get("share", 100)
                    db_off.is_removed = False
                    db_off.is_new = False
                else:
                    off_name = f"Offer #{k_off_id}"
                    try:
                        info = await keitaro_client.get_offer(k_off_id)
                        if isinstance(info, dict) and "name" in info:
                            off_name = info["name"]
                    except Exception:
                        pass

                    new_off = StreamOffer(
                        stream_id=db_stream.id,
                        keitaro_offer_id=k_off_id,
                        name=off_name,
                        share=k_off_data.get("share", 100),
                        is_pinned=False,
                        is_removed=False,
                        is_new=False
                    )
                    db.add(new_off)

            for db_off_id, db_off in existing_offers_map.items():
                if db_off_id not in k_offers_map:
                    db_off.is_removed = True
                    db_off.share = 0
                    db_off.is_new = False

    await db.commit()
    res = await db.execute(camp_stmt)
    return res.scalar_one().streams


async def add_offer_to_stream(
    db: AsyncSession,
    stream_id: int,
    offer_id: int,
    offer_name: Optional[str] = None
) -> Stream:
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.offers))
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()
    if not stream:
        raise ValueError(f"Stream with ID {stream_id} not found")

    if not offer_name:
        offer_name = f"Offer #{offer_id}"
        try:
            info = await keitaro_client.get_offer(offer_id)
            if isinstance(info, dict) and "name" in info:
                offer_name = info["name"]
        except Exception:
            pass

    existing = next((o for o in stream.offers if o.keitaro_offer_id == offer_id), None)
    if existing:
        existing.is_removed = False
        existing.name = offer_name or existing.name
    else:
        new_offer = StreamOffer(
            stream_id=stream.id,
            keitaro_offer_id=offer_id,
            name=offer_name,
            share=0,
            is_pinned=False,
            is_removed=False,
            is_new=True
        )
        db.add(new_offer)
        stream.offers.append(new_offer)

    _rebalance_stream_offers(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return await _get_fully_loaded_stream(db, stream_id)


async def remove_offer_from_stream(
    db: AsyncSession,
    stream_id: int,
    offer_id: int
) -> Stream:
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.offers))
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()
    if not stream:
        raise ValueError(f"Stream with ID {stream_id} not found")

    target = next((o for o in stream.offers if o.keitaro_offer_id == offer_id), None)
    if not target:
        raise ValueError(f"Offer with ID {offer_id} not found in stream")

    target.is_removed = True
    target.is_pinned = False
    target.share = 0

    _rebalance_stream_offers(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return await _get_fully_loaded_stream(db, stream_id)


async def bring_back_offer(
    db: AsyncSession,
    stream_id: int,
    offer_id: int
) -> Stream:
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.offers))
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()
    if not stream:
        raise ValueError(f"Stream with ID {stream_id} not found")

    target = next((o for o in stream.offers if o.keitaro_offer_id == offer_id), None)
    if not target:
        raise ValueError(f"Offer with ID {offer_id} not found in stream")

    target.is_removed = False
    _rebalance_stream_offers(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return await _get_fully_loaded_stream(db, stream_id)


async def pin_offer_weight(
    db: AsyncSession,
    stream_id: int,
    offer_id: int,
    is_pinned: bool,
    share: Optional[int] = None
) -> Stream:
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.offers))
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()
    if not stream:
        raise ValueError(f"Stream with ID {stream_id} not found")

    target = next((o for o in stream.offers if o.keitaro_offer_id == offer_id), None)
    if not target:
        raise ValueError(f"Offer with ID {offer_id} not found in stream")

    target.is_pinned = is_pinned
    if share is not None and not target.is_removed:
        target.share = max(0, min(100, share))

    _rebalance_stream_offers(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return await _get_fully_loaded_stream(db, stream_id)


async def cancel_stream_changes(
    db: AsyncSession,
    stream_id: int
) -> Stream:
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.offers))
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()
    if not stream:
        raise ValueError(f"Stream with ID {stream_id} not found")

    k_stream = await keitaro_client.get_stream(stream.keitaro_stream_id)
    k_offers = k_stream.get("offers", [])
    k_offers_map = {o["offer_id"]: o for o in k_offers}

    for o in list(stream.offers):
        if o.is_new:
            await db.delete(o)
        elif o.keitaro_offer_id in k_offers_map:
            o.is_removed = False
            o.share = k_offers_map[o.keitaro_offer_id].get("share", 100)
            o.is_pinned = False
        else:
            o.is_removed = True
            o.share = 0

    stream.is_dirty = False
    await db.commit()
    return await _get_fully_loaded_stream(db, stream_id)


async def push_stream_to_keitaro(
    db: AsyncSession,
    stream_id: int
) -> Stream:
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.offers))
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()
    if not stream:
        raise ValueError(f"Stream with ID {stream_id} not found")

    active_offers = [o for o in stream.offers if not o.is_removed]

    payload = {
        "name": stream.name,
        "offers": [
            {
                "offer_id": o.keitaro_offer_id,
                "share": o.share,
                "state": "active"
            }
            for o in active_offers
        ]
    }

    await keitaro_client.update_stream(stream.keitaro_stream_id, payload)

    for o in stream.offers:
        o.is_new = False

    stream.is_dirty = False
    await db.commit()
    return await _get_fully_loaded_stream(db, stream_id)
