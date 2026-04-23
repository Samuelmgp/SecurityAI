"""SecurityAI backend — FastAPI + RAG + Ollama."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_ingest_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest")


async def _run_ingest() -> None:
    from rag.ingest import ingest_all
    logger.info("Ingesting textbooks from %s (background) …", settings.books_path)
    loop = asyncio.get_running_loop()
    try:
        results = await loop.run_in_executor(_ingest_executor, ingest_all)
        for book, count in results.items():
            if count > 0:
                logger.info("  %s → %d new chunks indexed", book, count)
            elif count == 0:
                logger.info("  %s → already indexed, nothing new", book)
            else:
                logger.warning("  %s → ingestion failed", book)
    except Exception:
        logger.exception("Textbook ingestion failed — RAG will work with existing data only")


async def _run_warmup() -> None:
    from llm.engine import warmup_model
    logger.info("Warming up model '%s' …", settings.ollama_model)
    await warmup_model()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SecurityAI backend …")
    asyncio.create_task(_run_ingest())
    asyncio.create_task(_run_warmup())
    yield
    logger.info("Shutting down …")
    _ingest_executor.shutdown(wait=False)


app = FastAPI(
    title="SecurityAI",
    description="Lightweight security assistant grounded in curated textbooks.",
    version="0.1.0",
    lifespan=lifespan,
)

from api.chat import router as chat_router          # noqa: E402
from api.health import router as health_router      # noqa: E402
from api.outcomes import router as outcomes_router  # noqa: E402

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
