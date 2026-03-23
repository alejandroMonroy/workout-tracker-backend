from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import AuthResponse, TokenResponse, UserRegister, UserResponse


async def register_user(db: AsyncSession, data: UserRegister) -> AuthResponse:
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ValueError("El email ya está registrado")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    tokens = _create_tokens(user.id)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def login_user(db: AsyncSession, email: str, password: str) -> AuthResponse:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Email o contraseña incorrectos")

    tokens = _create_tokens(user.id)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise ValueError("Token de refresco inválido")

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Token de refresco inválido")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("Usuario no encontrado")

    return _create_tokens(user.id)


def _create_tokens(user_id: int) -> TokenResponse:
    token_data = {"sub": str(user_id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
