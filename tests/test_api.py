import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.keitaro_client import keitaro_client


@pytest.mark.asyncio
async def test_root_index():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        assert "Keitaro Flow Manager" in response.text
        assert "New campaign" in response.text


@pytest.mark.asyncio
async def test_search_offers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/offers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "id" in data[0]
            assert "name" in data[0]


@pytest.mark.asyncio
async def test_get_resources():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Domains
        r_dom = await ac.get("/api/resources/domains")
        assert r_dom.status_code == 200
        assert isinstance(r_dom.json(), list)

        # Groups
        r_grp = await ac.get("/api/resources/groups")
        assert r_grp.status_code == 200
        assert isinstance(r_grp.json(), list)

        # Sources
        r_src = await ac.get("/api/resources/traffic_sources")
        assert r_src.status_code == 200
        assert isinstance(r_src.json(), list)


@pytest.mark.asyncio
async def test_campaign_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_name = f"test_pytest_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique_name,
            "geo": "AU, MX",
            "offer_id": 25327
        }
        res = await ac.post("/api/campaigns", json=payload)
        assert res.status_code == 200
        camp = res.json()
        camp_id = camp["id"]
        k_id = camp["keitaro_id"]
        assert camp["name"] == unique_name
        assert len(camp["streams"]) == 2

        # Verify Stream 1 (Redirect)
        s1 = next(s for s in camp["streams"] if s["position"] == 1)
        assert s1.get("schema") == "redirect" or s1.get("schema_type") == "redirect"
        assert "https://google.com" in s1["action_options"]
        assert "AU" in s1["filters"]

        # Verify Stream 2 (Offers)
        s2 = next(s for s in camp["streams"] if s["position"] == 2)
        assert s2.get("schema") == "landings" or s2.get("schema_type") == "landings"
        assert len(s2["offers"]) == 1
        assert s2["offers"][0]["share"] == 100
        assert s2["offers"][0]["keitaro_offer_id"] == 25327

        s2_id = s2["id"]

        try:
            # 2. Add an offer to Stream 2
            add_res = await ac.post(f"/api/streams/{s2_id}/offers", json={"offer_id": 25326, "name": "Second Offer"})
            assert add_res.status_code == 200
            updated_s2 = add_res.json()
            assert updated_s2["is_dirty"] is True
            assert len(updated_s2["offers"]) == 2
            assert updated_s2["offers"][0]["share"] == 50
            assert updated_s2["offers"][1]["share"] == 50

            # 3. Pin weight of first offer to 25%
            pin_res = await ac.post(f"/api/streams/{s2_id}/offers/25327/pin", json={"is_pinned": True, "share": 25})
            assert pin_res.status_code == 200
            pinned_s2 = pin_res.json()
            off1 = next(o for o in pinned_s2["offers"] if o["keitaro_offer_id"] == 25327)
            off2 = next(o for o in pinned_s2["offers"] if o["keitaro_offer_id"] == 25326)
            assert off1["share"] == 25
            assert off1["is_pinned"] is True
            assert off2["share"] == 75

            # 4. Push to Keitaro
            push_res = await ac.post(f"/api/streams/{s2_id}/push")
            assert push_res.status_code == 200
            pushed_s2 = push_res.json()
            assert pushed_s2["is_dirty"] is False

            # 5. Remove an offer (soft delete)
            del_res = await ac.delete(f"/api/streams/{s2_id}/offers/25326")
            assert del_res.status_code == 200
            del_s2 = del_res.json()
            off2_del = next(o for o in del_s2["offers"] if o["keitaro_offer_id"] == 25326)
            assert off2_del["is_removed"] is True
            assert off2_del["share"] == 0
            assert del_s2["is_dirty"] is True

            # 6. Bring back offer
            back_res = await ac.post(f"/api/streams/{s2_id}/offers/25326/bring_back")
            assert back_res.status_code == 200
            back_s2 = back_res.json()
            off2_back = next(o for o in back_s2["offers"] if o["keitaro_offer_id"] == 25326)
            assert off2_back["is_removed"] is False

        finally:
            # Clean up campaign in Keitaro tracker
            try:
                await keitaro_client.delete_campaign(k_id)
            except Exception:
                pass
