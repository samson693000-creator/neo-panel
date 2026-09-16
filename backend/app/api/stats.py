from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.bot.runner import bot_manager
from app.db.session import get_session
from app.models.models import Admin, AiRequest, AuditLog, BotUser, Payment
from app.schemas import DashboardOut
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("support")),
) -> DashboardOut:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    async def count(stmt) -> int:
        return await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    svc = SettingsService(session)

    revenue = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == "paid"
        )
    )

    return DashboardOut(
        users_total=await count(select(BotUser)),
        users_today=await count(select(BotUser).where(BotUser.created_at >= day_start)),
        users_active_7d=await count(select(BotUser).where(BotUser.last_seen >= week_ago)),
        blocked=await count(select(BotUser).where(BotUser.is_blocked.is_(True))),
        requests_total=await count(select(AiRequest)),
        requests_today=await count(
            select(AiRequest).where(AiRequest.created_at >= day_start)
        ),
        paid_users=await count(
            select(BotUser).where(
                or_(BotUser.paid_requests > 0, BotUser.is_unlimited.is_(True))
            )
        ),
        revenue_total=float(revenue or 0),
        bot_status=bot_manager.state()["status"],
        bot_username=bot_manager.state()["username"],
        ai_configured=bool(await svc.get("ai_api_key")),
        payments_configured=bool(
            await svc.get("cryptopay_token")
            or await svc.get("cryptomus_api_key")
            or await svc.get_bool("yoomoney_enabled", False)
        ),
    )

@router.get("/requests")
async def recent_requests(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("support")),
) -> list[dict]:
    rows = await session.execute(
        select(AiRequest, BotUser)
        .join(BotUser, BotUser.id == AiRequest.user_id)
        .order_by(AiRequest.id.desc())
        .limit(min(limit, 200))
    )
    return [
        {
            "id": r.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "prompt": r.prompt[:200],
            "tokens": r.tokens,
            "source": r.source,
            "is_error": r.is_error,
            "created_at": r.created_at,
        }
        for r, u in rows.all()
    ]

@router.get("/logs")
async def logs(
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> list[dict]:
    rows = await session.execute(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 300))
    )
    return [
        {
            "id": log.id,
            "admin": log.admin_name,
            "action": log.action,
            "entity": log.entity,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in rows.scalars().all()
    ]
