import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import Vendor
from app.repositories.base import BaseRepository
from app.schemas.vendor import VendorCreate, VendorUpdate


class VendorRepository(BaseRepository[Vendor]):
    def __init__(self, session: AsyncSession):
        super().__init__(Vendor, session)

    async def get_by_email(self, email: str) -> Vendor | None:
        result = await self.session.execute(
            select(Vendor).where(Vendor.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_items(self, vendor_id: uuid.UUID) -> Vendor | None:
        result = await self.session.execute(
            select(Vendor)
            .options(
                selectinload(Vendor.stock_links).selectinload(
                    Vendor.stock_links.property.mapper.class_.stock_item
                )
            )
            .where(Vendor.id == vendor_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: VendorCreate) -> Vendor:
        vendor_data = data.model_dump()
        vendor_data["email"] = vendor_data["email"].lower()
        vendor = Vendor(**vendor_data)
        self.session.add(vendor)
        await self.session.flush()
        await self.session.refresh(vendor)
        return vendor

    async def update(self, vendor: Vendor, data: VendorUpdate) -> Vendor:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vendor, field, value)
        await self.session.flush()
        await self.session.refresh(vendor)
        return vendor

    async def get_all_with_pagination(
        self, skip: int = 0, limit: int = 100
    ) -> list[Vendor]:
        result = await self.session.execute(
            select(Vendor).order_by(Vendor.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        from sqlalchemy import func
        result = await self.session.execute(select(func.count()).select_from(Vendor))
        return result.scalar_one()
