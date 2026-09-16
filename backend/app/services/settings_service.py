from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt, mask
from app.models.models import Setting

SECRET_KEYS = {
    "telegram_token",
    "ai_api_key",
    "cryptopay_token",
    "cryptomus_api_key",
    "cryptomus_merchant_id",
    "webhook_secret",
    "yoomoney_oauth_token",
    "yoomoney_notification_secret",
}

DEFAULTS: dict[str, str] = {
    "telegram_token": "",
    "bot_enabled": "false",
    "bot_name": "AI Assistant",
    "welcome_text": (
        "Привет, {name}! Я ИИ-ассистент.\n\n"
        "У тебя есть {free} бесплатных запросов. "
        "Просто напиши свой вопрос."
    ),
    "limit_text": (
        "Бесплатные запросы закончились.\n"
        "Выбери тариф командой /buy, чтобы продолжить."
    ),
    "blocked_text": "Доступ к боту ограничен. Свяжитесь с поддержкой.",
    "error_text": "Не удалось получить ответ. Попробуй ещё раз позже.",
    "support_url": "",
    "ai_provider": "openai",
    "ai_base_url": "https://api.openai.com/v1",
    "ai_api_key": "",
    "ai_model": "gpt-4o-mini",
    "ai_system_prompt": "Ты полезный ассистент. Отвечай кратко и по делу.",
    "ai_max_tokens": "1000",
    "ai_temperature": "0.7",
    "ai_timeout": "60",
    "free_requests": "2",
    "max_prompt_length": "4000",
    "payment_provider": "test",
    "payments_test_mode": "true",
    "cryptopay_token": "",
    "cryptomus_api_key": "",
    "cryptomus_merchant_id": "",
    "webhook_secret": "",
    "usdt_network": "TRC20",
    "enabled_assets": "USDT,BTC",
    "public_url": "",
    "yoomoney_enabled": "false",
    "yoomoney_wallet": "",
    "yoomoney_oauth_token": "",
    "yoomoney_notification_secret": "",
    "yoomoney_commission_percent": "3",
    "yoomoney_commission_fixed": "0",
    "yoomoney_commission_payer": "client",
    "yoomoney_test_mode": "false",
    "yoomoney_payment_type": "AC",
}

class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def seed_defaults(self) -> None:
        result = await self.session.execute(select(Setting.key))
        existing = set(result.scalars().all())
        for key, value in DEFAULTS.items():
            if key in existing:
                continue
            is_secret = key in SECRET_KEYS
            stored = encrypt(value) if (is_secret and value) else value
            self.session.add(Setting(key=key, value=stored, is_secret=is_secret))
        await self.session.commit()

    async def all_raw(self) -> dict[str, str]:
        result = await self.session.execute(select(Setting))
        data = dict(DEFAULTS)
        for row in result.scalars().all():
            data[row.key] = decrypt(row.value) if row.is_secret else row.value
        return data

    async def get(self, key: str, default: str = "") -> str:
        row = await self.session.get(Setting, key)
        if row is None:
            return DEFAULTS.get(key, default)
        return decrypt(row.value) if row.is_secret else row.value

    async def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(float(await self.get(key, str(default))))
        except (TypeError, ValueError):
            return default

    async def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(await self.get(key, str(default)))
        except (TypeError, ValueError):
            return default

    async def get_bool(self, key: str, default: bool = False) -> bool:
        value = (await self.get(key, "true" if default else "false")).lower()
        return value in {"1", "true", "yes", "on"}

    async def set_many(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            if value is None:
                continue
            is_secret = key in SECRET_KEYS
            if is_secret and str(value) == "":
                continue
            row = await self.session.get(Setting, key)
            stored = encrypt(str(value)) if (is_secret and value) else str(value)
            if row is None:
                self.session.add(Setting(key=key, value=stored, is_secret=is_secret))
            else:
                row.value = stored
                row.is_secret = is_secret
        await self.session.commit()

    async def masked(self) -> dict[str, str]:
        data = await self.all_raw()
        return {
            key: (mask(value) if key in SECRET_KEYS else value)
            for key, value in data.items()
        }

    async def secret_status(self) -> dict[str, bool]:
        data = await self.all_raw()
        return {key: bool(data.get(key)) for key in SECRET_KEYS}
