"""AI consultant endpoints.

GET  /api/v1/ai/status  -> is a Kimi API key configured, and which model?
POST /api/v1/ai/consult -> data-grounded prompt; with a key, also the answer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.ai_consult import consult

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class AiStatus(BaseModel):
    configured: bool
    model: str
    base_url: str


class AiConsultRequest(BaseModel):
    ticker: str | None = None          # asset context; None = portfolio overview
    question: str | None = Field(default=None, max_length=2000)
    # When set, switches to cross-reference mode: N events vs one asset.
    # Requires ticker. Capped to keep prompts sane.
    event_ids: list[int] | None = Field(default=None, max_length=20)


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


@router.post("/consult", response_model=AiConsultResponse)
def ai_consult(payload: AiConsultRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return consult(db, payload.ticker, payload.question, payload.event_ids)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
