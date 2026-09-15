import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.bot.runner import bot_manager
from app.db.session import SessionLocal
from app.models.models import BotUser, Broadcast

logger = logging.getLogger("broadcast")

AUDIENCES = {
    "all": "Все пользователи",
    "paid": "Платные клиенты",
    "free": "Без оплаты",
    "unlimited": "Безлимит",
    "active_7d": "Активные за 7 дней",
    "blocked": "Заблокированные",
}

_tasks: dict[int, asyncio.Task] = {}
_cancelled: set[int] = set()

def audience_filter(audience: str):
    now = datetime.now(timezone.utc)
    if audience == "paid":
        return [
            or_(BotUser.paid_requests > 0, BotUser.is_unlimited.is_(True)),
            BotUser.is_blocked.is_(False),
        ]
    if audience == "free":
        return [
            BotUser.paid_requests == 0,
            BotUser.is_unlimited.is_(False),
            BotUser.is_blocked.is_(False),
        ]
    if audience == "unlimited":
        return [BotUser.is_unlimited.is_(True), BotUser.is_blocked.is_(False)]
    if audience == "active_7d":
        return [
            BotUser.last_seen >= now - timedelta(days=7),
            BotUser.is_blocked.is_(False),
        ]
    if audience == "blocked":
        return [BotUser.is_blocked.is_(True)]
    return [BotUser.is_blocked.is_(False)]

async def count_audience(session, audience: str) -> int:
    rows = await session.execute(select(BotUser.id).where(*audience_filter(audience)))
    return len(rows.scalars().all())

async def _run(broadcast_id: int) -> None:
    async with SessionLocal() as session:
        broadcast = await session.get(Broadcast, broadcast_id)
        if broadcast is None:
            return

        rows = await session.execute(
            select(BotUser.telegram_id).where(*audience_filter(broadcast.audience))
        )
        targets = list(rows.scalars().all())

        broadcast.status = "running"
        broadcast.total = len(targets)
        broadcast.sent = 0
        broadcast.failed = 0
        await session.commit()

        bot = bot_manager.bot
        if bot is None:
            broadcast.status = "error"
            broadcast.finished_at = datetime.now(timezone.utc)
            await session.commit()
            return

        for index, telegram_id in enumerate(targets, start=1):
            if broadcast_id in _cancelled:
                broadcast.status = "cancelled"
                break
            try:
                await bot.send_message(telegram_id, broadcast.text)
                broadcast.sent += 1
            except Exception as exc:
                broadcast.failed += 1
                logger.debug("send fail %s: %s", telegram_id, exc)

            if index % 20 == 0:
                await session.commit()
            await asyncio.sleep(0.06)

        if broadcast.status == "running":
            broadcast.status = "done"
        broadcast.finished_at = datetime.now(timezone.utc)
        await session.commit()

    _cancelled.discard(broadcast_id)
    _tasks.pop(broadcast_id, None)

def start(broadcast_id: int) -> bool:
    if broadcast_id in _tasks and not _tasks[broadcast_id].done():
        return False
    _tasks[broadcast_id] = asyncio.create_task(_run(broadcast_id))
    return True

def cancel(broadcast_id: int) -> bool:
    if broadcast_id in _tasks and not _tasks[broadcast_id].done():
        _cancelled.add(broadcast_id)
        return True
    return False

def is_running(broadcast_id: int) -> bool:
    task = _tasks.get(broadcast_id)
    return task is not None and not task.done()
