"""AI consultant endpoints.

GET  /api/v1/ai/status     -> is a Kimi API key configured, and which model?
GET  /api/v1/ai/indicators -> the curated cross-reference indicator registry
POST /api/v1/ai/consult    -> data-grounded prompt; with a key, also the answer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.ai_consult import consult
from app.services.indicators import INDICATORS

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class AiStatus(BaseModel):
    configured: bool
    model: str
    base_url: str


class Indicator(BaseModel):
    id: str
    name: str
    watch: str


class AiConsultRequest(BaseModel):
    ticker: str | None = None          # asset context; None = portfolio overview
    question: str | None = Field(default=None, max_length=2000)
    # When set (even empty), switches to cross-reference mode: N indicators
    # vs one asset. Requires ticker. Calendar events are auto-included.
    indicators: list[str] | None = Field(default=None, max_length=len(INDICATORS))


class AiConsultResponse(BaseModel):
    prompt: str
    configured: bool
    model: str
    response: str | None = None        # Kimi's answer (None in prompt-only mode)
    error: str | None = None


@router.get("/status", response_model=AiStatus)
def ai_status() -> AiStatus:
    settings = get_settings()
    return AiStatus(
        configured=bool(settings.kimi_api_key),
        model=settings.kimi_model,
        base_url=settings.kimi_base_url,
    )


@router.get("/indicators", response_model=list[Indicator])
def list_indicators() -> list[dict]:
    """The curated indicator registry for cross-reference analysis."""
    return INDICATORS


@router.post("/consult", response_model=AiConsultResponse)
def ai_consult(payload: AiConsultRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return consult(db, payload.ticker, payload.question, payload.indicators)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
