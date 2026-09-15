from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.bot.runner import bot_manager
from app.db.session import get_session
from app.models.models import Admin, AuditLog
from app.schemas import SettingsIn
from app.services.ai import check_ai_connection
from app.services.settings_service import SECRET_KEYS, SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("")
async def read_settings(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    svc = SettingsService(session)
    return {
        "values": await svc.masked(),
        "secret_keys": sorted(SECRET_KEYS),
        "secret_filled": await svc.secret_status(),
    }

@router.put("")
async def update_settings(
    data: SettingsIn,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    svc = SettingsService(session)
    clean = {
        key: value
        for key, value in data.values.items()
        if not (key in SECRET_KEYS and "****" in str(value))
    }
    await svc.set_many(clean)
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action="update",
            entity="settings",
            details=", ".join(sorted(clean.keys()))[:500],
        )
    )
    await session.commit()
    return {"ok": True, "values": await svc.masked()}

@router.get("/bot/status")
async def bot_status(admin: Admin = Depends(require_role("admin"))) -> dict:
    return bot_manager.state()

@router.post("/bot/start")
async def bot_start(admin: Admin = Depends(require_role("admin"))) -> dict:
    ok, message = await bot_manager.start()
    return {"ok": ok, "message": message, "state": bot_manager.state()}

@router.post("/bot/stop")
async def bot_stop(admin: Admin = Depends(require_role("admin"))) -> dict:
    ok, message = await bot_manager.stop()
    return {"ok": ok, "message": message, "state": bot_manager.state()}

@router.post("/bot/restart")
async def bot_restart(admin: Admin = Depends(require_role("admin"))) -> dict:
    ok, message = await bot_manager.restart()
    return {"ok": ok, "message": message, "state": bot_manager.state()}

@router.post("/ai/test")
async def ai_test(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    ok, message = await check_ai_connection(session)
    return {"ok": ok, "message": message}
