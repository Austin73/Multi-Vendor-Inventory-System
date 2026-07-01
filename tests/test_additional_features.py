"""
Tests for features added in the second pass:
- Paginated list responses (total, skip, limit, items)
- Stock item search by name/SKU
- Lookup by SKU
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _make_item(client: AsyncClient, sku: str, name: str, qty: int = 0, threshold: int = 10):
    resp = await client.post(
        "/api/v1/stock-items/",
        json={"sku": sku, "name": name, "unit_price": "5.00", "reorder_threshold": threshold},
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]
    if qty:
        await client.post(
            f"/api/v1/stock-items/{item_id}/adjust-stock", json={"adjustment": qty}
        )
    return resp.json()


# ── Pagination ─────────────────────────────────────────────────────────────────

async def test_list_stock_items_returns_paginated_envelope(client: AsyncClient):
    await _make_item(client, "PAG-001", "Paginated Item A")
    await _make_item(client, "PAG-002", "Paginated Item B")

    response = await client.get("/api/v1/stock-items/?skip=0&limit=50")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "items" in body
    assert "skip" in body
    assert "limit" in body
    assert isinstance(body["items"], list)
    assert body["total"] >= 2


async def test_list_vendors_returns_paginated_envelope(client: AsyncClient):
    await client.post(
        "/api/v1/vendors/", json={"name": "Paging Vendor", "email": "paging@vendor.com"}
    )
    response = await client.get("/api/v1/vendors/")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "items" in body


async def test_list_purchase_orders_returns_paginated_envelope(client: AsyncClient):
    response = await client.get("/api/v1/purchase-orders/")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "items" in body


# ── Search ─────────────────────────────────────────────────────────────────────

async def test_search_stock_items_by_name(client: AsyncClient):
    await _make_item(client, "SRCH-001", "Unique Sprocket Component")
    await _make_item(client, "SRCH-002", "Generic Bolt")

    response = await client.get("/api/v1/stock-items/?search=Sprocket")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any("Sprocket" in i["name"] for i in items)


async def test_search_stock_items_by_sku(client: AsyncClient):
    await _make_item(client, "FINDME-XYZ", "Some Item")

    response = await client.get("/api/v1/stock-items/?search=FINDME")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(i["sku"] == "FINDME-XYZ" for i in items)


async def test_search_no_results(client: AsyncClient):
    response = await client.get("/api/v1/stock-items/?search=ZZZNOMATCH999")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0



# ── Lookup by SKU ──────────────────────────────────────────────────────────────

async def test_get_by_sku(client: AsyncClient):
    await _make_item(client, "BYSKU-001", "Lookup By SKU Item")

    response = await client.get("/api/v1/stock-items/by-sku/BYSKU-001")
    assert response.status_code == 200
    assert response.json()["sku"] == "BYSKU-001"
    assert "vendors" in response.json()


async def test_get_by_sku_case_insensitive(client: AsyncClient):
    await _make_item(client, "CASE-001", "Case Insensitive Item")

    response = await client.get("/api/v1/stock-items/by-sku/case-001")
    assert response.status_code == 200
    assert response.json()["sku"] == "CASE-001"


async def test_get_by_sku_not_found(client: AsyncClient):
    response = await client.get("/api/v1/stock-items/by-sku/DOES-NOT-EXIST")
    assert response.status_code == 404


# ── Health check ───────────────────────────────────────────────────────────────

async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code in (200, 503)  # 503 if DB unavailable in test env
    body = response.json()
    assert "status" in body
    assert "version" in body
    assert "database" in body
