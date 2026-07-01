import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

VENDOR_PAYLOAD = {
    "name": "Acme Supplies",
    "email": "orders@acme.com",
    "phone": "+1-555-0100",
    "address": "123 Supply Lane, Commerce City, CA",
}


async def test_create_vendor(client: AsyncClient):
    response = await client.post("/api/v1/vendors/", json=VENDOR_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Supplies"
    assert data["status"] == "active"


async def test_create_duplicate_email_returns_409(client: AsyncClient):
    await client.post("/api/v1/vendors/", json=VENDOR_PAYLOAD)
    response = await client.post("/api/v1/vendors/", json=VENDOR_PAYLOAD)
    assert response.status_code == 409


async def test_get_vendor_detail(client: AsyncClient):
    create_resp = await client.post("/api/v1/vendors/", json=VENDOR_PAYLOAD)
    vendor_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/vendors/{vendor_id}")
    assert response.status_code == 200
    assert "stock_items" in response.json()


async def test_update_vendor_status(client: AsyncClient):
    create_resp = await client.post("/api/v1/vendors/", json=VENDOR_PAYLOAD)
    vendor_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/vendors/{vendor_id}", json={"status": "inactive"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


async def test_delete_vendor(client: AsyncClient):
    create_resp = await client.post("/api/v1/vendors/", json=VENDOR_PAYLOAD)
    vendor_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/vendors/{vendor_id}")
    assert del_resp.status_code == 204
