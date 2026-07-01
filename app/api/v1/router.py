from fastapi import APIRouter

from app.api.v1.endpoints import purchase_orders, stock_items, vendors

api_router = APIRouter()

api_router.include_router(stock_items.router)
api_router.include_router(vendors.router)
api_router.include_router(purchase_orders.router)
