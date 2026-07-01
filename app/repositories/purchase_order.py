import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import PurchaseOrder, PurchaseOrderLine
from app.repositories.base import BaseRepository


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    def __init__(self, session: AsyncSession):
        super().__init__(PurchaseOrder, session)

    async def get_by_order_number(self, order_number: str) -> PurchaseOrder | None:
        result = await self.session.execute(
            select(PurchaseOrder).where(PurchaseOrder.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_details(self, order_id: uuid.UUID) -> PurchaseOrder | None:
        result = await self.session.execute(
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.lines).selectinload(
                    PurchaseOrderLine.stock_item
                ),
            )
            .where(PurchaseOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        vendor_id: uuid.UUID,
        notes: str | None,
    ) -> PurchaseOrder:
        order_number = self._generate_order_number()
        order = PurchaseOrder(
            order_number=order_number,
            vendor_id=vendor_id,
            notes=notes,
        )
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        return order

    async def add_line(
        self,
        order: PurchaseOrder,
        stock_item_id: uuid.UUID,
        quantity: int,
        unit_price: float,
    ) -> PurchaseOrderLine:
        line = PurchaseOrderLine(
            purchase_order_id=order.id,
            stock_item_id=stock_item_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        self.session.add(line)
        await self.session.flush()
        return line

    async def get_all_with_pagination(
        self,
        skip: int = 0,
        limit: int = 100,
        vendor_id: uuid.UUID | None = None,
    ) -> list[PurchaseOrder]:
        query = (
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.vendor))
            .order_by(PurchaseOrder.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if vendor_id:
            query = query.where(PurchaseOrder.vendor_id == vendor_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def _generate_order_number() -> str:
        """Generate a human-readable, time-based order number."""
        now = datetime.now(UTC)
        return f"PO-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S%f')[:10]}"

    async def count_all(self, vendor_id=None) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(PurchaseOrder)
        if vendor_id:
            query = query.where(PurchaseOrder.vendor_id == vendor_id)
        result = await self.session.execute(query)
        return result.scalar_one()
