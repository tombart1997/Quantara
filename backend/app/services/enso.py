"""Official ENSO status from NOAA's Climate Prediction Center.

The CPC ENSO Diagnostic Discussion page carries the official Alert System
status (El Niño Advisory / La Niña Watch / ENSO-Neutral) plus a synopsis
with probabilities. We extract the status line — no API key, one HTTP GET.

The detector only trusts the official status; page-layout changes degrade
it gracefully to 'unavailable' rather than guessing.
"""
from __future__ import annotations

import html
import logging
import re
import time

import httpx

logger = logging.getLogger(__name__)

CPC_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml"
CACHE_TTL = 6 * 3600  # advisory updates roughly monthly
_cache: tuple[float, dict] | None = None

_STATUS_PATTERNS = [
    (r"El Ni.o Advisory", ("EL_NINO", 80.0)),
    (r"La Ni.a Advisory", ("LA_NINA", 80.0)),
    (r"El Ni.o Watch", ("EL_NINO", 40.0)),
    (r"La Ni.a Watch", ("LA_NINA", 40.0)),
    (r"ENSO-neutral", ("NEUTRAL", 0.0)),
]


def get_enso_status() -> dict:
    """Official ENSO state: {state, activation, detail} (cached 6h)."""
    global _cache
    now = time.time()
    if _cache and now - _cache[0] < CACHE_TTL:
        return _cache[1]

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(CPC_URL)
            resp.raise_for_status()
            # CPC serves windows-1252; decode accordingly to keep ñ intact.
            text = resp.content.decode("cp1252", errors="replace")
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(text)))
    except Exception as e:
        logger.warning("CPC ENSO page fetch failed: %s", e)
        result = {"state": "UNAVAILABLE", "activation": 0.0,
                  "detail": "CPC advisory page unreachable"}
        _cache = (now, result)
        return result

    for pattern, (state, activation) in _STATUS_PATTERNS:
        if re.search(pattern, plain, re.IGNORECASE):
            synopsis = ""
            m = re.search(r"Synopsis:\s*([^|]{10,300}?)(?:\. |\|)", plain)
            if m:
                synopsis = m.group(1).strip() + "."
            result = {
                "state": state,
                "activation": activation,
                "detail": f"NOAA CPC status: {state.replace('_', ' ')}"
                          + (f" — {synopsis}" if synopsis else ""),
            }
            _cache = (now, result)
            return result

    result = {"state": "UNPARSEABLE", "activation": 0.0,
              "detail": "CPC page layout changed; status not found"}
    _cache = (now, result)
    return result
