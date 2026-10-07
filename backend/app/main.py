from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.core.config import settings
from app.api.events import router as events_router
from app.api.interactions import router as interactions_router
from app.api.recommendations import router as recommendations_router
from app.api.users import router as users_router

app = FastAPI(title="EventSphere API", version="0.1.0")
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
