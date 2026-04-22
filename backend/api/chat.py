"""SSE streaming chat endpoint.

The frontend connects via fetch() + ReadableStream.
Each SSE event is either a token delta or a final [DONE] marker with source metadata.
"""
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm.engine import stream_chat, is_available
from llm.prompt import build_prompt
from rag.retriever import retrieve, format_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class HistoryTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    history: list[HistoryTurn] = []
    category: str = "general"


async def _event_stream(request: ChatRequest):
    llm_ok, llm_msg = await is_available()
    if not llm_ok:
        error_event = f"data: {json.dumps({'error': llm_msg})}\n\n"
        yield error_event
        return

    # RAG retrieval
    chunks = retrieve(request.query)
    context = format_context(chunks)

    # Build sources list for the frontend
    sources = [
        {"book": c.book, "page": c.page, "type": c.source_type}
        for c in chunks
        if c.score > 0.3
    ]

    history = [{"role": t.role, "content": t.content} for t in request.history]
    messages = build_prompt(request.query, context, history)

    try:
        async for token in stream_chat(messages):
            yield f"data: {json.dumps({'token': token})}\n\n"
    except Exception as exc:
        logger.exception("LLM stream error")
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        return

    # Final event carries source metadata
    yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
