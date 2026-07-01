import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.db.session import get_db
from app.schemas.association import LinkVendorToItemRequest, UpdateVendorLinkRequest
from app.schemas.common import PaginatedResponse
from app.schemas.stock_item import (
    StockItemAdjustQuantity,
    StockItemCreate,
    StockItemDetailResponse,
    StockItemResponse,
    StockItemUpdate,
    StockItemVendorResponse,
)
from app.services.stock_item import StockItemService

router = APIRouter(prefix="/stock-items", tags=["Stock Items"])


def get_service(db: AsyncSession = Depends(get_db)) -> StockItemService:
    return StockItemService(db)


@router.post("/", response_model=StockItemResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_item(
    payload: StockItemCreate,
    service: StockItemService = Depends(get_service),
):
    """Register a new stock item in the inventory."""
    try:
        return await service.create_item(payload)
    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/", response_model=PaginatedResponse[StockItemResponse])
async def list_stock_items(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, description="Search by name or SKU"),
    service: StockItemService = Depends(get_service),
):
    """Retrieve all stock items with optional pagination and search."""
    items, total = await service.list_items_paginated(skip=skip, limit=limit, search=search)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


@router.get("/by-sku/{sku}", response_model=StockItemDetailResponse)
async def get_stock_item_by_sku(
    sku: str,
    service: StockItemService = Depends(get_service),
):
    """Look up a stock item by its SKU. Case-insensitive."""
    try:
        return await service.get_item_by_sku(sku.upper())
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{item_id}", response_model=StockItemDetailResponse)
async def get_stock_item(
    item_id: uuid.UUID,
    service: StockItemService = Depends(get_service),
):
    """Get a single stock item along with its approved vendor list."""
    try:
        return await service.get_item_detail(item_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{item_id}", response_model=StockItemResponse)
async def update_stock_item(
    item_id: uuid.UUID,
    payload: StockItemUpdate,
    service: StockItemService = Depends(get_service),
):
    """Partially update a stock item's details."""
    try:
        return await service.update_item(item_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_item(
    item_id: uuid.UUID,
    service: StockItemService = Depends(get_service),
):
    """Remove a stock item from the registry."""
    try:
        await service.delete_item(item_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{item_id}/adjust-stock", response_model=StockItemResponse)
async def adjust_stock(
    item_id: uuid.UUID,
    payload: StockItemAdjustQuantity,
    service: StockItemService = Depends(get_service),
):
    """Adjust stock quantity (positive = add stock, negative = remove stock)."""
    try:
        return await service.adjust_stock(item_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ── Vendor-item association endpoints ─────────────────────────────────────────

@router.get("/{item_id}/vendors", response_model=list[StockItemVendorResponse])
async def get_item_vendors(
    item_id: uuid.UUID,
    service: StockItemService = Depends(get_service),
):
    """List all vendors approved to supply a specific stock item."""
    try:
        return await service.get_item_vendors(item_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{item_id}/vendors",
    response_model=StockItemDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_vendor_to_item(
    item_id: uuid.UUID,
    payload: LinkVendorToItemRequest,
    service: StockItemService = Depends(get_service),
):
    """
    Approve a vendor to supply a specific stock item.

    Records the agreed vendor price and expected lead time alongside the link.
    This must be done before the vendor can appear on a purchase order for this item.
    """
    try:
        return await service.link_vendor(item_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch(
    "/{item_id}/vendors/{vendor_id}",
    response_model=StockItemDetailResponse,
)
async def update_vendor_link(
    item_id: uuid.UUID,
    vendor_id: uuid.UUID,
    payload: UpdateVendorLinkRequest,
    service: StockItemService = Depends(get_service),
):
    """Update the agreed pricing or lead time for an approved vendor on a stock item."""
    try:
        return await service.update_vendor_link(item_id, vendor_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{item_id}/vendors/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_vendor_from_item(
    item_id: uuid.UUID,
    vendor_id: uuid.UUID,
    service: StockItemService = Depends(get_service),
):
    """Revoke a vendor's approval to supply a specific stock item."""
    try:
        await service.unlink_vendor(item_id, vendor_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
