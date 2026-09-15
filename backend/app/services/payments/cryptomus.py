import base64
import hashlib
import json
import uuid

import httpx

from app.services.payments.base import Invoice, PaymentProvider, ProviderError

API_URL = "https://api.cryptomus.com/v1"

NETWORKS = {
    "TRC20": "tron",
    "BEP20": "bsc",
    "ERC20": "eth",
    "TON": "ton",
}

class CryptomusProvider(PaymentProvider):
    name = "cryptomus"
    supported_assets = ("USDT", "BTC", "ETH", "TON", "LTC")

    def __init__(self, api_key: str, merchant_id: str, network: str, public_url: str):
        self.api_key = api_key
        self.merchant_id = merchant_id
        self.network = NETWORKS.get(network.upper(), "tron")
        self.public_url = public_url.rstrip("/")

    def _sign(self, body: dict) -> str:
        raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        encoded = base64.b64encode(raw.encode()).decode()
        return hashlib.md5((encoded + self.api_key).encode()).hexdigest()

    async def _call(self, path: str, body: dict) -> dict:
        headers = {
            "merchant": self.merchant_id,
            "sign": self._sign(body),
            "Content-Type": "application/json",
        }
        content = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(
                    f"{API_URL}{path}", content=content, headers=headers
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Cryptomus: сеть — {exc}") from exc

        data = res.json()
        if data.get("state") != 0:
            message = data.get("message") or data.get("errors")
            raise ProviderError(f"Cryptomus: {message}")
        return data.get("result", {})

    async def create_invoice(
        self, amount_usd: float, asset: str, description: str, payload: str
    ) -> Invoice:
        asset = asset.upper()
        body: dict = {
            "amount": f"{amount_usd:.2f}",
            "currency": "USD",
            "order_id": f"{payload}-{uuid.uuid4().hex[:8]}",
            "to_currency": asset,
            "lifetime": 3600,
        }
        if asset == "USDT":
            body["network"] = self.network
        if self.public_url:
            body["url_callback"] = f"{self.public_url}/api/webhooks/cryptomus"

        result = await self._call("/payment", body)

        return Invoice(
            invoice_id=str(result.get("uuid", "")),
            pay_url=result.get("url", ""),
            amount=float(result.get("payer_amount") or amount_usd),
            asset=asset,
            network=body.get("network", ""),
            raw=result,
        )

    async def check_invoice(self, invoice_id: str) -> str:
        result = await self._call("/payment/info", {"uuid": invoice_id})
        status = (result.get("payment_status") or "").lower()
        if status in {"paid", "paid_over"}:
            return "paid"
        if status in {"cancel", "fail", "system_fail", "wrong_amount"}:
            return "failed"
        if status in {"expired", "refund_process"}:
            return "expired"
        return "pending"

    def verify_webhook(self, payload: dict) -> bool:
        sign = payload.pop("sign", "")
        return sign == self._sign(payload)
