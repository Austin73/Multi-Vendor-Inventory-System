import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class LinkVendorToItemRequest(BaseModel):
    vendor_id: uuid.UUID
    vendor_sku: str | None = Field(default=None, max_length=100)
    vendor_price: Decimal = Field(..., ge=0, decimal_places=2)
    lead_time_days: int = Field(default=7, ge=1)


class UpdateVendorLinkRequest(BaseModel):
    vendor_sku: str | None = None
    vendor_price: Decimal | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=1)
