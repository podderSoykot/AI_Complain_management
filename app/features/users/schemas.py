from typing import Literal
from pydantic import BaseModel, EmailStr, Field


UserRole = Literal["customer", "support_agent", "admin", "supervisor"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UserResponse(BaseModel):
    id: int
    tenant_id: str
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: int


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
