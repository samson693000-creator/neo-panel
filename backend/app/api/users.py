from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_session
from app.models.models import Admin, AiRequest, AuditLog, BotUser
from app.schemas import GrantIn, UserListOut, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])

async def log(session: AsyncSession, admin: Admin, action: str, details: str) -> None:
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action=action,
            entity="user",
            details=details,
        )
    )

@router.get("", response_model=UserListOut)
async def list_users(
    q: str = "",
    status_filter: str = Query("all", alias="status"),
    page: int = 1,
    per_page: int = 25,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("support")),
) -> UserListOut:
    stmt = select(BotUser)
    if q:
        like = f"%{q}%"
        conditions = [
            BotUser.username.ilike(like),
            BotUser.first_name.ilike(like),
            BotUser.last_name.ilike(like),
        ]
        if q.isdigit():
            conditions.append(BotUser.telegram_id == int(q))
        stmt = stmt.where(or_(*conditions))

    if status_filter == "blocked":
        stmt = stmt.where(BotUser.is_blocked.is_(True))
    elif status_filter == "paid":
        stmt = stmt.where(
            or_(BotUser.paid_requests > 0, BotUser.is_unlimited.is_(True))
        )
    elif status_filter == "free":
        stmt = stmt.where(BotUser.paid_requests == 0, BotUser.is_unlimited.is_(False))

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    rows = await session.execute(
        stmt.order_by(BotUser.id.desc()).offset((page - 1) * per_page).limit(per_page)
    )

    return UserListOut(
        items=[UserOut.model_validate(u) for u in rows.scalars().all()],
        total=total,
        page=page,
        pages=max(1, ceil(total / per_page)),
    )

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("support")),
) -> dict:
    user = await session.get(BotUser, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")

    rows = await session.execute(
        select(AiRequest)
        .where(AiRequest.user_id == user_id)
        .order_by(AiRequest.id.desc())
        .limit(20)
    )
    history = [
        {
            "id": r.id,
            "prompt": r.prompt[:300],
            "answer": r.answer[:500],
            "tokens": r.tokens,
            "source": r.source,
            "is_error": r.is_error,
            "created_at": r.created_at,
        }
        for r in rows.scalars().all()
    ]
    return {"user": UserOut.model_validate(user), "history": history}

@router.post("/{user_id}/block")
async def block_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    user = await session.get(BotUser, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    user.is_blocked = not user.is_blocked
    await log(
        session,
        admin,
        "block" if user.is_blocked else "unblock",
        f"telegram_id={user.telegram_id}",
    )
    await session.commit()
    return {"ok": True, "is_blocked": user.is_blocked}

@router.post("/{user_id}/grant")
async def grant(
    user_id: int,
    data: GrantIn,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    user = await session.get(BotUser, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")

    if data.requests:
        user.paid_requests = max(0, user.paid_requests + data.requests)
    if data.unlimited is not None:
        user.is_unlimited = data.unlimited
    if data.days:
        base = user.tariff_expires_at or datetime.now(timezone.utc)
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        if base < datetime.now(timezone.utc):
            base = datetime.now(timezone.utc)
        user.tariff_expires_at = base + timedelta(days=data.days)
    if data.note is not None:
        user.note = data.note

    await log(
        session, admin, "grant", f"telegram_id={user.telegram_id} {data.model_dump()}"
    )
    await session.commit()
    await session.refresh(user)
    return {"ok": True, "user": UserOut.model_validate(user)}

@router.post("/{user_id}/reset-free")
async def reset_free(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    user = await session.get(BotUser, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    user.free_used = 0
    await log(session, admin, "reset_free", f"telegram_id={user.telegram_id}")
    await session.commit()
    return {"ok": True}

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("owner")),
) -> dict:
    user = await session.get(BotUser, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    await log(session, admin, "delete", f"telegram_id={user.telegram_id}")
    await session.delete(user)
    await session.commit()
    return {"ok": True}
