import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

STOCK_ITEM_PAYLOAD = {
    "sku": "WIDGET-001",
    "name": "Blue Widget",
    "description": "A reliable blue widget.",
    "unit_price": "9.99",
    "reorder_threshold": 5,
}


async def test_create_stock_item(client: AsyncClient):
    response = await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "WIDGET-001"
    assert data["quantity_on_hand"] == 0


async def test_create_duplicate_sku_returns_409(client: AsyncClient):
    await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    response = await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    assert response.status_code == 409


async def test_get_stock_item(client: AsyncClient):
    create_resp = await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    item_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/stock-items/{item_id}")
    assert response.status_code == 200
    assert response.json()["id"] == item_id
    assert "vendors" in response.json()


async def test_get_nonexistent_item_returns_404(client: AsyncClient):
    response = await client.get(
        "/api/v1/stock-items/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_list_stock_items(client: AsyncClient):
    await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    response = await client.get("/api/v1/stock-items/")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1
    assert isinstance(body["items"], list)


async def test_update_stock_item(client: AsyncClient):
    create_resp = await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    item_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/stock-items/{item_id}",
        json={"name": "Updated Widget", "unit_price": "12.50"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Widget"


async def test_adjust_stock_add(client: AsyncClient):
    create_resp = await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    item_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/stock-items/{item_id}/adjust-stock",
        json={"adjustment": 50, "reason": "Initial stock load"},
    )
    assert response.status_code == 200
    assert response.json()["quantity_on_hand"] == 50


async def test_adjust_stock_below_zero_returns_422(client: AsyncClient):
    create_resp = await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    item_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/stock-items/{item_id}/adjust-stock",
        json={"adjustment": -100},
    )
    assert response.status_code == 422


async def test_delete_stock_item(client: AsyncClient):
    create_resp = await client.post("/api/v1/stock-items/", json=STOCK_ITEM_PAYLOAD)
    item_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/stock-items/{item_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/stock-items/{item_id}")
    assert get_resp.status_code == 404
