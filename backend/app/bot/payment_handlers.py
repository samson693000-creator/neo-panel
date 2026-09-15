from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from app.bot.handlers import get_or_create_user
from app.db.session import SessionLocal
from app.models.models import BotUser, Payment, Tariff
from app.services.activation import activate_payment
from app.services.payments import ProviderError, get_provider
from app.services.settings_service import SettingsService

router = Router()

ASSET_TITLES = {"USDT": "USDT", "BTC": "BTC", "TON": "TON", "ETH": "ETH"}

async def tariffs_keyboard(session) -> InlineKeyboardMarkup | None:
    rows = await session.execute(
        select(Tariff)
        .where(Tariff.is_active.is_(True), Tariff.price > 0)
        .order_by(Tariff.sort_order, Tariff.id)
    )
    tariffs = rows.scalars().all()
    if not tariffs:
        return None

    buttons = []
    for t in tariffs:
        limit = "∞" if t.is_unlimited else f"{t.requests} зап."
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{t.name} · {limit} · {float(t.price):g} {t.currency}",
                    callback_data=f"tariff:{t.id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    async with SessionLocal() as session:
        await get_or_create_user(session, message)
        keyboard = await tariffs_keyboard(session)

    if keyboard is None:
        await message.answer("Тарифы пока не настроены. Загляни позже.")
        return

    await message.answer(
        "<b>Выбери тариф</b>\n\nПосле выбора укажешь валюту оплаты.",
        reply_markup=keyboard,
    )

@router.callback_query(F.data.startswith("tariff:"))
async def choose_asset(call: CallbackQuery) -> None:
    tariff_id = int(call.data.split(":")[1])

    async with SessionLocal() as session:
        tariff = await session.get(Tariff, tariff_id)
        if tariff is None or not tariff.is_active:
            await call.answer("Тариф недоступен", show_alert=True)
            return
        svc = SettingsService(session)
        assets = [
            a.strip().upper()
            for a in (await svc.get("enabled_assets", "USDT,BTC")).split(",")
            if a.strip()
        ]
        network = await svc.get("usdt_network", "TRC20")

    buttons = []
    for a in assets:
        suffix = f" ({network})" if a == "USDT" else ""
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"Оплатить в {ASSET_TITLES.get(a, a)}{suffix}",
                    callback_data=f"pay:{tariff_id}:{a}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="buy:back")])

    limit = "безлимит" if tariff.is_unlimited else f"{tariff.requests} запросов"
    await call.message.edit_text(
        f"<b>{tariff.name}</b>\n"
        f"{tariff.description or ''}\n\n"
        f"Включено: {limit}\n"
        f"Стоимость: <b>{float(tariff.price):g} {tariff.currency}</b>\n\n"
        "Выбери валюту оплаты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await call.answer()

@router.callback_query(F.data == "buy:back")
async def back_to_tariffs(call: CallbackQuery) -> None:
    async with SessionLocal() as session:
        keyboard = await tariffs_keyboard(session)
    await call.message.edit_text("<b>Выбери тариф</b>", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data.startswith("pay:"))
async def create_invoice(call: CallbackQuery) -> None:
    _, tariff_id_raw, asset = call.data.split(":")
    tariff_id = int(tariff_id_raw)

    async with SessionLocal() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == call.from_user.id)
        )
        user = result.scalar_one_or_none()
        tariff = await session.get(Tariff, tariff_id)
        if user is None or tariff is None:
            await call.answer("Данные не найдены, отправь /start", show_alert=True)
            return

        svc = SettingsService(session)
        test_mode = await svc.get_bool("payments_test_mode", True)
        support = await svc.get("support_url")

        try:
            provider = await get_provider(session)
            invoice = await provider.create_invoice(
                amount_usd=float(tariff.price),
                asset=asset,
                description=f"{tariff.name} для {user.telegram_id}",
                payload=f"u{user.id}t{tariff.id}",
            )
        except ProviderError as exc:
            extra = f"\n\nПоддержка: {support}" if support else ""
            await call.message.answer(
                f"Не удалось создать счёт.\n<i>{exc}</i>{extra}"
            )
            await call.answer()
            return

        payment = Payment(
            user_id=user.id,
            tariff_id=tariff.id,
            provider=provider.name,
            invoice_id=invoice.invoice_id,
            amount=invoice.amount,
            currency=tariff.currency,
            asset=invoice.asset,
            network=invoice.network,
            pay_url=invoice.pay_url,
            status="pending",
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        payment_id = payment.id
        default_network = await svc.get("usdt_network", "")
        network_text = invoice.network or (default_network if asset == "USDT" else "")
        tariff_name = tariff.name

    buttons = []
    if invoice.pay_url:
        buttons.append([InlineKeyboardButton(text="Оплатить", url=invoice.pay_url)])
    buttons.append(
        [
            InlineKeyboardButton(
                text="Я оплатил — проверить",
                callback_data=f"check:{payment_id}",
            )
        ]
    )

    lines = [
        "<b>Счёт создан</b>",
        "",
        f"Тариф: <b>{tariff_name}</b>",
        f"К оплате: <b>{invoice.amount:g} {invoice.asset}</b>",
    ]
    if network_text:
        lines.append(f"Сеть: <b>{network_text}</b>")
    lines.append(f"Счёт: <code>{invoice.invoice_id}</code>")
    lines.append("")
    if test_mode:
        lines.append("Включён тестовый режим. Оплату подтверждает администратор.")
    else:
        lines.append("После оплаты нажми кнопку проверки — тариф активируется сам.")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await call.answer()

@router.callback_query(F.data.startswith("check:"))
async def check_payment(call: CallbackQuery) -> None:
    payment_id = int(call.data.split(":")[1])

    async with SessionLocal() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            await call.answer("Счёт не найден", show_alert=True)
            return

        if payment.status == "paid":
            await call.answer("Оплата уже зачислена", show_alert=True)
            return

        try:
            provider = await get_provider(session)
            status = await provider.check_invoice(payment.invoice_id)
        except ProviderError as exc:
            await call.answer(f"Ошибка проверки: {exc}"[:190], show_alert=True)
            return

        if status == "paid":
            await activate_payment(session, payment, notify=False)
            await call.message.edit_text(
                "<b>Оплата получена</b>\n\nТариф активирован. Задавай вопросы."
            )
            await call.answer("Готово")
            return

        if status in {"expired", "failed"}:
            payment.status = status
            await session.commit()
            await call.answer(
                "Счёт больше не активен. Создай новый через /buy", show_alert=True
            )
            return

    await call.answer("Оплата пока не найдена. Попробуй через минуту.", show_alert=True)
