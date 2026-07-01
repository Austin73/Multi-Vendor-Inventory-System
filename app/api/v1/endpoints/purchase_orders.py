import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderDetailResponse,
    PurchaseOrderResponse,
    PurchaseOrderStatusUpdate,
)
from app.services.purchase_order import PurchaseOrderService

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


def get_service(db: AsyncSession = Depends(get_db)) -> PurchaseOrderService:
    return PurchaseOrderService(db)


@router.post(
    "/",
    response_model=PurchaseOrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    service: PurchaseOrderService = Depends(get_service),
):
    """
    Create a new purchase order.

    **Business rules enforced:**
    - The selected vendor must be `active`.
    - For every line item, the vendor must already be linked to that stock item
      (i.e. pre-approved as a supplier).
    - Unit prices are automatically sourced from the vendor-item link — the caller
      does not set prices.

    The order is created in `draft` status and must be advanced via the status endpoint.
    """
    try:
        return await service.create_order(payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/", response_model=PaginatedResponse[PurchaseOrderResponse])
async def list_purchase_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    vendor_id: uuid.UUID | None = Query(default=None, description="Filter by vendor"),
    service: PurchaseOrderService = Depends(get_service),
):
    """List purchase orders with pagination. Optionally filter by vendor."""
    orders, total = await service.list_orders_paginated(
        skip=skip, limit=limit, vendor_id=vendor_id
    )
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=orders)


@router.get("/{order_id}", response_model=PurchaseOrderDetailResponse)
async def get_purchase_order(
    order_id: uuid.UUID,
    service: PurchaseOrderService = Depends(get_service),
):
    """Get full details of a purchase order including vendor info and all line items."""
    try:
        return await service.get_order_detail(order_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{order_id}/status", response_model=PurchaseOrderDetailResponse)
async def update_order_status(
    order_id: uuid.UUID,
    payload: PurchaseOrderStatusUpdate,
    service: PurchaseOrderService = Depends(get_service),
):
    """
    Advance or cancel a purchase order.

    **Valid transitions:**
    - `draft` → `submitted` or `cancelled`
    - `submitted` → `confirmed` or `cancelled`
    - `confirmed` → `received` or `cancelled`
    - `received` → *(terminal — no further changes)*
    - `cancelled` → *(terminal — no further changes)*
    """
    try:
        return await service.update_status(order_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{order_id}/cancel", response_model=PurchaseOrderDetailResponse)
async def cancel_purchase_order(
    order_id: uuid.UUID,
    service: PurchaseOrderService = Depends(get_service),
):
    """Convenience endpoint to cancel a purchase order (valid from draft, submitted, or confirmed)."""
    try:
        return await service.cancel_order(order_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
