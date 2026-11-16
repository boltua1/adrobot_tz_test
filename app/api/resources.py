from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from app.services.keitaro_client import keitaro_client, KeitaroAPIError

router = APIRouter(prefix="/resources", tags=["Keitaro Resources"])


@router.get("/domains")
async def get_domains() -> List[Dict[str, Any]]:
    try:
        return await keitaro_client.get_domains()
    except KeitaroAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Keitaro API error: {e.detail}")


@router.get("/groups")
async def get_groups() -> List[Dict[str, Any]]:
    try:
        return await keitaro_client.get_groups(group_type="campaigns")
    except KeitaroAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Keitaro API error: {e.detail}")


@router.get("/traffic_sources")
async def get_traffic_sources() -> List[Dict[str, Any]]:
    try:
        return await keitaro_client.get_traffic_sources()
    except KeitaroAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Keitaro API error: {e.detail}")
