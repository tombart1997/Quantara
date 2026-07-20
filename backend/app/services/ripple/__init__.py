"""Ripple Engine registry — the causal graph, curated by hand.

Design discipline (per project decision): a signal only exists here if its
DETECTOR works with data we actually have (Yahoo prices / Google News RSS).
An edge only exists if its target is an asset we track. Every edge carries
provenance — a graph without provenance is just an opinion with graphics.

Edges are hypotheses with confidence scores, not facts. The confidence
multiplier keeps weakly-evidenced links from dominating scores.
"""
from __future__ import annotations

# --- Signals ---------------------------------------------------------------
# detector kinds:
#   price_change: activation from an asset's N-day % change (threshold..scale -> 0..100)
#   price_level:  activation from an asset's level above a floor
#   news:         activation from 7-day RSS article count for a query
SIGNALS: list[dict] = [
    {
        "id": "RISK_OFF",
        "name": "Risk-off regime",
        "description": "Elevated fear gauge; deleveraging environment for risk assets.",
        "detector": {"kind": "price_level", "ticker": "VIX", "floor": 18.0, "scale": 12.0},
    },
    {
        "id": "USD_STRENGTH",
        "name": "US dollar strengthening",
        "description": "Rising dollar pressures dollar-priced commodities and EM demand.",
        "detector": {"kind": "price_change", "ticker": "DXY", "days": 30, "threshold": 0.5, "scale": 2.5},
    },
    {
        "id": "OIL_SHOCK",
        "name": "Oil price shock",
        "description": "Sharp crude move; input-cost and inflation transmission.",
        "detector": {"kind": "price_change", "ticker": "CL", "days": 30, "threshold": 4.0, "scale": 10.0},
    },
    {
        "id": "COCOA_SUPPLY_STRESS",
        "name": "Cocoa supply stress",
        "description": "Tight cocoa market pricing — weather, disease, or structural deficit.",
        "detector": {"kind": "price_change", "ticker": "CC", "days": 30, "threshold": 5.0, "scale": 15.0},
    },
    {
        "id": "RATES_PRESSURE",
        "name": "Rising long-term rates",
        "description": "10Y yield rising; discount-rate pressure on long-duration assets.",
        "detector": {"kind": "price_change", "ticker": "TNX", "days": 30, "threshold": 3.0, "scale": 8.0},
    },
    {
        "id": "AI_DATACENTER",
        "name": "AI / datacenter buildout momentum",
        "description": "Compute investment cycle; semiconductors and the power/grid chain.",
        "detector": {"kind": "price_change", "ticker": "NVDA", "days": 30, "threshold": 5.0, "scale": 15.0},
    },
    {
        "id": "SAFE_HAVEN_BID",
        "name": "Safe-haven demand",
        "description": "Capital rotating into gold; usually mirrors stress elsewhere.",
        "detector": {"kind": "price_change", "ticker": "GC", "days": 30, "threshold": 2.0, "scale": 6.0},
    },
    {
        "id": "EL_NINO",
        "name": "El Niño / climate anomaly",
        "description": "ENSO-driven weather disruption in growing regions.",
        "detector": {"kind": "news", "query": "El Niño La Niña weather", "full_scale_articles": 15},
    },
    {
        "id": "TARIFFS",
        "name": "Tariff / trade-war escalation",
        "description": "Trade policy shocks; export exposure and supply-chain friction.",
        "detector": {"kind": "news", "query": "tariffs trade war", "full_scale_articles": 20},
    },
    {
        "id": "RECESSION",
        "name": "Recession fears",
        "description": "Growth-scare narrative; demand destruction channel.",
        "detector": {"kind": "news", "query": "recession fears economy", "full_scale_articles": 20},
    },
]

