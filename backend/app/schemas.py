from datetime import datetime

from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class AccountUpdate(BaseModel):
    old_password: str
    new_username: str | None = None
    new_password: str | None = None

class TariffIn(BaseModel):
    name: str
    description: str = ""
    price: float = 0
    currency: str = "USDT"
    requests: int = 0
    is_unlimited: bool = False
    duration_days: int = 0
    is_active: bool = True
    sort_order: int = 0

class TariffOut(TariffIn):
    model_config = ConfigDict(from_attributes=True)
    id: int

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    free_used: int
    paid_requests: int
    total_requests: int
    is_unlimited: bool
    is_blocked: bool
    tariff_id: int | None
    tariff_expires_at: datetime | None
    note: str
    created_at: datetime
    last_seen: datetime | None

class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    pages: int

class GrantIn(BaseModel):
    requests: int = 0
    days: int = 0
    unlimited: bool | None = None
    note: str | None = None

class SettingsIn(BaseModel):
    values: dict[str, str]

class DashboardOut(BaseModel):
    users_total: int
    users_today: int
    users_active_7d: int
    blocked: int
    requests_total: int
    requests_today: int
    paid_users: int
    revenue_total: float
    bot_status: str
    bot_username: str
    ai_configured: bool
    payments_configured: bool
