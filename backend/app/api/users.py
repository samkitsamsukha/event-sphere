from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, get_current_user
from app.models.interest import Interest, UserInterest
from app.models.user import User
from app.schemas.user import (
    InterestRequest,
    InterestResponse,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


async def _load_user(user_id: int, db: DbSession) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.interests)).where(User.id == user_id)
    )
    user = result.scalar_one()
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return await _load_user(current_user.id, db)


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdateRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        updates["email"] = str(payload.email).lower()
        existing = await db.execute(
            select(User).where(User.email == updates["email"], User.id != current_user.id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

    for field, value in updates.items():
        setattr(current_user, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from None
    return await _load_user(current_user.id, db)


@router.get("/me/interests", response_model=list[InterestResponse])
async def list_my_interests(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Interest]:
    user = await _load_user(current_user.id, db)
    return list(user.interests)


@router.post(
    "/me/interests",
    response_model=InterestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_interest(
    payload: InterestRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Interest:
    if payload.interest_id is None and payload.name is None:
        raise HTTPException(status_code=422, detail="interest_id or name is required")

    if payload.interest_id is not None:
        interest = await db.get(Interest, payload.interest_id)
        if interest is None:
            raise HTTPException(status_code=404, detail="Interest not found")
    else:
        result = await db.execute(select(Interest).where(Interest.name == payload.name))
        interest = result.scalar_one_or_none()
        if interest is None:
            if payload.category is None:
                raise HTTPException(
                    status_code=422, detail="category is required for a new interest"
                )
            interest = Interest(name=payload.name, category=payload.category)
            db.add(interest)
            await db.flush()

    existing = await db.execute(
        select(UserInterest).where(
            UserInterest.user_id == current_user.id,
            UserInterest.interest_id == interest.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Interest already added")

    db.add(UserInterest(user_id=current_user.id, interest_id=interest.id))
    await db.commit()
    return interest


@router.delete("/me/interests/{interest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_interest(
    interest_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    result = await db.execute(
        select(UserInterest).where(
            UserInterest.user_id == current_user.id,
            UserInterest.interest_id == interest_id,
        )
    )
    user_interest = result.scalar_one_or_none()
    if user_interest is None:
        raise HTTPException(status_code=404, detail="Interest not found for user")
    await db.delete(user_interest)
    await db.commit()
