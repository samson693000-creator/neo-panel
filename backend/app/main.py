import logging
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.api import (
    admins,
    auth,
    backup,
    broadcasts,
    payments,
    settings as settings_api,
    stats,
    tariffs,
    users,
    webhooks,
)
from app.bot.runner import bot_manager
from app.core.config import settings
from app.core.security import hash_password
from app.db.migrate import patch_schema
from app.db.session import SessionLocal, engine
from app.models.models import Admin, Base, Tariff
from app.services.settings_service import SettingsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await patch_schema(engine)


async def seed() -> None:
    async with SessionLocal() as session:
        await SettingsService(session).seed_defaults()

        exists = await session.scalar(select(Admin.id).limit(1))
        if exists is None:
            session.add(
                Admin(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    role="owner",
                )
            )
            logger.info("Создан администратор: %s", settings.admin_username)

        has_tariffs = await session.scalar(select(Tariff.id).limit(1))
        if has_tariffs is None:
            session.add_all(
                [
                    Tariff(
                        name="Старт",
                        description="100 запросов",
                        price=5,
                        currency="USDT",
                        requests=100,
                        sort_order=1,
                    ),
                    Tariff(
                        name="Стандарт",
                        description="500 запросов",
                        price=15,
                        currency="USDT",
                        requests=500,
                        sort_order=2,
                    ),
                    Tariff(
                        name="Безлимит 30 дней",
                        description="Без ограничений",
                        price=30,
                        currency="USDT",
                        is_unlimited=True,
                        duration_days=30,
                        sort_order=3,
                    ),
                ]
            )
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed()
    async with SessionLocal() as session:
        auto = await SettingsService(session).get_bool("bot_enabled", False)
    if auto:
        await bot_manager.start()

    async def yoomoney_loop() -> None:
        from app.services.payments.yoomoney import poll_pending_yoomoney

        await asyncio.sleep(8)
        while True:
            try:
                await poll_pending_yoomoney()
            except Exception:
                logger.exception("YooMoney poller")
            await asyncio.sleep(45)

    poller = asyncio.create_task(yoomoney_loop())
    yield
    poller.cancel()
    await bot_manager.stop()
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = settings.cors_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admins.router)
app.include_router(users.router)
app.include_router(tariffs.router)
app.include_router(payments.router)
app.include_router(broadcasts.router)
app.include_router(settings_api.router)
app.include_router(stats.router)
app.include_router(webhooks.router)
app.include_router(backup.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "bot": bot_manager.state()}


def _mount_frontend() -> None:
    if not DIST.is_dir():
        logger.warning("Админка не собрана: нет %s. Запусти python install.py", DIST)
        return
    assets = DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(404, "Not found")
        candidate = DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = DIST / "index.html"
        if not index.is_file():
            raise HTTPException(404, "Админка не собрана")
        return FileResponse(index)


_mount_frontend()
