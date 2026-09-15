import hashlib
import hmac

import httpx

from app.services.payments.base import Invoice, PaymentProvider, ProviderError

API_URL = "https://pay.crypt.bot/api"

class CryptoPayProvider(PaymentProvider):
    name = "cryptopay"
    supported_assets = ("USDT", "BTC", "TON", "ETH", "LTC", "TRX")

    def __init__(self, token: str):
        self.token = token

    async def _call(self, method: str, params: dict | None = None) -> dict:
        headers = {"Crypto-Pay-API-Token": self.token}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(
                    f"{API_URL}/{method}", json=params or {}, headers=headers
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Crypto Pay: сеть — {exc}") from exc

        data = res.json()
        if not data.get("ok"):
            raise ProviderError(f"Crypto Pay: {data.get('error')}")
        return data["result"]

    async def _rate_to_usd(self, asset: str) -> float:
        rates = await self._call("getExchangeRates")
        for rate in rates:
            if rate.get("source") == asset and rate.get("target") == "USD":
                return float(rate.get("rate") or 0)
        raise ProviderError(f"Crypto Pay: нет курса {asset}/USD")

    async def create_invoice(
        self, amount_usd: float, asset: str, description: str, payload: str
    ) -> Invoice:
        asset = asset.upper()
        if asset == "USDT":
            amount = round(amount_usd, 2)
        else:
            rate = await self._rate_to_usd(asset)
            if rate <= 0:
                raise ProviderError("Нулевой курс обмена")
            amount = round(amount_usd / rate, 8)

        result = await self._call(
            "createInvoice",
            {
                "asset": asset,
                "amount": str(amount),
                "description": description[:1024],
                "payload": payload,
                "expires_in": 3600,
                "allow_comments": False,
            },
        )

        return Invoice(
            invoice_id=str(result.get("invoice_id")),
            pay_url=result.get("bot_invoice_url") or result.get("pay_url", ""),
            amount=float(amount),
            asset=asset,
            raw=result,
        )

    async def check_invoice(self, invoice_id: str) -> str:
        result = await self._call("getInvoices", {"invoice_ids": invoice_id})
        items = result.get("items", []) if isinstance(result, dict) else []
        if not items:
            return "pending"
        status = items[0].get("status", "active")
        return {"paid": "paid", "expired": "expired", "active": "pending"}.get(
            status, "pending"
        )

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        secret = hashlib.sha256(self.token.encode()).digest()
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    @staticmethod
    def parse_webhook(payload: dict) -> tuple[str, str]:
        if payload.get("update_type") != "invoice_paid":
            return "", ""
        invoice = payload.get("payload", {})
        return str(invoice.get("invoice_id", "")), "paid"
