import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import VendorStatus


class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = None
    address: str | None = None
    status: VendorStatus | None = None


class StockItemBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str


class VendorStockLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock_item: StockItemBriefResponse
    vendor_sku: str | None
    vendor_price: float
    lead_time_days: int


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone: str | None
    address: str | None
    status: VendorStatus
    created_at: datetime
    updated_at: datetime


class VendorDetailResponse(VendorResponse):
    stock_items: list[VendorStockLinkResponse] = []