# --- Edges -------------------------------------------------------------------
# (signal, ticker, direction, magnitude%, lag, confidence 0-1, order, provenance)
# order: 1 = direct (decay 1.0), 2 = second-order (0.5), 3 = third-order (0.25)
EDGES: list[tuple] = [
    # RISK_OFF — broad deleveraging
    ("RISK_OFF", "SPX", -1, 6, "immediate", 0.9, 1, "VIX regimes: high-VIX windows have negative equity risk premia (Whaley, 2000)"),
    ("RISK_OFF", "NDX", -1, 7, "immediate", 0.85, 1, "High-beta growth underperforms in VIX spikes (2020, 2022 episodes)"),
    ("RISK_OFF", "DJI", -1, 5, "immediate", 0.85, 1, "Defensive tilt cushions but does not avoid drawdowns"),
    ("RISK_OFF", "RUT", -1, 8, "immediate", 0.8, 1, "Small-caps underperform in risk-off (liquidity premium)"),
    ("RISK_OFF", "DAX", -1, 6, "immediate", 0.8, 1, "Global equity correlation converges to ~1 in stress"),
    ("RISK_OFF", "N225", -1, 6, "immediate", 0.75, 1, "Same global stress correlation"),
    ("RISK_OFF", "HSI", -1, 7, "immediate", 0.75, 1, "EM/Asia beta amplifies global risk-off"),
    ("RISK_OFF", "GC", +1, 3, "immediate", 0.7, 1, "Safe-haven flows into gold during VIX spikes"),
    ("RISK_OFF", "SSO", -1, 11, "immediate", 0.9, 2, "2x daily leverage mechanically doubles SPX path"),
    ("RISK_OFF", "QLD", -1, 13, "immediate", 0.9, 2, "2x daily leverage mechanically doubles NDX path"),
    ("RISK_OFF", "DDM", -1, 9, "immediate", 0.9, 2, "2x daily leverage mechanically doubles DJI path"),

    # USD_STRENGTH — dollar-priced commodities
    ("USD_STRENGTH", "GC", -1, 3, "3m", 0.75, 1, "Gold is USD-priced; strong dollar historically pressures it (DXY correlation studies)"),
    ("USD_STRENGTH", "CC", -1, 3, "3m", 0.6, 1, "Dollar-priced soft commodity; same mechanical channel"),
    ("USD_STRENGTH", "SI", -1, 4, "3m", 0.7, 1, "Silver shows higher beta to USD than gold"),
    ("USD_STRENGTH", "HG", -1, 3, "3m", 0.65, 1, "Copper inversely correlated with DXY over cycles"),
    ("USD_STRENGTH", "CL", -1, 3, "3m", 0.6, 1, "Oil invoiced in USD; demand channel via EM purchasing power"),

    # OIL_SHOCK
    ("OIL_SHOCK", "CL", +1, 10, "immediate", 0.95, 1, "The signal IS the crude move"),
    ("OIL_SHOCK", "UCO", +1, 19, "immediate", 0.9, 2, "2x daily leverage on crude-linked fund"),
    ("OIL_SHOCK", "SPX", -1, 2, "3m", 0.55, 2, "Energy input costs squeeze margins (1970s, 2008, 2022 episodes)"),
    ("OIL_SHOCK", "GC", +1, 2, "3m", 0.5, 2, "Oil shocks transmit to inflation expectations -> gold bid"),
    ("OIL_SHOCK", "TAN", -1, 2, "3m", 0.4, 3, "Higher rates from energy inflation pressure renewables valuations"),

    # COCOA_SUPPLY_STRESS
    ("COCOA_SUPPLY_STRESS", "CC", +1, 15, "immediate", 0.95, 1, "The signal IS the cocoa move"),
    ("COCOA_SUPPLY_STRESS", "KC", +1, 3, "3m", 0.4, 2, "Softs sympathy trade; shared West Africa weather exposure"),
    ("COCOA_SUPPLY_STRESS", "SB", +1, 2, "3m", 0.35, 2, "Soft-basket correlation in commodity indices"),

    # RATES_PRESSURE
    ("RATES_PRESSURE", "NDX", -1, 5, "immediate", 0.8, 1, "Long-duration growth de-rates when discount rates rise (2022)"),
    ("RATES_PRESSURE", "NVDA", -1, 5, "immediate", 0.7, 1, "High-multiple tech is duration-sensitive"),
    ("RATES_PRESSURE", "QLD", -1, 9, "immediate", 0.85, 2, "2x NDX leverage"),
    ("RATES_PRESSURE", "GC", -1, 3, "immediate", 0.65, 1, "Real-yield channel: higher real rates hurt zero-yield gold"),
    ("RATES_PRESSURE", "TAN", -1, 5, "immediate", 0.7, 1, "Renewables are financed like long-duration infrastructure"),
    ("RATES_PRESSURE", "ICLN", -1, 5, "immediate", 0.7, 1, "Same duration channel as TAN"),
    ("RATES_PRESSURE", "SPX", -1, 3, "immediate", 0.7, 1, "Broad equity multiple compression"),

    # AI_DATACENTER
    ("AI_DATACENTER", "NVDA", +1, 15, "immediate", 0.95, 1, "The signal IS NVDA momentum"),
    ("AI_DATACENTER", "NVDL", +1, 28, "immediate", 0.9, 2, "2x daily NVDA leverage — mechanical"),
    ("AI_DATACENTER", "QLD", +1, 4, "3m", 0.6, 2, "NVDA is a top QQQ holding; index pull-through"),
    ("AI_DATACENTER", "QTUM", +1, 3, "3m", 0.45, 2, "Compute-theme sympathy (quantum/next-gen compute)"),
    ("AI_DATACENTER", "HG", +1, 3, "12m", 0.55, 3, "Datacenter electrification -> copper demand (grid buildout studies)"),
    ("AI_DATACENTER", "SPX", +1, 2, "3m", 0.55, 2, "Mega-cap weight drives index"),

    # SAFE_HAVEN_BID
    ("SAFE_HAVEN_BID", "GC", +1, 6, "immediate", 0.95, 1, "The signal IS the gold move"),
    ("SAFE_HAVEN_BID", "UGL", +1, 11, "immediate", 0.9, 2, "2x gold leverage — mechanical"),
    ("SAFE_HAVEN_BID", "SI", +1, 4, "immediate", 0.6, 1, "Silver correlates with gold in haven flows"),
    ("SAFE_HAVEN_BID", "AGQ", +1, 8, "immediate", 0.85, 2, "2x silver leverage — mechanical"),

    # EL_NINO — soft commodity supply
    ("EL_NINO", "CC", +1, 10, "3m", 0.65, 1, "2015-16 El Niño: West Africa dryness cut cocoa output; prices rallied"),
    ("EL_NINO", "KC", +1, 6, "3m", 0.5, 1, "ENSO alters Brazil/Vietnam coffee rainfall"),
    ("EL_NINO", "SB", +1, 5, "3m", 0.45, 1, "ENSO disrupts cane-growing rainfall patterns"),
    ("EL_NINO", "ZW", +1, 4, "3m", 0.4, 2, "Global grain weather correlation under ENSO"),
    ("EL_NINO", "ZC", +1, 4, "3m", 0.4, 2, "US Midwest precipitation shifts under El Niño"),

    # TARIFFS
    ("TARIFFS", "HSI", -1, 5, "immediate", 0.7, 1, "Export-exposed Asia de-rates on trade escalation (2018-19)"),
    ("TARIFFS", "N225", -1, 4, "immediate", 0.65, 1, "Japan export sector sensitive to trade friction"),
    ("TARIFFS", "SPX", -1, 3, "immediate", 0.6, 1, "2018-19 tariff rounds coincided with equity drawdowns"),
    ("TARIFFS", "NVDA", -1, 5, "immediate", 0.65, 1, "Chip export controls hit AI-chip sales abroad directly"),
    ("TARIFFS", "DAX", -1, 4, "immediate", 0.65, 1, "Germany is export-heavy; auto/industrial exposure"),

    # RECESSION
    ("RECESSION", "SPX", -1, 5, "3m", 0.7, 1, "Earnings downgrades follow growth scares"),
    ("RECESSION", "RUT", -1, 7, "3m", 0.7, 1, "Small-caps most sensitive to domestic growth"),
    ("RECESSION", "CC", -1, 4, "3m", 0.5, 2, "Demand destruction: recession cuts chocolate demand (2008, 2020 grind data)"),
    ("RECESSION", "CL", -1, 5, "3m", 0.6, 2, "Oil demand falls in recessions"),
    ("RECESSION", "HG", -1, 6, "3m", 0.65, 1, "Copper is the classic cyclical demand proxy ('Dr. Copper')"),
    ("RECESSION", "GC", +1, 3, "3m", 0.55, 1, "Safe-haven / rate-cut-anticipation bid"),
]

# Decay per hop — first-order full strength, then attenuation.
ORDER_DECAY = {1: 1.0, 2: 0.5, 3: 0.25}

_SIGNALS_BY_ID = {s["id"]: s for s in SIGNALS}


def get_signal(signal_id: str) -> dict | None:
    return _SIGNALS_BY_ID.get(signal_id)


def edges_for_signal(signal_id: str) -> list[tuple]:
    return [e for e in EDGES if e[0] == signal_id]


def edges_for_ticker(ticker: str) -> list[tuple]:
    return [e for e in EDGES if e[1] == ticker]
