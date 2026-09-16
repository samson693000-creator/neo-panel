import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.models import Payment
from app.services.activation import activate_payment
from app.services.payments import CryptomusProvider, CryptoPayProvider
from app.services.settings_service import SettingsService

logger = logging.getLogger("webhooks")
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

async def _find_payment(session: AsyncSession, invoice_id: str) -> Payment | None:
    if not invoice_id:
        return None
    result = await session.execute(
        select(Payment).where(Payment.invoice_id == str(invoice_id))
    )
    return result.scalar_one_or_none()

@router.post("/cryptopay")
async def cryptopay_webhook(
    request: Request,
    crypto_pay_api_signature: str = Header("", alias="crypto-pay-api-signature"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    body = await request.body()
    token = await SettingsService(session).get("cryptopay_token")
    if not token:
        raise HTTPException(400, "Crypto Pay не настроен")

    provider = CryptoPayProvider(token)
    if not provider.verify_webhook(body, crypto_pay_api_signature):
        logger.warning("Crypto Pay: неверная подпись webhook")
        raise HTTPException(403, "Неверная подпись")

    payload = json.loads(body.decode() or "{}")
    invoice_id, status = CryptoPayProvider.parse_webhook(payload)
    if status != "paid":
        return {"ok": True, "skipped": True}

    payment = await _find_payment(session, invoice_id)
    if payment is None:
        logger.warning("Crypto Pay: платёж %s не найден", invoice_id)
        return {"ok": True, "found": False}

    payment.raw = json.dumps(payload, ensure_ascii=False)[:4000]
    await activate_payment(session, payment)
    return {"ok": True}

@router.post("/cryptomus")
async def cryptomus_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    payload = await request.json()
    svc = SettingsService(session)
    api_key = await svc.get("cryptomus_api_key")
    merchant = await svc.get("cryptomus_merchant_id")
    network = await svc.get("usdt_network", "TRC20")
    public_url = await svc.get("public_url")
    if not api_key or not merchant:
        raise HTTPException(400, "Cryptomus не настроен")

    provider = CryptomusProvider(api_key, merchant, network, public_url)
    if not provider.verify_webhook(dict(payload)):
        logger.warning("Cryptomus: неверная подпись webhook")
        raise HTTPException(403, "Неверная подпись")

    uuid_value = str(payload.get("uuid", ""))
    status = (payload.get("status") or "").lower()
    payment = await _find_payment(session, uuid_value)
    if payment is None:
        return {"ok": True, "found": False}

    payment.raw = json.dumps(payload, ensure_ascii=False)[:4000]
    if status in {"paid", "paid_over"}:
        await activate_payment(session, payment)
    elif status in {"cancel", "fail", "system_fail", "wrong_amount"}:
        payment.status = "failed"
        await session.commit()
    else:
        await session.commit()

    return {"ok": True}


@router.post("/yoomoney")
async def yoomoney_webhook_alias(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    from app.api.payments import yoomoney_webhook

    return await yoomoney_webhook(request, session)
