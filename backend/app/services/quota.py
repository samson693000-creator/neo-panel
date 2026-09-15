from datetime import datetime, timezone

from app.models.models import BotUser

def tariff_active(user: BotUser) -> bool:
    if not user.is_unlimited:
        return False
    if user.tariff_expires_at is None:
        return True
    expires = user.tariff_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)

def consume_request(user: BotUser, free_limit: int) -> tuple[bool, str]:
    if user.is_blocked:
        return False, "blocked"

    if tariff_active(user):
        user.total_requests += 1
        return True, "unlimited"

    if user.paid_requests > 0:
        user.paid_requests -= 1
        user.total_requests += 1
        return True, "paid"

    if user.free_used < free_limit:
        user.free_used += 1
        user.total_requests += 1
        return True, "free"

    return False, "limit"

def remaining_text(user: BotUser, free_limit: int) -> str:
    if tariff_active(user):
        until = (
            user.tariff_expires_at.strftime("%d.%m.%Y")
            if user.tariff_expires_at
            else "бессрочно"
        )
        return f"безлимит до {until}"
    free_left = max(free_limit - user.free_used, 0)
    return f"платных: {user.paid_requests}, бесплатных: {free_left}"
