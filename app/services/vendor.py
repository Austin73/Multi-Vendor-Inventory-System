import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateError, NotFoundError
from app.models.inventory import Vendor
from app.repositories.vendor import VendorRepository
from app.schemas.vendor import (
    VendorCreate,
    VendorDetailResponse,
    VendorResponse,
    VendorStockLinkResponse,
    StockItemBriefResponse,
    VendorUpdate,
)


class VendorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = VendorRepository(session)

    async def create_vendor(self, data: VendorCreate) -> VendorResponse:
        existing = await self.repo.get_by_email(str(data.email))
        if existing:
            raise DuplicateError("Vendor", "email", data.email)

        vendor = await self.repo.create(data)
        return VendorResponse.model_validate(vendor)

    async def get_vendor(self, vendor_id: uuid.UUID) -> VendorResponse:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        return VendorResponse.model_validate(vendor)

    async def get_vendor_detail(self, vendor_id: uuid.UUID) -> VendorDetailResponse:
        vendor = await self.repo.get_by_id_with_items(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)

        stock_links = [
            VendorStockLinkResponse(
                stock_item=StockItemBriefResponse.model_validate(link.stock_item),
                vendor_sku=link.vendor_sku,
                vendor_price=float(link.vendor_price),
                lead_time_days=link.lead_time_days,
            )
            for link in vendor.stock_links
        ]

        return VendorDetailResponse(
            **VendorResponse.model_validate(vendor).model_dump(),
            stock_items=stock_links,
        )

    async def list_vendors(
        self, skip: int = 0, limit: int = 100
    ) -> list[VendorResponse]:
        vendors = await self.repo.get_all_with_pagination(skip=skip, limit=limit)
        return [VendorResponse.model_validate(v) for v in vendors]

    async def update_vendor(
        self, vendor_id: uuid.UUID, data: VendorUpdate
    ) -> VendorResponse:
        vendor = await self._get_or_404(vendor_id)
        updated = await self.repo.update(vendor, data)
        return VendorResponse.model_validate(updated)

    async def delete_vendor(self, vendor_id: uuid.UUID) -> None:
        vendor = await self._get_or_404(vendor_id)
        await self.repo.delete(vendor)

    async def _get_or_404(self, vendor_id: uuid.UUID) -> Vendor:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        return vendor

    async def list_vendors_paginated(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[VendorResponse], int]:
        vendors = await self.repo.get_all_with_pagination(skip=skip, limit=limit)
        total = await self.repo.count_all()
        return [VendorResponse.model_validate(v) for v in vendors], total
