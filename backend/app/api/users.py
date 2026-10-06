from fastapi import APIRouter

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse
from fastapi import Depends

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
