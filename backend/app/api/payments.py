from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_session
from app.models.models import Admin, AuditLog, BotUser, Payment, Tariff
from app.services.activation import activate_payment
from app.services.payments import ProviderError, get_provider

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
            "amount": float(p.amount),
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
