"""Curated registry of well-known market indicators/themes for
cross-reference analysis.

These are NOT database rows — they are stable, always-relevant lenses
(inflation, Fed policy, positioning, ...) whose cross-asset links are easy to
overlook. The AI receiving the prompt (often pasted into an external chat) is
expected to know what to do with each one; the `watch` field tells it which
concrete metrics matter.
"""
from __future__ import annotations

INDICATORS: list[dict] = [
    {"id": "INFLATION", "name": "Inflation (CPI / PCE)",
     "watch": "US CPI & core CPI YoY, PCE deflator; prints vs consensus and trend."},
    {"id": "FED_POLICY", "name": "Fed policy & rates",
     "watch": "Fed funds target, FOMC guidance/dot plot, rate-cut/hike pricing in fed funds futures."},
    {"id": "YIELD_CURVE", "name": "Yield curve & real yields",
     "watch": "10Y–2Y spread (inversion = recession signal), 10Y real yield (discount rate for valuations)."},
    {"id": "USD_STRENGTH", "name": "US dollar strength (DXY)",
     "watch": "DXY level & trend; strong USD pressures dollar-priced commodities and EM demand."},
    {"id": "RECESSION_FEARS", "name": "Recession risk",
     "watch": "PMIs, initial jobless claims, yield curve, consumer confidence; growth scare vs soft landing."},
    {"id": "ENERGY_PRICES", "name": "Energy prices",
     "watch": "WTI/Brent, natural gas; input-cost channel for agriculture, transport, and margins."},
    {"id": "CHINA_DEMAND", "name": "China demand & stimulus",
     "watch": "China PMI, commodity imports, credit impulse, stimulus measures; key for metals & ags."},
    {"id": "WEATHER_CLIMATE", "name": "Weather & climate (ENSO)",
     "watch": "El Niño/La Niña state, drought indices, rainfall vs normal in growing regions."},
    {"id": "RISK_SENTIMENT", "name": "Risk sentiment (VIX)",
     "watch": "VIX level & term structure, equity put/call ratios; risk-on vs risk-off regime."},
    {"id": "GEOPOLITICS", "name": "Geopolitics & trade policy",
     "watch": "Tariffs, sanctions, export controls, conflicts; supply-disruption premia."},
    {"id": "POSITIONING", "name": "Market positioning (COT)",
     "watch": "CFTC Commitments of Traders net positioning; crowded trades carry unwind risk."},
    {"id": "INVENTORY_STOCKS", "name": "Inventories & stocks",
     "watch": "Exchange warehouse stocks (ICE/LME/COMEX), USDA stocks-to-use ratios; scarcity signal."},
    {"id": "CREDIT_CONDITIONS", "name": "Credit conditions",
     "watch": "High-yield spreads, bank lending standards; financial stress transmission."},
    {"id": "LIQUIDITY", "name": "Global liquidity",
     "watch": "Fed balance sheet (QT/QE), global M2 growth; the tide under all risk assets."},
]

_BY_ID = {i["id"]: i for i in INDICATORS}


def get_indicators(ids: list[str]) -> list[dict]:
    """Resolve indicator ids to registry entries, ignoring unknown ids."""
    return [_BY_ID[i] for i in ids if i in _BY_ID]
