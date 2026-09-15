import uuid

from app.services.payments.base import Invoice, PaymentProvider

class TestProvider(PaymentProvider):
    name = "test"

    async def create_invoice(
        self, amount_usd: float, asset: str, description: str, payload: str
    ) -> Invoice:
        invoice_id = f"test-{uuid.uuid4().hex[:12]}"
        return Invoice(
            invoice_id=invoice_id,
            pay_url="",
            amount=round(amount_usd, 2),
            asset=asset,
            raw={"mode": "test", "description": description, "payload": payload},
        )

    async def check_invoice(self, invoice_id: str) -> str:
        return "pending"
