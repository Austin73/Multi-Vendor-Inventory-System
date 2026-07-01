import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus
from app.schemas.vendor import VendorResponse


class PurchaseOrderLineCreate(BaseModel):
    stock_item_id: uuid.UUID
    quantity: int = Field(..., gt=0)


class PurchaseOrderCreate(BaseModel):
    vendor_id: uuid.UUID
    notes: str | None = None
    lines: list[PurchaseOrderLineCreate] = Field(..., min_length=1)


class PurchaseOrderStatusUpdate(BaseModel):
    status: OrderStatus


class PurchaseOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_item_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    vendor_id: uuid.UUID
    status: OrderStatus
    notes: str | None
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime


class PurchaseOrderDetailResponse(PurchaseOrderResponse):
    vendor: VendorResponse
    lines: list[PurchaseOrderLineResponse] = []
