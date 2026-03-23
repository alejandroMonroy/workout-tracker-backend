from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import SexType, UnitsPreference, UserRole


# --- Request schemas ---


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.ATHLETE


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRefresh(BaseModel):
    refresh_token: str


class UserProfileUpdate(BaseModel):
    name: str | None = None
    units_preference: UnitsPreference | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=500)
    sex: SexType | None = None


# --- Response schemas ---


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    avatar_url: str | None = None
    units_preference: UnitsPreference
    birth_date: date | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    sex: SexType | None = None
    total_xp: int = 0
    level: int = 1
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse
