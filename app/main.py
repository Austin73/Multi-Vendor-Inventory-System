from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.db.session import AsyncSessionLocal


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "A backend service to manage product inventory with many-to-many "
            "vendor relationships and a flexible purchase order flow.\n\n"
            "**Quick start:**\n"
            "1. Create stock items\n"
            "2. Create vendors\n"
            "3. Link vendors to items (sets agreed price + lead time)\n"
            "4. Create purchase orders — only linked vendors are valid choices"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handlers ──────────────────────────────────────────────
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DuplicateError)
    async def duplicate_handler(request: Request, exc: DuplicateError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(BusinessRuleError)
    async def business_rule_handler(request: Request, exc: BusinessRuleError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    # ── Routes ─────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["Health"], summary="Health check with DB connectivity")
    async def health_check():
        """
        Returns service status and verifies database connectivity.
        A `db` status of `"ok"` means the database is reachable.
        """
        db_status = "ok"
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            db_status = "unavailable"

        http_status = status.HTTP_200_OK if db_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(
            status_code=http_status,
            content={
                "status": "ok" if db_status == "ok" else "degraded",
                "version": settings.APP_VERSION,
                "database": db_status,
            },
        )

    return app


app = create_application()
