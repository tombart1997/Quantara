"""Event provider factory — combines all configured sources.

Yahoo earnings is always active (no key needed). Finnhub macro calendar
activates automatically once FINNHUB_API_KEY is set.
"""
from app.core.config import get_settings
from app.services.event_providers.base import EventProvider
from app.services.event_providers.finnhub_calendar import FinnhubCalendarProvider
from app.services.event_providers.yahoo_earnings import YahooEarningsProvider


def get_event_providers() -> list[EventProvider]:
    providers: list[EventProvider] = [YahooEarningsProvider()]
    if get_settings().finnhub_api_key:
        providers.append(FinnhubCalendarProvider())
    return providers
