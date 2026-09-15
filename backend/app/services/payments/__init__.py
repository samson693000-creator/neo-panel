from sqlalchemy.ext.asyncio import AsyncSession

from app.services.payments.base import Invoice, PaymentProvider, ProviderError
from app.services.payments.cryptomus import CryptomusProvider
from app.services.payments.cryptopay import CryptoPayProvider
from app.services.payments.test_provider import TestProvider
from app.services.settings_service import SettingsService

async def get_provider(session: AsyncSession) -> PaymentProvider:
    svc = SettingsService(session)
    name = (await svc.get("payment_provider", "test")).lower()
    test_mode = await svc.get_bool("payments_test_mode", True)

    if test_mode or name == "test":
        return TestProvider()

    if name == "cryptopay":
        token = await svc.get("cryptopay_token")
        if not token:
            raise ProviderError("Crypto Pay token не задан в настройках")
        return CryptoPayProvider(token)

    if name == "cryptomus":
        api_key = await svc.get("cryptomus_api_key")
        merchant = await svc.get("cryptomus_merchant_id")
        network = await svc.get("usdt_network", "TRC20")
        public_url = await svc.get("public_url")
        if not api_key or not merchant:
            raise ProviderError("Cryptomus: не заданы API key и merchant ID")
        return CryptomusProvider(api_key, merchant, network, public_url)

    raise ProviderError(f"Неизвестный платёжный провайдер: {name}")

__all__ = [
    "Invoice",
    "PaymentProvider",
    "ProviderError",
    "get_provider",
    "TestProvider",
    "CryptoPayProvider",
    "CryptomusProvider",
]
