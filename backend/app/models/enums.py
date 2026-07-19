"""Shared enumerations for the domain models.

Python enums are stored via sa.Enum(..., native_enum=False), i.e. as VARCHAR
with a CHECK constraint. This behaves the same on SQLite and PostgreSQL and
avoids the migration pain of native Postgres enum types.
"""
import enum


class AssetType(str, enum.Enum):
    STOCK = "STOCK"
    COMMODITY = "COMMODITY"
    ETF = "ETF"
    INDEX = "INDEX"


class EventType(str, enum.Enum):
    EARNINGS = "EARNINGS"
    ECONOMIC_RELEASE = "ECONOMIC_RELEASE"        # CPI, FOMC, jobs report, ...
    COMPANY_ANNOUNCEMENT = "COMPANY_ANNOUNCEMENT"
    COMMODITY_REPORT = "COMMODITY_REPORT"        # ICCO, USDA WASDE, OPEC, ...
    WEATHER = "WEATHER"                          # relevant for soft commodities


class Recurrence(str, enum.Enum):
    """How often an event repeats. NONE = one-off."""
    NONE = "NONE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
