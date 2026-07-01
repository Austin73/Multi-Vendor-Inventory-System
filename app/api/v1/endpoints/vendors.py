import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateError, NotFoundError
from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.vendor import (
    VendorCreate,
    VendorDetailResponse,
    VendorResponse,
    VendorUpdate,
)
from app.services.vendor import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


def get_service(db: AsyncSession = Depends(get_db)) -> VendorService:
    return VendorService(db)


@router.post("/", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: VendorCreate,
    service: VendorService = Depends(get_service),
):
    """Register a new vendor/supplier in the system."""
    try:
        return await service.create_vendor(payload)
    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/", response_model=PaginatedResponse[VendorResponse])
async def list_vendors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: VendorService = Depends(get_service),
):
    """Retrieve all registered vendors with pagination."""
    vendors, total = await service.list_vendors_paginated(skip=skip, limit=limit)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=vendors)


@router.get("/{vendor_id}", response_model=VendorDetailResponse)
async def get_vendor(
    vendor_id: uuid.UUID,
    service: VendorService = Depends(get_service),
):
    """Get a vendor's full profile including all items they are approved to supply."""
    try:
        return await service.get_vendor_detail(vendor_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    service: VendorService = Depends(get_service),
):
    """Update a vendor's contact details or change their status (active/inactive/suspended)."""
    try:
        return await service.update_vendor(vendor_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: uuid.UUID,
    service: VendorService = Depends(get_service),
):
    """Remove a vendor from the system."""
    try:
        await service.delete_vendor(vendor_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
