from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.bot.runner import bot_manager
from app.db.session import get_session
from app.models.models import Admin, AuditLog, Broadcast
from app.services import broadcast as bc

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])

@router.get("/audiences")
async def audiences(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> list[dict]:
    result = []
    for key, label in bc.AUDIENCES.items():
        result.append(
            {
                "key": key,
                "label": label,
                "count": await bc.count_audience(session, key),
            }
        )
    return result

@router.get("")
async def list_broadcasts(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> list[dict]:
    rows = await session.execute(
        select(Broadcast).order_by(Broadcast.id.desc()).limit(50)
    )
    return [
        {
            "id": b.id,
            "text": b.text,
            "audience": b.audience,
            "audience_label": bc.AUDIENCES.get(b.audience, b.audience),
            "status": b.status,
            "total": b.total,
            "sent": b.sent,
            "failed": b.failed,
            "created_at": b.created_at,
            "finished_at": b.finished_at,
            "running": bc.is_running(b.id),
        }
        for b in rows.scalars().all()
    ]

@router.post("")
async def create_broadcast(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    text = (payload.get("text") or "").strip()
    audience = payload.get("audience") or "all"
    send_now = bool(payload.get("send_now", True))

    if not text:
        raise HTTPException(400, "Текст рассылки пуст")
    if audience not in bc.AUDIENCES:
        raise HTTPException(400, "Неизвестная аудитория")
    if send_now and bot_manager.bot is None:
        raise HTTPException(400, "Бот не запущен — рассылка невозможна")

    item = Broadcast(text=text, audience=audience, status="draft")
    session.add(item)
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action="create_broadcast",
            entity="broadcast",
            details=f"audience={audience}",
        )
    )
    await session.commit()
    await session.refresh(item)

    if send_now:
        bc.start(item.id)

    return {"ok": True, "id": item.id, "started": send_now}

@router.post("/{broadcast_id}/start")
async def start_broadcast(
    broadcast_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    item = await session.get(Broadcast, broadcast_id)
    if item is None:
        raise HTTPException(404, "Рассылка не найдена")
    if bot_manager.bot is None:
        raise HTTPException(400, "Бот не запущен")
    started = bc.start(broadcast_id)
    return {"ok": started, "message": "Запущена" if started else "Уже выполняется"}

@router.post("/{broadcast_id}/cancel")
async def cancel_broadcast(
    broadcast_id: int,
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    cancelled = bc.cancel(broadcast_id)
    return {
        "ok": cancelled,
        "message": "Останавливаю" if cancelled else "Не выполняется",
    }

@router.delete("/{broadcast_id}")
async def delete_broadcast(
    broadcast_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    item = await session.get(Broadcast, broadcast_id)
    if item is None:
        raise HTTPException(404, "Рассылка не найдена")
    if bc.is_running(broadcast_id):
        raise HTTPException(400, "Сначала остановите рассылку")
    await session.delete(item)
    await session.commit()
    return {"ok": True}
