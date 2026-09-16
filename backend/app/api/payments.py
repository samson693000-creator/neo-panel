from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_session
from app.models.models import Admin, AuditLog, BotUser, Payment, Tariff
from app.services.activation import activate_payment
from app.services.payments import ProviderError, get_provider
from app.services.payments.yoomoney import (
    check_yoomoney_order,
    create_yoomoney_order,
    handle_http_notification,
    load_yoomoney_settings,
    poll_pending_yoomoney,
    test_connection,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.get("")
async def list_payments(
    status_filter: str = Query("all", alias="status"),
    page: int = 1,
    per_page: int = 25,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("support")),
) -> dict:
    stmt = (
        select(Payment, BotUser, Tariff)
        .join(BotUser, BotUser.id == Payment.user_id)
        .outerjoin(Tariff, Tariff.id == Payment.tariff_id)
    )

    if status_filter != "all":
        stmt = stmt.where(Payment.status == status_filter)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    rows = await session.execute(
        stmt.order_by(Payment.id.desc()).offset((page - 1) * per_page).limit(per_page)
    )

    items = [
        {
            "id": p.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "tariff": t.name if t else "-",
            "provider": p.provider,
            "invoice_id": p.invoice_id,
            "order_id": p.order_id,
            "amount": float(p.amount),
            "amount_net": float(p.amount_net or 0),
            "amount_gross": float(p.amount_gross or 0),
            "commission_amount": float(p.commission_amount or 0),
            "asset": p.asset,
            "network": p.network,
            "status": p.status,
            "pay_url": p.pay_url,
            "created_at": p.created_at,
            "paid_at": p.paid_at,
        }
        for p, u, t in rows.all()
    ]

    revenue = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == "paid"
        )
    )
    pending = await session.scalar(
        select(func.count()).select_from(
            select(Payment.id).where(Payment.status == "pending").subquery()
        )
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": max(1, ceil(total / per_page)),
        "revenue": float(revenue or 0),
        "pending": int(pending or 0),
    }


def _audit(session: AsyncSession, admin: Admin, action: str, details: str) -> None:
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action=action,
            entity="yoomoney",
            details=details[:500],
        )
    )


@router.post("/yoomoney/create")
async def yoomoney_create(
    data: dict,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    telegram_id = data.get("telegram_user_id") or data.get("telegram_id")
    tariff_id = data.get("tariff_id")
    if telegram_id is None:
        raise HTTPException(400, "Укажи telegram_user_id")
    user = (
        await session.execute(select(BotUser).where(BotUser.telegram_id == int(telegram_id)))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Пользователь бота не найден")
    tariff = await session.get(Tariff, int(tariff_id)) if tariff_id else None
    if tariff_id and tariff is None:
        raise HTTPException(404, "Тариф не найден")
    try:
        payment = await create_yoomoney_order(
            session,
            user=user,
            tariff=tariff,
            payment_type=data.get("payment_type"),
        )
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc
    _audit(session, admin, "yoomoney_create", f"order={payment.order_id}")
    await session.commit()
    cfg = await load_yoomoney_settings(session)
    return {
        "ok": True,
        "order_id": payment.order_id,
        "payment_url": payment.pay_url,
        "amount_net": float(payment.amount_net),
        "amount_gross": float(payment.amount_gross),
        "commission_amount": float(payment.commission_amount),
        "currency": "RUB",
        "status": payment.status,
        "notify_url": f"{cfg['public_url']}/api/payments/yoomoney/webhook" if cfg["public_url"] else "",
    }


@router.post("/yoomoney/webhook")
async def yoomoney_webhook(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    content_type = (request.headers.get("content-type") or "").lower()
    params: dict[str, str] = {}
    if "json" in content_type:
        body = await request.json()
        params = {str(k): str(v) for k, v in dict(body).items()}
    else:
        form = await request.form()
        params = {str(k): str(v) for k, v in form.items()}
    result = await handle_http_notification(session, params)
    if result.get("http") == 403:
        raise HTTPException(403, "Неверная подпись")
    return {k: v for k, v in result.items() if k != "http"}


@router.post("/yoomoney/check/{order_id}")
async def yoomoney_check(
    order_id: str,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    try:
        result = await check_yoomoney_order(session, order_id)
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc
    _audit(session, admin, "yoomoney_check", f"order={order_id} status={result.get('status')}")
    await session.commit()
    return result


@router.post("/yoomoney/test")
async def yoomoney_test(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    try:
        result = await test_connection(session)
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc
    _audit(session, admin, "yoomoney_test", "account-info")
    await session.commit()
    return result


@router.post("/yoomoney/test-invoice")
async def yoomoney_test_invoice(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    from decimal import Decimal

    user = (
        await session.execute(select(BotUser).order_by(BotUser.id.asc()).limit(1))
    ).scalar_one_or_none()
    if user is None:
        user = BotUser(telegram_id=0, username="yoomoney-probe", first_name="probe")
        session.add(user)
        await session.flush()
    tariff = (
        await session.execute(
            select(Tariff).where(Tariff.is_active.is_(True)).order_by(Tariff.id.asc()).limit(1)
        )
    ).scalar_one_or_none()
    try:
        payment = await create_yoomoney_order(
            session,
            user=user,
            tariff=tariff,
            amount_override=Decimal("2.00") if tariff is None else None,
        )
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc
    _audit(session, admin, "yoomoney_test_invoice", f"order={payment.order_id}")
    await session.commit()
    return {
        "ok": True,
        "order_id": payment.order_id,
        "payment_url": payment.pay_url,
        "amount_gross": float(payment.amount_gross),
        "message": "Тестовый счёт создан. Оплати по ссылке, затем нажми «Проверить ожидающие».",
    }


@router.post("/yoomoney/sync")
async def yoomoney_sync(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    try:
        count = await poll_pending_yoomoney()
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc
    _audit(session, admin, "yoomoney_sync", f"activated={count}")
    await session.commit()
    return {"ok": True, "activated": count, "message": f"Подтверждено платежей: {count}"}

@router.post("/{payment_id}/confirm")
async def confirm_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(404, "Платёж не найден")
    if payment.status == "paid":
        return {"ok": False, "message": "Платёж уже подтверждён"}

    activated = await activate_payment(session, payment)
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action="confirm_payment",
            entity="payment",
            details=f"id={payment_id} invoice={payment.invoice_id}",
        )
    )
    await session.commit()
    return {"ok": activated, "message": "Тариф активирован"}

@router.post("/{payment_id}/recheck")
async def recheck_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(404, "Платёж не найден")

    if payment.provider == "yoomoney":
        try:
            result = await check_yoomoney_order(session, payment.order_id)
        except ProviderError as exc:
            raise HTTPException(400, str(exc)) from exc
        return result

    try:
        provider = await get_provider(session)
        status = await provider.check_invoice(payment.invoice_id)
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc

    if status == "paid":
        await activate_payment(session, payment)
        return {"ok": True, "status": "paid", "message": "Оплата найдена, тариф выдан"}

    if status != "pending":
        payment.status = status
        await session.commit()

    return {"ok": True, "status": status, "message": f"Статус счёта: {status}"}

@router.post("/{payment_id}/cancel")
async def cancel_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(404, "Платёж не найден")
    if payment.status == "paid":
        raise HTTPException(400, "Оплаченный счёт нельзя отменить")
    payment.status = "cancelled"
    await session.commit()
    return {"ok": True}
