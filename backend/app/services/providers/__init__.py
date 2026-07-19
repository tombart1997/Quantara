"""Provider factory — the single place that decides which provider is used."""
from app.core.config import get_settings
from app.services.providers.base import MarketDataProvider
from app.services.providers.mock import MockProvider


def get_provider() -> MarketDataProvider:
    name = get_settings().market_data_provider
    if name == "mock":
        return MockProvider()
    if name == "yfinance":
        from app.services.providers.yfinance import YFinanceProvider
        return YFinanceProvider()
    raise ValueError(f"Unknown market data provider: {name!r}")
