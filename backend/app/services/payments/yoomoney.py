# -*- coding: utf-8 -*-
"""YooMoney wallet: QuickPay, HTTP notifications, operation-history."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from decimal import ROUND_UP, Decimal
from urllib.parse import quote, urlencode
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog, BotUser, Payment, Tariff
from app.services.activation import activate_payment
from app.services.payments.base import ProviderError
from app.services.settings_service import SettingsService

logger = logging.getLogger("yoomoney")

API = "https://yoomoney.ru/api"
QUICKPAY = "https://yoomoney.ru/quickpay/confirm"
RUB = Decimal("0.01")
EXPIRE_HOURS = 24
POLL_LIMIT = 40


def _redact(text: str) -> str:
    lower = text.lower()
    for key in ("bearer ", "access_token", "notification_secret", "oauth"):
        if key in lower:
            return "[redacted]"
    return text[:300]


def ceil_kopecks(value: Decimal) -> Decimal:
    return value.quantize(RUB, rounding=ROUND_UP)


def calc_gross(
    price: Decimal,
    percent: Decimal,
    fixed: Decimal,
    payer: str,
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (net, gross, commission). Net is tariff price."""
    net = ceil_kopecks(max(price, Decimal("0")))
    percent = max(percent, Decimal("0"))
    fixed = max(fixed, Decimal("0"))
    if payer == "seller":
        commission = ceil_kopecks(net * percent / Decimal("100") + fixed)
        return net, net, commission
    rate = percent / Decimal("100")
    if rate >= 1:
        raise ProviderError("Процент комиссии должен быть меньше 100")
    gross = ceil_kopecks((net + fixed) / (Decimal("1") - rate))
    return net, gross, gross - net


def new_order_id() -> str:
    return f"np{secrets.token_hex(12)}"[:64]


def rfc3986(value: str) -> str:
    return quote(str(value), safe="-._~")


def hmac_sign(params: dict[str, str], secret: str) -> str:
    parts = []
    for key in sorted(params):
        if key == "sign":
            continue
        parts.append(f"{key}={rfc3986(params[key])}")
    payload = "&".join(parts)
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def sha1_sign(params: dict[str, str], secret: str) -> str:
    raw = "&".join(
        [
            params.get("notification_type", ""),
            params.get("operation_id", ""),
            params.get("amount", ""),
            params.get("currency", ""),
            params.get("datetime", ""),
            params.get("sender", ""),
            params.get("codepro", ""),
            secret,
            params.get("label", ""),
        ]
    )
    return hashlib.sha1(raw.encode()).hexdigest()


