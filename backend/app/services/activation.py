from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import BotUser, Payment, Tariff
from app.services.notify import notify_user

async def activate_payment(
    session: AsyncSession, payment: Payment, notify: bool = True
) -> bool:
    if payment.status == "paid":
        return False

    now = datetime.now(timezone.utc)
    user = await session.get(BotUser, payment.user_id)
    tariff = (
        await session.get(Tariff, payment.tariff_id) if payment.tariff_id else None
    )

    payment.status = "paid"
    payment.paid_at = now
    payment.processed_at = now

    granted = ""
    if user is not None and tariff is not None:
        if tariff.is_unlimited:
            user.is_unlimited = True
            base = user.tariff_expires_at or now
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            if base < now:
                base = now
            days = tariff.duration_days or 30
            user.tariff_expires_at = base + timedelta(days=days)
            granted = f"безлимит на {days} дн."
        else:
            user.paid_requests += tariff.requests
            if tariff.duration_days:
                base = user.tariff_expires_at or now
                if base.tzinfo is None:
                    base = base.replace(tzinfo=timezone.utc)
                if base < now:
                    base = now
                user.tariff_expires_at = base + timedelta(days=tariff.duration_days)
            granted = f"{tariff.requests} запросов"
        user.tariff_id = tariff.id

    await session.commit()

    if notify and user is not None:
        name = tariff.name if tariff else "начисление"
        if payment.provider == "yoomoney":
            text = (
                "<b>Оплата подтверждена. Доступ к тарифу активирован.</b>\n\n"
                f"Тариф: <b>{name}</b>\n"
                f"Начислено: {granted or 'доступ обновлён'}"
            )
        else:
            text = (
                "<b>Оплата получена</b>\n\n"
                f"Тариф: <b>{name}</b>\n"
                f"Начислено: {granted or 'доступ обновлён'}\n\n"
                "Можешь продолжать — просто напиши свой вопрос."
            )
        await notify_user(user.telegram_id, text)
    return True
