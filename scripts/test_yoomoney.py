# -*- coding: utf-8 -*-
"""Unit tests: commission rounding, HMAC sign, idempotent YooMoney fulfill."""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "backend"))

SMOKE_DB = ROOT / "data" / "yoomoney_unit.db"
SMOKE_DB.parent.mkdir(parents=True, exist_ok=True)
if SMOKE_DB.exists():
    SMOKE_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{SMOKE_DB.as_posix()}"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "SmokePass12345"
os.environ["SECRET_KEY"] = "smoke-secret-key-not-for-production-use"
os.environ["ENCRYPTION_KEY"] = ""
os.environ["CORS_ORIGINS"] = "http://test"

from app.services.payments.yoomoney import (  # noqa: E402
    calc_gross,
    hmac_sign,
    verify_notification,
)


def ok(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        raise SystemExit(f"FAIL {name}: {detail}")
    print("OK", name)


net, gross, commission = calc_gross(Decimal("50"), Decimal("2"), Decimal("0"), "client")
ok("net-50", net == Decimal("50.00"), str(net))
ok("gross-ceil", gross == Decimal("51.03"), str(gross))
ok("commission", commission == Decimal("1.03"), str(commission))
ok("wallet-enough", (gross * Decimal("0.98")) >= Decimal("50"), str(gross * Decimal("0.98")))

s_net, s_gross, s_fee = calc_gross(Decimal("50"), Decimal("2"), Decimal("1.50"), "seller")
ok("seller-gross", s_gross == Decimal("50.00"), str(s_gross))
ok("seller-fee", s_fee == Decimal("2.50"), str(s_fee))

params = {
    "notification_type": "p2p-incoming",
    "operation_id": "904035776918098009",
    "amount": "50.00",
    "withdraw_amount": "51.03",
    "currency": "643",
    "datetime": "2014-04-28T16:31:28Z",
    "sender": "41003188981230",
    "codepro": "false",
    "label": "npabc123",
    "test_notification": "false",
    "unaccepted": "false",
}
secret = "secret123"
params["sign"] = hmac_sign(params, secret)
ok("hmac-ok", verify_notification(params, secret))
bad = dict(params, sign="00" * 32)
ok("hmac-bad", not verify_notification(bad, secret))
ok("hmac-empty-secret", not verify_notification(params, ""))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
import sqlite3  # noqa: E402


with TestClient(app) as client:
    login = client.post(
        "/api/auth/login", json={"username": "admin", "password": "SmokePass12345"}
    )
    ok("login", login.status_code == 200, login.text)
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    settings = client.get("/api/settings", headers=headers)
    ok("settings", settings.status_code == 200, settings.text)
    values = settings.json()["values"]
    ok(
        "token-masked",
        "yoomoney_oauth_token" in settings.json()["secret_keys"],
        str(settings.json()["secret_keys"]),
    )

    save = client.put(
        "/api/settings",
        headers=headers,
        json={
            "values": {
                **{k: v for k, v in values.items() if "****" not in str(v)},
                "yoomoney_enabled": "true",
                "yoomoney_wallet": "410011234567890",
                "yoomoney_notification_secret": "secret123",
                "yoomoney_commission_percent": "2",
                "yoomoney_commission_payer": "client",
                "public_url": "https://panel.example.com",
            }
        },
    )
    ok("save-ym", save.status_code == 200, save.text)
    saved = save.json()["values"]
    ok(
        "secret-not-full",
        "secret123" not in str(saved.get("yoomoney_notification_secret", "")),
        str(saved.get("yoomoney_notification_secret")),
    )

    conn = sqlite3.connect(SMOKE_DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bot_users (telegram_id, username, free_used, paid_requests, "
        "total_requests, is_unlimited, is_blocked, note) "
        "VALUES (90001, 'payer', 0, 0, 0, 0, 0, '')"
    )
    user_id = cur.lastrowid
    tariff_id = cur.execute("SELECT id FROM tariffs LIMIT 1").fetchone()[0]
    cur.execute(
        "INSERT INTO payments (user_id, tariff_id, provider, invoice_id, order_id, "
        "amount, amount_net, amount_gross, commission_amount, currency, asset, "
        "status, failure_reason, raw, pay_url, network) "
        "VALUES (?, ?, 'yoomoney', 'npunit1', 'npunit1', 51.03, 50, 51.03, 1.03, "
        "'RUB', 'RUB', 'pending', '', '', '', '')",
        (user_id, tariff_id),
    )
    conn.commit()
    conn.close()
    order_id = "npunit1"

    forged = dict(params, label=order_id, amount="50.00", withdraw_amount="51.03")
    forged.pop("sign", None)
    forged["sign"] = hmac_sign(forged, "wrong")
    bad_hook = client.post("/api/payments/yoomoney/webhook", data=forged)
    ok("webhook-403", bad_hook.status_code == 403, bad_hook.text)

    good = dict(params, label=order_id, amount="50.00", withdraw_amount="51.03")
    good.pop("sign", None)
    good["sign"] = hmac_sign(good, "secret123")
    hook = client.post("/api/payments/yoomoney/webhook", data=good)
    ok("webhook-200", hook.status_code == 200, hook.text)
    ok("webhook-paid", hook.json().get("status") in {"paid", "already_paid"}, hook.text)

    hook2 = client.post("/api/payments/yoomoney/webhook", data=good)
    ok("webhook-idempotent", hook2.status_code == 200, hook2.text)
    ok("no-second-grant", hook2.json().get("activated") is False, hook2.text)

    payments = client.get("/api/payments?status=paid", headers=headers)
    ok("list-paid", payments.status_code == 200, payments.text)
    items = payments.json()["items"]
    ym = [p for p in items if p.get("order_id") == order_id]
    ok("one-paid", len(ym) == 1, str(len(ym)))

    create_unauth = client.post("/api/payments/yoomoney/create", json={})
    ok("create-auth", create_unauth.status_code == 401, str(create_unauth.status_code))

print("YOOMONEY TESTS PASSED")
