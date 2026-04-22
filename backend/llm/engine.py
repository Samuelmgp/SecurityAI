"""Ollama inference engine with token streaming support.

Ollama wraps llama.cpp under the hood, handling model loading, quantization,
and memory management. For memory-constrained devices the recommended model is
phi3.5:mini (~2.3 GB RAM). Pull it with: ollama pull phi3.5:mini
"""
import json
import logging
from typing import AsyncIterator

import httpx

from config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)


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


async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    """Yield response tokens one by one from Ollama's streaming chat API."""
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.3,   # lower → more deterministic for security facts
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
