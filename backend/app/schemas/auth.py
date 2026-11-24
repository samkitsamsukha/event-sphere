from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CUSTOMER

    @field_validator("role")
    @classmethod
    def reject_admin_registration(cls, value: UserRole) -> UserRole:
        if value == UserRole.ADMIN:
            raise ValueError("Admin accounts must be provisioned by an administrator")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
