import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockItemVendor
from app.repositories.base import BaseRepository


class AssociationRepository(BaseRepository[StockItemVendor]):
    def __init__(self, session: AsyncSession):
        super().__init__(StockItemVendor, session)

    async def get_link(
        self, stock_item_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> StockItemVendor | None:
        result = await self.session.execute(
            select(StockItemVendor).where(
                StockItemVendor.stock_item_id == stock_item_id,
                StockItemVendor.vendor_id == vendor_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_vendors_for_item(
        self, stock_item_id: uuid.UUID
    ) -> list[StockItemVendor]:
        result = await self.session.execute(
            select(StockItemVendor).where(
                StockItemVendor.stock_item_id == stock_item_id
            )
        )
        return list(result.scalars().all())

    async def create_link(
        self,
        stock_item_id: uuid.UUID,
        vendor_id: uuid.UUID,
        vendor_sku: str | None,
        vendor_price: float,
        lead_time_days: int,
    ) -> StockItemVendor:
        link = StockItemVendor(
            stock_item_id=stock_item_id,
            vendor_id=vendor_id,
            vendor_sku=vendor_sku,
            vendor_price=vendor_price,
            lead_time_days=lead_time_days,
        )
        self.session.add(link)
        await self.session.flush()
        await self.session.refresh(link)
        return link
