from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.users import router as users_router

app = FastAPI(title="EventSphere API", version="0.1.0")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(events_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
