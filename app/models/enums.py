import enum


class VendorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    RECEIVED = "received"
    CANCELLED = "cancelled"
