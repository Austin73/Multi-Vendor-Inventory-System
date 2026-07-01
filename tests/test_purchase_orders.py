import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

VENDOR_PAYLOAD = {"name": "TechParts Ltd", "email": "supply@techparts.com"}
ITEM_PAYLOAD = {
    "sku": "BOLT-M8",
    "name": "M8 Hex Bolt",
    "unit_price": "0.50",
    "reorder_threshold": 100,
}


async def _setup_vendor_and_item(client: AsyncClient):
    """Helper: create a vendor, a stock item, and link them."""
    vendor_resp = await client.post("/api/v1/vendors/", json=VENDOR_PAYLOAD)
    assert vendor_resp.status_code == 201
    vendor_id = vendor_resp.json()["id"]

    item_resp = await client.post("/api/v1/stock-items/", json=ITEM_PAYLOAD)
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    link_resp = await client.post(
        f"/api/v1/stock-items/{item_id}/vendors",
        json={"vendor_id": vendor_id, "vendor_price": "0.45", "lead_time_days": 3},
    )
    assert link_resp.status_code == 201

    return vendor_id, item_id


async def test_create_purchase_order(client: AsyncClient):
    vendor_id, item_id = await _setup_vendor_and_item(client)

    response = await client.post(
        "/api/v1/purchase-orders/",
        json={
            "vendor_id": vendor_id,
            "notes": "Urgent restock",
            "lines": [{"stock_item_id": item_id, "quantity": 200}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert len(data["lines"]) == 1
    assert data["lines"][0]["unit_price"] == "0.45"  # pulled from the link
    assert float(data["total_amount"]) == 90.0  # 200 * 0.45


async def test_order_with_unlinked_vendor_returns_422(client: AsyncClient):
    # Create a vendor and item but do NOT link them
    vendor_resp = await client.post(
        "/api/v1/vendors/", json={"name": "Unlinked Vendor", "email": "unlinked@vendor.com"}
    )
    vendor_id = vendor_resp.json()["id"]

    item_resp = await client.post(
        "/api/v1/stock-items/",
        json={"sku": "UNLINKED-01", "name": "Unlinked Item", "unit_price": "1.00"},
    )
    item_id = item_resp.json()["id"]

    response = await client.post(
        "/api/v1/purchase-orders/",
        json={
            "vendor_id": vendor_id,
            "lines": [{"stock_item_id": item_id, "quantity": 10}],
        },
    )
    assert response.status_code == 422
    assert "approved supplier" in response.json()["detail"]


async def test_order_status_transitions(client: AsyncClient):
    vendor_id, item_id = await _setup_vendor_and_item(client)
    create_resp = await client.post(
        "/api/v1/purchase-orders/",
        json={
            "vendor_id": vendor_id,
            "lines": [{"stock_item_id": item_id, "quantity": 10}],
        },
    )
    order_id = create_resp.json()["id"]

    # draft → submitted
    resp = await client.patch(
        f"/api/v1/purchase-orders/{order_id}/status", json={"status": "submitted"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"

    # submitted → confirmed
    resp = await client.patch(
        f"/api/v1/purchase-orders/{order_id}/status", json={"status": "confirmed"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    # confirmed → received
    resp = await client.patch(
        f"/api/v1/purchase-orders/{order_id}/status", json={"status": "received"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


async def test_invalid_status_transition_returns_422(client: AsyncClient):
    vendor_id, item_id = await _setup_vendor_and_item(client)
    create_resp = await client.post(
        "/api/v1/purchase-orders/",
        json={
            "vendor_id": vendor_id,
            "lines": [{"stock_item_id": item_id, "quantity": 10}],
        },
    )
    order_id = create_resp.json()["id"]

    # draft → received (invalid leap)
    resp = await client.patch(
        f"/api/v1/purchase-orders/{order_id}/status", json={"status": "received"}
    )
    assert resp.status_code == 422


async def test_cancel_order(client: AsyncClient):
    vendor_id, item_id = await _setup_vendor_and_item(client)
    create_resp = await client.post(
        "/api/v1/purchase-orders/",
        json={
            "vendor_id": vendor_id,
            "lines": [{"stock_item_id": item_id, "quantity": 10}],
        },
    )
    order_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/purchase-orders/{order_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_inactive_vendor_cannot_place_order(client: AsyncClient):
    vendor_id, item_id = await _setup_vendor_and_item(client)

    # Deactivate vendor
    await client.patch(f"/api/v1/vendors/{vendor_id}", json={"status": "inactive"})

    response = await client.post(
        "/api/v1/purchase-orders/",
        json={
            "vendor_id": vendor_id,
            "lines": [{"stock_item_id": item_id, "quantity": 10}],
        },
    )
    assert response.status_code == 422
    assert "not active" in response.json()["detail"]
