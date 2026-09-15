import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import router
from app.db.session import SessionLocal
from app.services.settings_service import SettingsService

logger = logging.getLogger("bot")

class BotManager:
    def __init__(self) -> None:
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None
        self.task: asyncio.Task | None = None
        self.status: str = "stopped"
        self.error: str = ""
        self.username: str = ""

    @property
    def running(self) -> bool:
        return self.task is not None and not self.task.done()

    async def start(self) -> tuple[bool, str]:
        if self.running:
            return True, "Бот уже запущен"

        async with SessionLocal() as session:
            svc = SettingsService(session)
            token = await svc.get("telegram_token")

        if not token:
            self.status, self.error = "stopped", "Telegram token не задан"
            return False, self.error

        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            me = await self.bot.get_me()
            self.username = me.username or ""
        except Exception as exc:
            self.status, self.error = "error", f"Неверный токен: {exc}"
            await self.bot.session.close()
            self.bot = None
            return False, self.error

        from app.bot.payment_handlers import router as payment_router

        self.dp = Dispatcher()
        self.dp.include_router(payment_router)
        self.dp.include_router(router)

        async def _run() -> None:
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
                await self.dp.start_polling(self.bot, handle_signals=False)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Polling stopped")
                self.status, self.error = "error", str(exc)

        self.task = asyncio.create_task(_run())
        self.status, self.error = "running", ""
        logger.info("Bot @%s started", self.username)
        return True, f"Бот @{self.username} запущен"

    async def stop(self) -> tuple[bool, str]:
        if self.dp is not None:
            try:
                await self.dp.stop_polling()
            except Exception:
                pass
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except Exception:
                pass
            self.task = None
        if self.bot is not None:
            await self.bot.session.close()
            self.bot = None
        self.dp = None
        self.status = "stopped"
        return True, "Бот остановлен"

    async def restart(self) -> tuple[bool, str]:
        await self.stop()
        return await self.start()

    def state(self) -> dict:
        return {
            "status": "running" if self.running else self.status,
            "username": self.username,
            "error": self.error,
        }

bot_manager = BotManager()
