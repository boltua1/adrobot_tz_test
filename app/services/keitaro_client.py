import logging
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class KeitaroAPIError(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(f"Keitaro API Error {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class KeitaroClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.base_url = (base_url or settings.KEITARO_API_URL).rstrip("/")
        self.api_key = api_key or settings.KEITARO_API_KEY

    def _headers(self) -> Dict[str, str]:
        return {
            "Api-Key": self.api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=data if data is not None else None,
                    params=params
                )
            except httpx.RequestError as exc:
                logger.error(f"HTTP request failed: {exc}")
                raise KeitaroAPIError(status_code=500, detail=str(exc))

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = response.text
                logger.error(f"Keitaro API error {response.status_code} on {method} {url}: {error_data}")
                raise KeitaroAPIError(status_code=response.status_code, detail=error_data)

            try:
                return response.json()
            except Exception:
                return response.text

    # --- Campaigns ---
    async def get_campaigns(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/campaigns")

    async def get_campaign(self, campaign_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"/campaigns/{campaign_id}")

    async def create_campaign(
        self,
        name: str,
        alias: str,
        domain_id: Optional[int] = None,
        group_id: Optional[int] = None,
        traffic_source_id: Optional[int] = None,
        cost_type: str = "CPC",
        cost_value: float = 0.0,
        cost_currency: str = "USD"
    ) -> Dict[str, Any]:
        payload = {
            "name": name,
            "alias": alias,
            "domain_id": domain_id or settings.KEITARO_DEFAULT_DOMAIN_ID,
            "group_id": group_id or settings.KEITARO_DEFAULT_GROUP_ID,
            "traffic_source_id": traffic_source_id or settings.KEITARO_DEFAULT_TRAFFIC_SOURCE_ID,
            "cost_type": cost_type,
            "cost_value": cost_value,
            "cost_currency": cost_currency,
            "cost_auto": False
        }
        return await self._request("POST", "/campaigns", data=payload)

    async def delete_campaign(self, campaign_id: int) -> Any:
        return await self._request("DELETE", f"/campaigns/{campaign_id}")

    # --- Streams / Flows ---
    async def get_campaign_streams(self, campaign_id: int) -> List[Dict[str, Any]]:
        return await self._request("GET", f"/campaigns/{campaign_id}/streams")

    async def get_stream(self, stream_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"/streams/{stream_id}")

    async def create_stream(
        self,
        campaign_id: int,
        name: str,
        type: str = "regular",
        position: int = 1,
        schema: str = "landings",
        action_type: str = "http",
        action_options: Optional[Dict[str, Any]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        offers: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "name": name,
            "type": type,
            "position": position,
            "schema": schema,
            "action_type": action_type,
            "collect_clicks": True
        }
        if action_options is not None:
            payload["action_options"] = action_options
        if filters is not None:
            payload["filters"] = filters
        if offers is not None:
            payload["offers"] = offers

        return await self._request("POST", "/streams", data=payload)

    async def update_stream(self, stream_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", f"/streams/{stream_id}", data=data)

    async def delete_stream(self, stream_id: int) -> Any:
        return await self._request("DELETE", f"/streams/{stream_id}")

    # --- Offers ---
    async def get_offers(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/offers")

    async def get_offer(self, offer_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"/offers/{offer_id}")

    # --- Resources ---
    async def get_domains(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/domains")

    async def get_groups(self, group_type: str = "campaigns") -> List[Dict[str, Any]]:
        return await self._request("GET", "/groups", params={"type": group_type})

    async def get_traffic_sources(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/traffic_sources")


keitaro_client = KeitaroClient()
