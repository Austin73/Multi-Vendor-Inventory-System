import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import StockItem
from app.repositories.base import BaseRepository
from app.schemas.stock_item import StockItemCreate, StockItemUpdate


class StockItemRepository(BaseRepository[StockItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(StockItem, session)

    async def get_by_sku(self, sku: str) -> StockItem | None:
        result = await self.session.execute(
            select(StockItem).where(StockItem.sku == sku.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_vendors(self, item_id: uuid.UUID) -> StockItem | None:
        result = await self.session.execute(
            select(StockItem)
            .options(
                selectinload(StockItem.vendor_links).selectinload(
                    StockItem.vendor_links.property.mapper.class_.vendor
                )
            )
            .where(StockItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: StockItemCreate) -> StockItem:
        item = StockItem(**data.model_dump())
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def update(self, item: StockItem, data: StockItemUpdate) -> StockItem:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def adjust_quantity(self, item: StockItem, adjustment: int) -> StockItem:
        item.quantity_on_hand += adjustment
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def get_all_with_pagination(
        self, skip: int = 0, limit: int = 100
    ) -> list[StockItem]:
        result = await self.session.execute(
            select(StockItem)
            .order_by(StockItem.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        from sqlalchemy import func
        result = await self.session.execute(select(func.count()).select_from(StockItem))
        return result.scalar_one()

    async def get_low_stock(self) -> list[StockItem]:
        """Return items where quantity_on_hand is at or below reorder_threshold."""
        result = await self.session.execute(
            select(StockItem)
            .where(StockItem.quantity_on_hand <= StockItem.reorder_threshold)
            .order_by(StockItem.quantity_on_hand.asc())
        )
        return list(result.scalars().all())

    async def search(self, query: str, skip: int = 0, limit: int = 100) -> list[StockItem]:
        """Case-insensitive search by name or SKU."""
        from sqlalchemy import or_
        pattern = f"%{query.upper()}%"
        result = await self.session.execute(
            select(StockItem)
            .where(
                or_(
                    StockItem.name.ilike(f"%{query}%"),
                    StockItem.sku.ilike(pattern),
                )
            )
            .order_by(StockItem.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
