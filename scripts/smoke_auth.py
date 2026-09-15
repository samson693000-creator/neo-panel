# -*- coding: utf-8 -*-
"""API smoke: login, health, account login/password change. Isolated DB."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "backend"))

SMOKE_DB = ROOT / "data" / "smoke.db"
SMOKE_DB.parent.mkdir(parents=True, exist_ok=True)
if SMOKE_DB.exists():
    SMOKE_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{SMOKE_DB.as_posix()}"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "SmokePass12345"
os.environ["SECRET_KEY"] = "smoke-secret-key-not-for-production-use"
os.environ["ENCRYPTION_KEY"] = ""
os.environ["CORS_ORIGINS"] = "http://test"

from fastapi.testclient import TestClient
from app.main import app


def ok(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        raise SystemExit(f"FAIL {name}: {detail}")
    print("OK", name)


with TestClient(app) as client:
    health = client.get("/api/health")
    ok("health", health.status_code == 200 and health.json().get("status") == "ok", health.text)

    bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    ok("bad-login", bad.status_code == 401, str(bad.status_code))

    login = client.post(
        "/api/auth/login", json={"username": "admin", "password": "SmokePass12345"}
    )
    ok("login", login.status_code == 200, login.text)
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=headers)
    ok("me", me.status_code == 200 and me.json()["username"] == "admin", me.text)

    changed = client.post(
        "/api/auth/account",
        headers=headers,
        json={
            "old_password": "SmokePass12345",
            "new_username": "owner1",
            "new_password": "NewSmokePass123",
        },
    )
    ok("account", changed.status_code == 200, changed.text)
    token2 = changed.json()["access_token"]
    ok("new-username", changed.json()["username"] == "owner1", changed.text)

    old = client.post(
        "/api/auth/login", json={"username": "admin", "password": "SmokePass12345"}
    )
    ok("old-login-rejected", old.status_code == 401, str(old.status_code))

    fresh = client.post(
        "/api/auth/login", json={"username": "owner1", "password": "NewSmokePass123"}
    )
    ok("new-login", fresh.status_code == 200, fresh.text)

    headers2 = {"Authorization": f"Bearer {fresh.json()['access_token']}"}

    page = client.get("/")
    ok("admin-ui", page.status_code == 200 and "NEO PANEL" in page.text, str(page.status_code))

    dash = client.get("/api/stats/dashboard", headers=headers2)
    ok("dashboard", dash.status_code == 200, dash.text)

    tariffs = client.get("/api/tariffs", headers=headers2)
    ok("tariffs", tariffs.status_code == 200 and isinstance(tariffs.json(), list), tariffs.text)
    ok("seed-tariffs", len(tariffs.json()) >= 3, str(len(tariffs.json())))

    users = client.get("/api/users", headers=headers2)
    ok("users", users.status_code == 200 and "items" in users.json(), users.text)

    settings = client.get("/api/settings", headers=headers2)
    ok("settings", settings.status_code == 200 and "values" in settings.json(), settings.text)

    payments = client.get("/api/payments", headers=headers2)
    ok("payments", payments.status_code == 200 and "items" in payments.json(), payments.text)

    audiences = client.get("/api/broadcasts/audiences", headers=headers2)
    ok("audiences", audiences.status_code == 200 and isinstance(audiences.json(), list), audiences.text)

    admins = client.get("/api/admins", headers=headers2)
    ok("admins", admins.status_code == 200 and len(admins.json()) >= 1, admins.text)

    bot = client.get("/api/settings/bot/status", headers=headers2)
    ok("bot-status", bot.status_code == 200, bot.text)

print("SMOKE PASSED")
