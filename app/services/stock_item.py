import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.models.inventory import StockItem
from app.repositories.association import AssociationRepository
from app.repositories.stock_item import StockItemRepository
from app.repositories.vendor import VendorRepository
from app.schemas.association import LinkVendorToItemRequest, UpdateVendorLinkRequest
from app.schemas.stock_item import (
    StockItemAdjustQuantity,
    StockItemCreate,
    StockItemDetailResponse,
    StockItemResponse,
    StockItemUpdate,
    StockItemVendorResponse,
    VendorBriefResponse,
)


class StockItemService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StockItemRepository(session)
        self.vendor_repo = VendorRepository(session)
        self.assoc_repo = AssociationRepository(session)

    async def create_item(self, data: StockItemCreate) -> StockItemResponse:
        existing = await self.repo.get_by_sku(data.sku)
        if existing:
            raise DuplicateError("StockItem", "sku", data.sku)

        item = await self.repo.create(data)
        return StockItemResponse.model_validate(item)

    async def get_item(self, item_id: uuid.UUID) -> StockItemResponse:
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise NotFoundError("StockItem", item_id)
        return StockItemResponse.model_validate(item)

    async def get_item_detail(self, item_id: uuid.UUID) -> StockItemDetailResponse:
        item = await self.repo.get_by_id_with_vendors(item_id)
        if not item:
            raise NotFoundError("StockItem", item_id)

        vendor_responses = [
            StockItemVendorResponse(
                vendor=VendorBriefResponse.model_validate(link.vendor),
                vendor_sku=link.vendor_sku,
                vendor_price=link.vendor_price,
                lead_time_days=link.lead_time_days,
            )
            for link in item.vendor_links
        ]

        return StockItemDetailResponse(
            **StockItemResponse.model_validate(item).model_dump(),
            vendors=vendor_responses,
        )

    async def list_items(
        self, skip: int = 0, limit: int = 100
    ) -> list[StockItemResponse]:
        items = await self.repo.get_all_with_pagination(skip=skip, limit=limit)
        return [StockItemResponse.model_validate(i) for i in items]

    async def update_item(
        self, item_id: uuid.UUID, data: StockItemUpdate
    ) -> StockItemResponse:
        item = await self._get_or_404(item_id)
        updated = await self.repo.update(item, data)
        return StockItemResponse.model_validate(updated)

    async def delete_item(self, item_id: uuid.UUID) -> None:
        item = await self._get_or_404(item_id)
        await self.repo.delete(item)

    async def adjust_stock(
        self, item_id: uuid.UUID, adjustment_data: StockItemAdjustQuantity
    ) -> StockItemResponse:
        item = await self._get_or_404(item_id)
        new_qty = item.quantity_on_hand + adjustment_data.adjustment
        if new_qty < 0:
            raise BusinessRuleError(
                f"Cannot reduce stock below 0. "
                f"Current quantity: {item.quantity_on_hand}, "
                f"Requested adjustment: {adjustment_data.adjustment}."
            )
        updated = await self.repo.adjust_quantity(item, adjustment_data.adjustment)
        return StockItemResponse.model_validate(updated)

    # ── Vendor association management ──────────────────────────────────────────

    async def link_vendor(
        self, item_id: uuid.UUID, data: LinkVendorToItemRequest
    ) -> StockItemDetailResponse:
        item = await self._get_or_404(item_id)

        vendor = await self.vendor_repo.get_by_id(data.vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", data.vendor_id)

        existing_link = await self.assoc_repo.get_link(item_id, data.vendor_id)
        if existing_link:
            raise DuplicateError(
                "StockItemVendor", "vendor_id", f"{data.vendor_id} for item {item_id}"
            )

        await self.assoc_repo.create_link(
            stock_item_id=item_id,
            vendor_id=data.vendor_id,
            vendor_sku=data.vendor_sku,
            vendor_price=float(data.vendor_price),
            lead_time_days=data.lead_time_days,
        )
        return await self.get_item_detail(item_id)

    async def unlink_vendor(self, item_id: uuid.UUID, vendor_id: uuid.UUID) -> None:
        await self._get_or_404(item_id)
        link = await self.assoc_repo.get_link(item_id, vendor_id)
        if not link:
            raise NotFoundError("StockItemVendor", f"{vendor_id} for item {item_id}")
        await self.assoc_repo.delete(link)

    async def update_vendor_link(
        self,
        item_id: uuid.UUID,
        vendor_id: uuid.UUID,
        data: UpdateVendorLinkRequest,
    ) -> StockItemDetailResponse:
        await self._get_or_404(item_id)
        link = await self.assoc_repo.get_link(item_id, vendor_id)
        if not link:
            raise NotFoundError("StockItemVendor", f"{vendor_id} for item {item_id}")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(link, field, value)
        await self.session.flush()

        return await self.get_item_detail(item_id)

    async def get_item_vendors(
        self, item_id: uuid.UUID
    ) -> list[StockItemVendorResponse]:
        detail = await self.get_item_detail(item_id)
        return detail.vendors

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_or_404(self, item_id: uuid.UUID) -> StockItem:
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise NotFoundError("StockItem", item_id)
        return item

    async def list_items_paginated(
        self, skip: int = 0, limit: int = 100, search: str | None = None
    ) -> tuple[list[StockItemResponse], int]:
        if search:
            items = await self.repo.search(search, skip=skip, limit=limit)
            # For search we do a full count with same filter — acceptable for screening project
            all_items = await self.repo.search(search, skip=0, limit=10_000)
            total = len(all_items)
        else:
            items = await self.repo.get_all_with_pagination(skip=skip, limit=limit)
            total = await self.repo.count_all()
        return [StockItemResponse.model_validate(i) for i in items], total

    async def get_item_by_sku(self, sku: str) -> StockItemDetailResponse:
        item = await self.repo.get_by_sku(sku)
        if not item:
            raise NotFoundError("StockItem", f"SKU={sku}")
        return await self.get_item_detail(item.id)