def verify_notification(params: dict[str, str], secret: str) -> bool:
    if not secret:
        return False
    incoming_hmac = (params.get("sign") or "").strip().lower()
    if incoming_hmac:
        expected = hmac_sign(params, secret)
        return hmac.compare_digest(expected, incoming_hmac)
    incoming_sha1 = (params.get("sha1_hash") or "").strip().lower()
    if incoming_sha1:
        return hmac.compare_digest(sha1_sign(params, secret), incoming_sha1)
    return False


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _money(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def build_pay_url(
    wallet: str,
    amount: Decimal,
    order_id: str,
    payment_type: str,
    success_url: str = "",
) -> str:
    query = {
        "receiver": wallet,
        "quickpay-form": "button",
        "paymentType": payment_type,
        "sum": f"{ceil_kopecks(amount):.2f}",
        "label": order_id,
    }
    if success_url:
        query["successURL"] = success_url
    return f"{QUICKPAY}?{urlencode(query)}"


class YooMoneyClient:
    def __init__(self, token: str):
        self.token = token

    async def _post(self, path: str, data: dict | None = None) -> dict:
        if not self.token:
            raise ProviderError("OAuth-токен ЮMoney не задан")
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                res = await client.post(f"{API}{path}", data=data or {}, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderError("ЮMoney: сеть недоступна") from exc
        if res.status_code == 401:
            raise ProviderError("ЮMoney: токен отклонён (401)")
        try:
            payload = res.json()
        except ValueError as exc:
            raise ProviderError("ЮMoney: неверный ответ API") from exc
        if isinstance(payload, dict) and payload.get("error"):
            raise ProviderError("ЮMoney: ошибка API")
        return payload if isinstance(payload, dict) else {}

    async def account_info(self) -> dict:
        return await self._post("/account-info")

    async def find_by_label(self, order_id: str) -> dict | None:
        payload = await self._post(
            "/operation-history",
            {"type": "deposition", "label": order_id, "records": "30", "details": "true"},
        )
        for op in payload.get("operations") or []:
            if str(op.get("label") or "") != order_id:
                continue
            if str(op.get("direction") or "in") not in {"in", ""}:
                continue
            return op
        return None


async def load_yoomoney_settings(session: AsyncSession) -> dict:
    svc = SettingsService(session)
    return {
        "enabled": await svc.get_bool("yoomoney_enabled", False),
        "wallet": (await svc.get("yoomoney_wallet")).strip(),
        "token": await svc.get("yoomoney_oauth_token"),
        "notify_secret": await svc.get("yoomoney_notification_secret"),
        "percent": Decimal(str(await svc.get("yoomoney_commission_percent") or "0")),
        "fixed": Decimal(str(await svc.get("yoomoney_commission_fixed") or "0")),
        "payer": (await svc.get("yoomoney_commission_payer") or "client").lower(),
        "test_mode": await svc.get_bool("yoomoney_test_mode", False),
        "public_url": (await svc.get("public_url")).rstrip("/"),
        "payment_type": (await svc.get("yoomoney_payment_type") or "AC").upper(),
    }


async def create_yoomoney_order(
    session: AsyncSession,
    *,
    user: BotUser,
    tariff: Tariff | None,
    amount_override: Decimal | None = None,
    payment_type: str | None = None,
) -> Payment:
    cfg = await load_yoomoney_settings(session)
    if not cfg["enabled"]:
        raise ProviderError("ЮMoney выключен в настройках")
    if not cfg["wallet"]:
        raise ProviderError("Не задан номер кошелька ЮMoney")

    price = amount_override if amount_override is not None else Decimal(str(tariff.price if tariff else 0))
    if price <= 0:
        raise ProviderError("Сумма тарифа должна быть больше нуля")

    net, gross, commission = calc_gross(price, cfg["percent"], cfg["fixed"], cfg["payer"])
    ptype = (payment_type or cfg["payment_type"] or "AC").upper()
    if ptype not in {"AC", "PC"}:
        ptype = "AC"
    order_id = new_order_id()
    pay_url = build_pay_url(cfg["wallet"], gross, order_id, ptype, cfg["public_url"])

    payment = Payment(
        user_id=user.id,
        tariff_id=tariff.id if tariff else None,
        provider="yoomoney",
        invoice_id=order_id,
        order_id=order_id,
        amount=gross,
        amount_net=net,
        amount_gross=gross,
        commission_amount=commission,
        currency="RUB",
        asset="RUB",
        network=ptype,
        pay_url=pay_url,
        status="pending",
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


def _amount_ok(payment: Payment, credited: Decimal, withdrawn: Decimal, payer: str) -> bool:
    net = _money(payment.amount_net)
    gross = _money(payment.amount_gross)
    if payer == "seller":
        paid = withdrawn if withdrawn > 0 else credited
        return paid + Decimal("0.009") >= gross
    return credited + Decimal("0.009") >= net


async def fulfill_yoomoney(
    session: AsyncSession,
    payment: Payment,
    *,
    operation_id: str,
    credited: Decimal,
    withdrawn: Decimal,
    payer: str,
    raw: str,
    notify: bool = True,
) -> tuple[bool, str]:
    locked = await session.execute(
        select(Payment).where(Payment.id == payment.id).with_for_update()
    )
    payment = locked.scalar_one()
    if payment.status == "paid":
        return False, "already_paid"

    if payment.provider != "yoomoney":
        return False, "wrong_provider"

    if not _amount_ok(payment, credited, withdrawn, payer):
        payment.failure_reason = "amount_mismatch"
        await session.commit()
        logger.warning("YooMoney amount mismatch order=%s", payment.order_id)
        return False, "amount_mismatch"

    if operation_id:
        dup = await session.scalar(
            select(Payment.id).where(
                Payment.yoomoney_operation_id == operation_id,
                Payment.id != payment.id,
            )
        )
        if dup:
            payment.failure_reason = "operation_reused"
            await session.commit()
            return False, "operation_reused"
        payment.yoomoney_operation_id = operation_id

    payment.raw = raw[:4000]
    payment.failure_reason = ""
    activated = await activate_payment(session, payment, notify=notify)
    if activated:
        payment.processed_at = datetime.now(timezone.utc)
        session.add(
            AuditLog(
                admin_name="yoomoney",
                action="yoomoney_paid",
                entity="payment",
                details=f"order={payment.order_id} op=***",
            )
        )
        await session.commit()
    return activated, "paid" if activated else "already_paid"


async def check_yoomoney_order(session: AsyncSession, order_id: str, notify: bool = True) -> dict:
    cfg = await load_yoomoney_settings(session)
    result = await session.execute(
        select(Payment).where(Payment.order_id == order_id).with_for_update()
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        return {"ok": False, "status": "not_found", "message": "Заказ не найден"}
    if payment.status == "paid":
        return {"ok": True, "status": "paid", "message": "Уже оплачен"}
    if payment.status in {"cancelled", "expired", "failed"}:
        return {"ok": False, "status": payment.status, "message": f"Статус: {payment.status}"}

    op = await YooMoneyClient(cfg["token"]).find_by_label(order_id)
    if op is None:
        return {"ok": False, "status": "pending", "message": "Оплата пока не найдена"}

    status = str(op.get("status") or "")
    if status == "in_progress":
        return {"ok": False, "status": "pending", "message": "Платёж ещё обрабатывается"}
    if status == "refused":
        payment.status = "failed"
        payment.failure_reason = "refused"
        await session.commit()
        return {"ok": False, "status": "failed", "message": "Перевод отклонён"}
    if status != "success":
        return {"ok": False, "status": "pending", "message": "Операция ещё не успешна"}

    credited = _money(op.get("amount"))
    withdrawn = _money(op.get("withdraw_amount") or op.get("amount"))
    activated, code = await fulfill_yoomoney(
        session,
        payment,
        operation_id=str(op.get("operation_id") or ""),
        credited=credited,
        withdrawn=withdrawn,
        payer=cfg["payer"],
        raw=str({k: op.get(k) for k in ("operation_id", "status", "amount", "datetime", "label")}),
        notify=notify,
    )
    if code == "amount_mismatch":
        return {
            "ok": False,
            "status": "pending",
            "message": "Сумма на кошельке меньше стоимости тарифа",
        }
    if activated or code == "already_paid":
        return {"ok": True, "status": "paid", "message": "Оплата подтверждена. Доступ к тарифу активирован."}
    return {"ok": False, "status": payment.status, "message": "Не удалось подтвердить"}


async def handle_http_notification(session: AsyncSession, params: dict[str, str]) -> dict:
    cfg = await load_yoomoney_settings(session)
    secret = cfg["notify_secret"]
    if not verify_notification(params, secret):
        logger.warning("YooMoney webhook: bad signature")
        return {"ok": False, "error": "bad_signature", "http": 403}

    if _as_bool(params.get("test_notification", "")):
        logger.info("YooMoney test notification received, access not granted")
        return {"ok": True, "skipped": "test_notification"}

    if _as_bool(params.get("unaccepted", "false")):
        return {"ok": True, "skipped": "unaccepted"}

    label = (params.get("label") or "").strip()
    if not label:
        return {"ok": True, "found": False}

    payment = (
        await session.execute(select(Payment).where(Payment.order_id == label))
    ).scalar_one_or_none()
    if payment is None:
        return {"ok": True, "found": False}

    currency = params.get("currency", "643")
    if currency not in {"643", "RUB"}:
        payment.failure_reason = "bad_currency"
        await session.commit()
        return {"ok": True, "skipped": "currency"}

    credited = _money(params.get("amount"))
    withdrawn = _money(params.get("withdraw_amount") or params.get("amount"))
    safe_raw = {
        "notification_type": params.get("notification_type"),
        "operation_id": params.get("operation_id"),
        "amount": params.get("amount"),
        "withdraw_amount": params.get("withdraw_amount"),
        "currency": params.get("currency"),
        "label": label,
        "datetime": params.get("datetime"),
    }
    activated, code = await fulfill_yoomoney(
        session,
        payment,
        operation_id=str(params.get("operation_id") or ""),
        credited=credited,
        withdrawn=withdrawn,
        payer=cfg["payer"],
        raw=str(safe_raw),
        notify=True,
    )
    return {"ok": True, "status": code, "activated": activated}


async def test_connection(session: AsyncSession) -> dict:
    cfg = await load_yoomoney_settings(session)
    info = await YooMoneyClient(cfg["token"]).account_info()
    account = str(info.get("account") or "")
    wallet = cfg["wallet"]
    wallet_match = bool(account) and (not wallet or wallet == account)
    return {
        "ok": True,
        "account": account,
        "currency": info.get("currency"),
        "account_status": info.get("account_status"),
        "wallet_match": wallet_match,
        "message": "Подключение успешно" if account else "Пустой ответ account-info",
    }


async def poll_pending_yoomoney() -> int:
    from app.db.session import SessionLocal

    activated = 0
    async with SessionLocal() as session:
        cfg = await load_yoomoney_settings(session)
        if not cfg["enabled"] or not cfg["token"]:
            return 0
        now = datetime.now(timezone.utc)
        rows = await session.execute(
            select(Payment)
            .where(Payment.provider == "yoomoney", Payment.status == "pending")
            .order_by(Payment.id.asc())
            .limit(POLL_LIMIT)
        )
        for payment in rows.scalars().all():
            created = payment.created_at
            if created is not None:
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if now - created > timedelta(hours=EXPIRE_HOURS):
                    payment.status = "expired"
                    payment.failure_reason = "expired"
                    await session.commit()
                    continue
            try:
                result = await check_yoomoney_order(session, payment.order_id, notify=True)
                if result.get("status") == "paid":
                    activated += 1
            except ProviderError as exc:
                logger.warning("YooMoney poll: %s", _redact(str(exc)))
            except Exception:
                logger.exception("YooMoney poll failed for order %s", payment.order_id)
    return activated
