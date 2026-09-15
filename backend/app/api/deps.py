from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_session
from app.models.models import Admin

bearer = HTTPBearer(auto_error=False)

ROLES = {"support": 1, "admin": 2, "owner": 3}

async def current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> Admin:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен")
    result = await session.execute(
        select(Admin).where(Admin.username == payload.get("sub"))
    )
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Администратор не найден")
    return admin

def require_role(minimum: str):
    async def checker(admin: Admin = Depends(current_admin)) -> Admin:
        if ROLES.get(admin.role, 0) < ROLES[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return admin

    return checker
