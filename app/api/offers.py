from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from app.services.keitaro_client import keitaro_client, KeitaroAPIError

router = APIRouter(prefix="/offers", tags=["Offers"])


@router.get("")
async def search_offers(
    query: Optional[str] = Query(None, description="Search term for offer name or ID")
) -> List[Dict[str, Any]]:
    """
    Returns list of offers from Keitaro, optionally filtered by search query.
    Used for autocomplete inputs in Campaign Creator and Stream Editor.
    """
    try:
        offers = await keitaro_client.get_offers()
        if not query:
            return offers[:50]

        q = query.strip().lower()
        filtered = []
        for o in offers:
            o_id = str(o.get("id", ""))
            o_name = str(o.get("name", "")).lower()
            if q in o_id or q in o_name:
                filtered.append(o)
                if len(filtered) >= 50:
                    break
        return filtered
    except KeitaroAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Keitaro API error: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
