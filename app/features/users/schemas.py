from typing import Literal
from pydantic import BaseModel, EmailStr, Field, model_validator


UserRole = Literal["customer", "support_agent", "admin", "supervisor"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    department: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def normalize_department(self) -> "UserCreate":
        if self.role in ("support_agent", "supervisor"):
            raw = (self.department or "").strip()
            if len(raw) < 1:
                raise ValueError("Department is required for support agents and supervisors")
            self.department = raw[:80]
        else:
            self.department = ""
        return self


class UserResponse(BaseModel):
    id: int
    tenant_id: str
    full_name: str
    email: EmailStr
    role: UserRole
    department: str = ""
    is_active: int


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserStatusUpdate(BaseModel):
    is_active: int = Field(ge=0, le=1)


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserAdminUpdate(BaseModel):
    """Partial update for admin user management."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    role: UserRole | None = None
    department: str | None = Field(default=None, max_length=80)
    is_active: int | None = Field(default=None, ge=0, le=1)
