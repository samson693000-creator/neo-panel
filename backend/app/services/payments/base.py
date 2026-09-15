from abc import ABC, abstractmethod
from dataclasses import dataclass, field

class ProviderError(Exception):
    pass

@dataclass
class Invoice:
    invoice_id: str
    pay_url: str
    amount: float
    asset: str
    network: str = ""
    raw: dict = field(default_factory=dict)

class PaymentProvider(ABC):
    name: str = "base"
    supported_assets: tuple[str, ...] = ("USDT", "BTC")

    @abstractmethod
    async def create_invoice(
        self,
        amount_usd: float,
        asset: str,
        description: str,
        payload: str,
    ) -> Invoice:
        ...

    @abstractmethod
    async def check_invoice(self, invoice_id: str) -> str:
        ...

    async def close(self) -> None:
        return None
