import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.interactions import router as interactions_router
from app.api.recommendations import router as recommendations_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging
from app.db.session import engine

configure_logging()
app = FastAPI(title="EventSphere API", version="0.1.0")
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(interactions_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/db")
async def database_health():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logging.getLogger("eventsphere.health").exception("Database health check failed")
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return {"status": "ok"}
