import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    PUBLISHER = "PUBLISHER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    events = relationship("Event", back_populates="publisher")
    user_interests = relationship(
        "UserInterest",
        back_populates="user",
        cascade="all, delete-orphan",
        overlaps="users,interests",
    )
    interests = relationship(
        "Interest",
        secondary="user_interests",
        back_populates="users",
        viewonly=True,
        overlaps="user,interest,user_interests",
    )
