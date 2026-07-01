import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import OrderStatus, VendorStatus
from app.models.inventory import PurchaseOrder
from app.repositories.association import AssociationRepository
from app.repositories.purchase_order import PurchaseOrderRepository
from app.repositories.stock_item import StockItemRepository
from app.repositories.vendor import VendorRepository
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderDetailResponse,
    PurchaseOrderLineResponse,
    PurchaseOrderResponse,
    PurchaseOrderStatusUpdate,
)
from app.schemas.vendor import VendorResponse

# Define which status transitions are allowed
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.SUBMITTED, OrderStatus.CANCELLED},
    OrderStatus.SUBMITTED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.RECEIVED, OrderStatus.CANCELLED},
    OrderStatus.RECEIVED: set(),
    OrderStatus.CANCELLED: set(),
}


class PurchaseOrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PurchaseOrderRepository(session)
        self.vendor_repo = VendorRepository(session)
        self.stock_repo = StockItemRepository(session)
        self.assoc_repo = AssociationRepository(session)

    async def create_order(self, data: PurchaseOrderCreate) -> PurchaseOrderDetailResponse:
        # 1. Validate vendor exists and is active
        vendor = await self.vendor_repo.get_by_id(data.vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", data.vendor_id)
        if vendor.status != VendorStatus.ACTIVE:
            raise BusinessRuleError(
                f"Vendor '{vendor.name}' is not active (status: {vendor.status.value}). "
                "Only active vendors can be used for purchase orders."
            )

        # 2. Validate each line item
        order_lines_data = []
        for line in data.lines:
            stock_item = await self.stock_repo.get_by_id(line.stock_item_id)
            if not stock_item:
                raise NotFoundError("StockItem", line.stock_item_id)

            # Core business rule: vendor must be linked to this stock item
            link = await self.assoc_repo.get_link(line.stock_item_id, data.vendor_id)
            if not link:
                raise BusinessRuleError(
                    f"Vendor '{vendor.name}' is not an approved supplier for "
                    f"item '{stock_item.name}' (SKU: {stock_item.sku}). "
                    "Please link the vendor to this item before ordering."
                )

            order_lines_data.append(
                {
                    "stock_item_id": line.stock_item_id,
                    "quantity": line.quantity,
                    "unit_price": link.vendor_price,  # Use the agreed vendor price
                }
            )

        # 3. Create the order
        order = await self.repo.create(vendor_id=data.vendor_id, notes=data.notes)

        # 4. Add line items and compute total
        total = Decimal("0.00")
        for line_data in order_lines_data:
            await self.repo.add_line(
                order=order,
                stock_item_id=line_data["stock_item_id"],
                quantity=line_data["quantity"],
                unit_price=float(line_data["unit_price"]),
            )
            total += Decimal(str(line_data["unit_price"])) * line_data["quantity"]

        order.total_amount = total
        await self.session.flush()

        return await self.get_order_detail(order.id)

    async def get_order(self, order_id: uuid.UUID) -> PurchaseOrderResponse:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("PurchaseOrder", order_id)
        return PurchaseOrderResponse.model_validate(order)

    async def get_order_detail(self, order_id: uuid.UUID) -> PurchaseOrderDetailResponse:
        order = await self.repo.get_by_id_with_details(order_id)
        if not order:
            raise NotFoundError("PurchaseOrder", order_id)
        return self._build_detail_response(order)

    async def list_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        vendor_id: uuid.UUID | None = None,
    ) -> list[PurchaseOrderResponse]:
        orders = await self.repo.get_all_with_pagination(
            skip=skip, limit=limit, vendor_id=vendor_id
        )
        return [PurchaseOrderResponse.model_validate(o) for o in orders]

    async def update_status(
        self, order_id: uuid.UUID, data: PurchaseOrderStatusUpdate
    ) -> PurchaseOrderDetailResponse:
        order = await self._get_or_404(order_id)

        allowed_next = VALID_TRANSITIONS.get(order.status, set())
        if data.status not in allowed_next:
            raise BusinessRuleError(
                f"Cannot transition order from '{order.status.value}' to "
                f"'{data.status.value}'. "
                f"Allowed transitions: {[s.value for s in allowed_next] or 'none (terminal state)'}."
            )

        order.status = data.status
        await self.session.flush()

        return await self.get_order_detail(order_id)

    async def cancel_order(self, order_id: uuid.UUID) -> PurchaseOrderDetailResponse:
        return await self.update_status(
            order_id, PurchaseOrderStatusUpdate(status=OrderStatus.CANCELLED)
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_or_404(self, order_id: uuid.UUID) -> PurchaseOrder:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("PurchaseOrder", order_id)
        return order

    @staticmethod
    def _build_detail_response(order: PurchaseOrder) -> PurchaseOrderDetailResponse:
        lines = [
            PurchaseOrderLineResponse(
                id=line.id,
                stock_item_id=line.stock_item_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )
            for line in order.lines
        ]
        return PurchaseOrderDetailResponse(
            id=order.id,
            order_number=order.order_number,
            vendor_id=order.vendor_id,
            status=order.status,
            notes=order.notes,
            total_amount=order.total_amount,
            created_at=order.created_at,
            updated_at=order.updated_at,
            vendor=VendorResponse.model_validate(order.vendor),
            lines=lines,
        )

    async def list_orders_paginated(
        self,
        skip: int = 0,
        limit: int = 100,
        vendor_id: uuid.UUID | None = None,
    ) -> tuple[list[PurchaseOrderResponse], int]:
        orders = await self.repo.get_all_with_pagination(
            skip=skip, limit=limit, vendor_id=vendor_id
        )
        total = await self.repo.count_all(vendor_id=vendor_id)
        return [PurchaseOrderResponse.model_validate(o) for o in orders], total
