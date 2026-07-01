import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import OrderStatus, VendorStatus


class StockItem(BaseModel):
    """Represents a unique product/item in the inventory."""

    __tablename__ = "stock_items"

    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="ck_stock_items_qty_non_negative"),
        CheckConstraint("unit_price >= 0", name="ck_stock_items_price_non_negative"),
    )

    # Relationships
    vendor_links: Mapped[list["StockItemVendor"]] = relationship(
        "StockItemVendor", back_populates="stock_item", cascade="all, delete-orphan"
    )
    purchase_order_lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="stock_item"
    )

    def __repr__(self) -> str:
        return f"<StockItem sku={self.sku!r} name={self.name!r}>"


class Vendor(BaseModel):
    """Represents a supplier/vendor."""

    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VendorStatus] = mapped_column(
        Enum(VendorStatus, name="vendor_status"), default=VendorStatus.ACTIVE, nullable=False
    )

    # Relationships
    stock_links: Mapped[list["StockItemVendor"]] = relationship(
        "StockItemVendor", back_populates="vendor", cascade="all, delete-orphan"
    )
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="vendor"
    )

    def __repr__(self) -> str:
        return f"<Vendor name={self.name!r} email={self.email!r}>"


class StockItemVendor(BaseModel):
    """
    Association table linking StockItems to Vendors (many-to-many).
    Stores vendor-specific pricing and lead time for a given item.
    """

    __tablename__ = "stock_item_vendors"

    stock_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vendor_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)

    __table_args__ = (
        UniqueConstraint("stock_item_id", "vendor_id", name="uq_stock_item_vendor"),
        CheckConstraint("vendor_price >= 0", name="ck_siv_vendor_price_non_negative"),
    )

    # Relationships
    stock_item: Mapped["StockItem"] = relationship("StockItem", back_populates="vendor_links")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="stock_links")

    def __repr__(self) -> str:
        return f"<StockItemVendor stock_item_id={self.stock_item_id} vendor_id={self.vendor_id}>"


class PurchaseOrder(BaseModel):
    """Represents a purchase order placed with a specific vendor."""

    __tablename__ = "purchase_orders"

    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.DRAFT,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="purchase_orders")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrder order_number={self.order_number!r} status={self.status}>"


class PurchaseOrderLine(BaseModel):
    """A line item within a purchase order."""

    __tablename__ = "purchase_order_lines"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pol_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_pol_unit_price_non_negative"),
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder", back_populates="lines"
    )
    stock_item: Mapped["StockItem"] = relationship(
        "StockItem", back_populates="purchase_order_lines"
    )

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    def __repr__(self) -> str:
        return (
            f"<PurchaseOrderLine po_id={self.purchase_order_id} "
            f"item_id={self.stock_item_id} qty={self.quantity}>"
        )
