"""Ollama inference engine with token streaming support.

Ollama wraps llama.cpp under the hood, handling model loading, quantization,
and memory management. For memory-constrained devices the recommended model is
phi3:mini (~2.3 GB RAM). Pull it with: ollama pull phi3:mini
"""
import json
import logging
from typing import AsyncIterator

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Generous timeouts — Ollama loads the model into RAM on the first request
# which can take 15-30 s on CPU-only hardware.
_TIMEOUT = httpx.Timeout(connect=60.0, read=300.0, write=30.0, pool=10.0)

# Warmup uses an even longer connect window; the model may not be in RAM yet.
_WARMUP_TIMEOUT = httpx.Timeout(connect=120.0, read=120.0, write=10.0, pool=10.0)


async def is_available() -> tuple[bool, str]:
    """Check that Ollama is running and the configured model is pulled."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            model_base = settings.ollama_model.split(":")[0]
            found = any(m.startswith(model_base) for m in models)
            if not found:
                return False, (
                    f"Model '{settings.ollama_model}' not pulled. "
                    f"Run: ollama pull {settings.ollama_model}"
                )
            return True, "ok"
    except httpx.ConnectError:
        return False, "Ollama is not running. Install from https://ollama.com and start with: ollama serve"
    except Exception as exc:
        return False, str(exc)


async def warmup_model() -> None:
    """Send a minimal request so Ollama pages the model into RAM before the
    first real user query arrives.  Failure is non-fatal — the model will
    simply load on demand instead."""
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
        "options": {"num_predict": 1},
    }
    try:
        async with httpx.AsyncClient(timeout=_WARMUP_TIMEOUT) as client:
            r = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
            r.raise_for_status()
        logger.info("Model '%s' is warm and ready.", settings.ollama_model)
    except Exception as exc:
        logger.warning("Model warmup skipped (%s) — will load on first request.", exc)


async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    """Yield response tokens one by one from Ollama's streaming chat API."""
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.3,
            "top_p": 0.9,
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        async with client.stream(
            "POST",
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = data.get("message", {}).get("content", "")
                if token:
                    yield token

                if data.get("done"):
                    break
