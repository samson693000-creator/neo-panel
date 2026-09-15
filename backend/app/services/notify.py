import logging

from app.bot.runner import bot_manager

logger = logging.getLogger("notify")

async def notify_user(telegram_id: int, text: str) -> bool:
    bot = bot_manager.bot
    if bot is None:
        logger.warning("Бот не запущен, уведомление не отправлено")
        return False
    try:
        await bot.send_message(telegram_id, text)
        return True
    except Exception as exc:
        logger.warning("Не удалось отправить сообщение %s: %s", telegram_id, exc)
        return False
