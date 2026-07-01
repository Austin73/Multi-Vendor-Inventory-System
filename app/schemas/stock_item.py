import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    reorder_threshold: int = Field(default=10, ge=0)


class StockItemCreate(StockItemBase):
    sku: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9\-_]+$")

    @field_validator("sku")
    @classmethod
    def sku_to_upper(cls, v: str) -> str:
        return v.upper()


class StockItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    reorder_threshold: int | None = Field(default=None, ge=0)


class StockItemAdjustQuantity(BaseModel):
    adjustment: int = Field(..., description="Positive to add, negative to remove stock.")
    reason: str | None = Field(default=None, max_length=500)


class VendorBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str


class StockItemVendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor: VendorBriefResponse
    vendor_sku: str | None
    vendor_price: Decimal
    lead_time_days: int


class StockItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    quantity_on_hand: int
    reorder_threshold: int
    unit_price: Decimal
    created_at: datetime
    updated_at: datetime


class StockItemDetailResponse(StockItemResponse):
    vendors: list[StockItemVendorResponse] = []
