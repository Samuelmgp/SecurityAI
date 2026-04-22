"""SecurityAI backend — FastAPI + RAG + Ollama."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.chat import router as chat_router
from api.health import router as health_router
from api.outcomes import router as outcomes_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SecurityAI backend …")
    logger.info("Ingesting textbooks from %s …", settings.books_path)
    try:
        from rag.ingest import ingest_all
        results = ingest_all()
        for book, count in results.items():
            if count > 0:
                logger.info("  %s → %d new chunks", book, count)
            elif count == 0:
                logger.info("  %s → already indexed (0 new chunks)", book)
            else:
                logger.warning("  %s → ingestion failed", book)
    except Exception:
        logger.exception("Textbook ingestion failed — RAG will be limited")
    yield
    logger.info("Shutting down …")


app = FastAPI(
    title="SecurityAI",
    description="Lightweight security assistant grounded in curated textbooks.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(outcomes_router)
