from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models.models import Admin
from app.schemas import AccountUpdate, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    result = await session.execute(select(Admin).where(Admin.username == data.username))
    admin = result.scalar_one_or_none()
    if admin is None or not verify_password(data.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")
    if not admin.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись отключена")

    admin.last_login = datetime.now(timezone.utc)
    await session.commit()

    return TokenResponse(
        access_token=create_access_token(admin.username, admin.role),
        username=admin.username,
        role=admin.role,
    )


@router.get("/me")
async def me(admin: Admin = Depends(current_admin)) -> dict:
    return {
        "username": admin.username,
        "role": admin.role,
        "last_login": admin.last_login,
    }


@router.post("/password")
async def change_password(
    payload: dict,
    admin: Admin = Depends(current_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    old = payload.get("old_password", "")
    new = payload.get("new_password", "")
    if not verify_password(old, admin.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль неверен")
    if len(new) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Минимум 8 символов")
    admin.password_hash = hash_password(new)
    await session.commit()
    return {"ok": True}


@router.post("/account", response_model=TokenResponse)
async def update_account(
    data: AccountUpdate,
    admin: Admin = Depends(current_admin),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    if not verify_password(data.old_password, admin.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль неверен")

    new_username = (data.new_username or "").strip()
    new_password = data.new_password or ""

    if not new_username and not new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Укажите новый логин или пароль")

    if new_username:
        if len(new_username) < 3:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Логин минимум 3 символа")
        taken = await session.scalar(
            select(Admin.id).where(
                Admin.username == new_username, Admin.id != admin.id
            )
        )
        if taken:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Такой логин уже существует")
        admin.username = new_username

    if new_password:
        if len(new_password) < 8:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пароль минимум 8 символов")
        admin.password_hash = hash_password(new_password)

    await session.commit()
    await session.refresh(admin)
    return TokenResponse(
        access_token=create_access_token(admin.username, admin.role),
        username=admin.username,
        role=admin.role,
    )
