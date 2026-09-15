from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import AiRequest, BotUser
from app.services.ai import AiError, ask_ai
from app.services.quota import consume_request, remaining_text
from app.services.settings_service import SettingsService

router = Router()

async def get_or_create_user(session, message: Message) -> BotUser:
    tg = message.from_user
    if tg is None:
        raise ValueError("Telegram user is missing")
    result = await session.execute(select(BotUser).where(BotUser.telegram_id == tg.id))
    user = result.scalar_one_or_none()
    if user is None:
        user = BotUser(
            telegram_id=tg.id,
            username=tg.username,
            first_name=tg.first_name,
            last_name=tg.last_name,
            language=tg.language_code,
        )
        session.add(user)
    else:
        user.username = tg.username
        user.first_name = tg.first_name
        user.last_name = tg.last_name
    user.last_seen = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return user

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    async with SessionLocal() as session:
        svc = SettingsService(session)
        user = await get_or_create_user(session, message)
        if user.is_blocked:
            await message.answer(await svc.get("blocked_text"))
            return
        free_limit = await svc.get_int("free_requests", 2)
        template = await svc.get("welcome_text")
        text = template.replace("{name}", user.first_name or "друг").replace(
            "{free}", str(free_limit)
        )
        await message.answer(f"{text}\n\nДоступно — {remaining_text(user, free_limit)}")

@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    async with SessionLocal() as session:
        svc = SettingsService(session)
        user = await get_or_create_user(session, message)
        free_limit = await svc.get_int("free_requests", 2)
        lines = [
            "<b>Профиль</b>",
            f"ID: <code>{user.telegram_id}</code>",
            f"Запросов всего: {user.total_requests}",
            f"Доступно: {remaining_text(user, free_limit)}",
        ]
        await message.answer("\n".join(lines))

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    async with SessionLocal() as session:
        support = await SettingsService(session).get("support_url")
    text = (
        "<b>Команды</b>\n"
        "/start — начать\n"
        "/profile — мой профиль и лимиты\n"
        "/buy — тарифы\n"
        "/help — помощь\n\n"
        "Просто напиши вопрос — я отвечу."
    )
    if support:
        text += f"\n\nПоддержка: {support}"
    await message.answer(text)

@router.message(F.text & ~F.text.startswith("/"))
async def handle_prompt(message: Message) -> None:
    async with SessionLocal() as session:
        svc = SettingsService(session)
        user = await get_or_create_user(session, message)

        if user.is_blocked:
            await message.answer(await svc.get("blocked_text"))
            return

        max_len = await svc.get_int("max_prompt_length", 4000)
        if len(message.text) > max_len:
            await message.answer(f"Слишком длинный запрос. Максимум {max_len} символов.")
            return

        free_limit = await svc.get_int("free_requests", 2)
        allowed, source = consume_request(user, free_limit)
        if not allowed:
            await message.answer(await svc.get("limit_text"))
            return
        await session.commit()

        await message.bot.send_chat_action(message.chat.id, "typing")

        try:
            answer, tokens, model = await ask_ai(session, message.text)
            is_error = False
        except AiError as exc:
            answer = await svc.get("error_text")
            tokens, model, is_error = 0, "", True
            if source == "paid":
                user.paid_requests += 1
            elif source == "free":
                user.free_used = max(user.free_used - 1, 0)
            user.total_requests = max(user.total_requests - 1, 0)
            await session.commit()
            answer += f"\n\n<i>{str(exc)[:200]}</i>"

        session.add(
            AiRequest(
                user_id=user.id,
                model=model,
                prompt=message.text[:4000],
                answer=answer[:8000],
                tokens=tokens,
                source=source,
                is_error=is_error,
            )
        )
        await session.commit()

        left = remaining_text(user, free_limit)

    await message.answer(answer)
    if not is_error:
        await message.answer(f"<i>Осталось — {left}</i>")
