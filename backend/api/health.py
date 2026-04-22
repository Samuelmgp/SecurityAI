from fastapi import APIRouter
from pydantic import BaseModel

from config import settings
from llm.engine import is_available
from rag.ingest import get_collection
from learning.store import get_outcomes_collection

router = APIRouter(prefix="/api")


class HealthResponse(BaseModel):
    status: str
    llm_available: bool
    llm_message: str
    model: str
    textbook_chunks: int
    outcome_count: int


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    llm_ok, llm_msg = await is_available()

    try:
        tb_count = get_collection().count()
    except Exception:
        tb_count = 0

    try:
        oc_count = get_outcomes_collection().count()
    except Exception:
        oc_count = 0

    return HealthResponse(
        status="ok" if llm_ok else "degraded",
        llm_available=llm_ok,
        llm_message=llm_msg,
        model=settings.ollama_model,
        textbook_chunks=tb_count,
        outcome_count=oc_count,
    )
