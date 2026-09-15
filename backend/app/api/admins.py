from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.security import hash_password
from app.db.session import get_session
from app.models.models import Admin, AuditLog

router = APIRouter(prefix="/api/admins", tags=["admins"])

ROLES = ("owner", "admin", "support")

@router.get("")
async def list_admins(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("owner")),
) -> list[dict]:
    rows = await session.execute(select(Admin).order_by(Admin.id))
    return [
        {
            "id": a.id,
            "username": a.username,
            "role": a.role,
            "is_active": a.is_active,
            "created_at": a.created_at,
            "last_login": a.last_login,
        }
        for a in rows.scalars().all()
    ]

@router.post("")
async def create_admin(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("owner")),
) -> dict:
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    role = payload.get("role") or "support"

    if len(username) < 3:
        raise HTTPException(400, "Логин минимум 3 символа")
    if len(password) < 8:
        raise HTTPException(400, "Пароль минимум 8 символов")
    if role not in ROLES:
        raise HTTPException(400, "Недопустимая роль")

    exists = await session.scalar(select(Admin.id).where(Admin.username == username))
    if exists:
        raise HTTPException(400, "Такой логин уже существует")

    session.add(
        Admin(username=username, password_hash=hash_password(password), role=role)
    )
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action="create_admin",
            entity="admin",
            details=f"{username}/{role}",
        )
    )
    await session.commit()
    return {"ok": True}

@router.put("/{admin_id}")
async def update_admin(
    admin_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("owner")),
) -> dict:
    target = await session.get(Admin, admin_id)
    if target is None:
        raise HTTPException(404, "Администратор не найден")

    role = payload.get("role")
    if role:
        if role not in ROLES:
            raise HTTPException(400, "Недопустимая роль")
        if target.id == admin.id and role != "owner":
            raise HTTPException(400, "Нельзя понизить собственную роль")
        target.role = role

    if "is_active" in payload:
        if target.id == admin.id and not payload["is_active"]:
            raise HTTPException(400, "Нельзя отключить свою учётную запись")
        target.is_active = bool(payload["is_active"])

    password = payload.get("password")
    if password:
        if len(password) < 8:
            raise HTTPException(400, "Пароль минимум 8 символов")
        target.password_hash = hash_password(password)

    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action="update_admin",
            entity="admin",
            details=target.username,
        )
    )
    await session.commit()
    return {"ok": True}

@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("owner")),
) -> dict:
    target = await session.get(Admin, admin_id)
    if target is None:
        raise HTTPException(404, "Администратор не найден")
    if target.id == admin.id:
        raise HTTPException(400, "Нельзя удалить себя")

    owners = await session.execute(select(Admin.id).where(Admin.role == "owner"))
    owner_ids = list(owners.scalars().all())
    if target.role == "owner" and len(owner_ids) <= 1:
        raise HTTPException(400, "Должен остаться хотя бы один владелец")

    await session.delete(target)
    await session.commit()
    return {"ok": True}
