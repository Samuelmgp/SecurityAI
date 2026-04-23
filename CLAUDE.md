# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SecurityAI is a domain-specific AI assistant for secure application development and penetration testing. Knowledge comes from two security textbooks (`book_data/`). The system is designed to run on memory-constrained devices. The end goal is a fine-tuned local LLM with textbook knowledge baked into its weights, augmented by a RAG layer for continual learning from test outcomes.

---

## Current State (as of last session)

### Done
- **Frontend** — React 19 + TypeScript + Tailwind CSS v4 + Vite 6 (dark cyber theme, SSE streaming chat)
- **Backend** — FastAPI + Ollama RAG pipeline (ChromaDB + fastembed BGE embeddings)
- **Docker** — 4-service compose: `ollama`, `ollama-init`, `backend`, `frontend`
- **Data pipeline** — PDF → clean text → paragraph chunks → Claude QA generation → JSONL dataset
- **Colab notebook** — `notebooks/finetune_securityai.ipynb` QLoRA fine-tune ready to run

### Pending / Next session priorities
1. **Run the Colab notebook** to produce `securityai.Q4_K_M.gguf`
2. **Register the GGUF with Ollama** (`ollama create securityai -f Modelfile`) and update `OLLAMA_MODEL=securityai`
3. **Fix the Ollama 500 error** — context overflow is the root cause (see Outstanding Issues below). These RAG changes were agreed on but not yet implemented.
4. **Outcomes UI** — a simple panel in the frontend for recording test/scenario results to the learning store

### Outstanding issues (NOT yet fixed)
**Ollama returns HTTP 500 after ~55s on the first chat request.**
Root cause: context overflow. We're injecting 5 chunks × ~400 words ≈ 2600 tokens into phi3:mini's 4096-token window leaving almost no room for output. The KV cache allocation pushes us to the 6 GB container limit.

Agreed fixes (implement at start of next session):
- `config.py`: `CHUNK_SIZE=200`, `TOP_K_RESULTS=3`
- `rag/retriever.py`: add `min_score=0.40` threshold — skip low-confidence chunks
- `llm/engine.py` options: `num_ctx: 2048` (halves KV cache memory)
- `llm/prompt.py`: cap `history` to last 4 messages
- `rag/ingest.py`: add PDF hash manifest so startup skips already-indexed books without checking every chunk ID (currently O(pages × chunks) DB reads on startup)

---

## Commands

### Docker — full stack
```bash
docker compose up --build          # first run: pulls phi3:mini (~2.3 GB), ingests PDFs
docker compose up                  # subsequent runs (volumes persist)
docker compose down                # stop, keep volumes
docker compose down -v             # stop + wipe volumes (model + vector DB)
OLLAMA_MODEL=securityai docker compose up   # use fine-tuned model
```
Access: frontend → http://localhost | backend → http://localhost:8000 | Ollama → http://localhost:11434

### Local dev (no Docker)
```bash
# Terminal 1 — frontend
npm run dev         # http://localhost:5173
npm run build       # TypeScript check + production build
npm run lint

# Terminal 2 — backend
cd backend
source .venv/bin/activate
uvicorn main:app --reload   # http://localhost:8000
# Requires backend/.env with OLLAMA_BASE_URL, OLLAMA_MODEL, ANTHROPIC_API_KEY

# Terminal 3 — Ollama
ollama serve
ollama pull phi3:mini       # or: ollama pull securityai (after fine-tuning)
```

### Data generation pipeline
```bash
cd backend
source .venv/bin/activate
python generate_dataset.py --dry-run        # preview: chunk counts + cost estimate
python generate_dataset.py                  # full run (~35 min, ~$3.77)
python generate_dataset.py --n-pairs 4     # 4 QA pairs per chunk
# Requires ANTHROPIC_API_KEY in backend/.env
# Output: backend/data/dataset/{train,test,raw_qa_pairs}.jsonl + stats.json
```

### Fine-tuning (Google Colab)
```
1. Open notebooks/finetune_securityai.ipynb in Google Colab
2. Runtime → Change runtime type → T4 GPU
3. Upload train.jsonl and test.jsonl from backend/data/dataset/
4. Run all cells (~60 min on free T4)
5. Download securityai-unsloth.Q4_K_M.gguf + Modelfile
```

### Load fine-tuned model into Ollama (local)
```bash
mv securityai-unsloth.Q4_K_M.gguf backend/models/
mv Modelfile backend/models/
cd backend/models
ollama create securityai -f Modelfile
ollama run securityai "What is a buffer overflow?"
# Then set OLLAMA_MODEL=securityai in backend/.env
```

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Tailwind CSS v4, Vite 6, lucide-react |
| Markdown/code | react-markdown, react-syntax-highlighter (Prism, oneDark) |
| Backend | FastAPI, uvicorn, Python 3.13 |
| Inference | Ollama (llama.cpp) — default `phi3:mini`, target `securityai` (fine-tuned) |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5` (ONNX Runtime, ~50 MB) |
| Vector store | ChromaDB (embedded, persistent) |
| PDF parsing | PyMuPDF (fitz) |
| Data generation | Anthropic SDK — `claude-haiku-4-5` with tool use + prompt caching |
| Fine-tuning | Unsloth + QLoRA (Google Colab T4) |
| Orchestration | Docker Compose (4 services) |

---

## Architecture

```
src/                               Frontend (React)
  types/index.ts                   Shared types: Message, Conversation, Category, Source
  hooks/useConversation.ts         Conversation CRUD + streaming message mutation
  components/
    Sidebar.tsx                    Category filter + conversation history
    ChatWindow.tsx                 Message list + per-category empty-state prompts
    MessageBubble.tsx              Markdown + syntax-highlighted code + source badges
    ChatInput.tsx                  Auto-resizing textarea, Enter to send
  App.tsx                          SSE stream consumer; AbortController 60s timeout

backend/
  main.py                          FastAPI app; fires ingest + warmup as background tasks
  config.py                        pydantic-settings (reads backend/.env)
  api/
    chat.py      POST /api/chat    SSE: RAG retrieve → prompt build → Ollama token stream
    health.py    GET  /api/health  LLM availability + chunk/outcome counts
    outcomes.py  POST/GET /api/outcomes
  rag/
    ingest.py                      PDF → page text → chunks → embed → ChromaDB (idempotent)
    chunker.py                     Word-count splitter with overlap
    retriever.py                   Cosine search across textbooks + outcomes collections
  llm/
    engine.py                      Ollama /api/chat wrapper; warmup_model() on startup
    prompt.py                      System prompt + RAG context injection
  learning/
    store.py                       Outcomes ChromaDB collection
  data_pipeline/
    cleaner.py                     Strip PDF noise (headers, footers, page numbers)
    splitter.py                    Paragraph-aware chunking (never cuts mid-sentence)
    qa_generator.py                Claude claude-haiku-4-5 + tool use → structured QAPairs
    pipeline.py                    End-to-end orchestration → train.jsonl + test.jsonl
  generate_dataset.py              CLI entry point

notebooks/
  finetune_securityai.ipynb        QLoRA fine-tune on Colab T4 → GGUF export
```

### Request lifecycle (current RAG mode)
1. Frontend `POST /api/chat` with `{query, history[], category}`
2. `retriever.retrieve(query)` — cosine search across **textbooks** + **outcomes** collections
3. Top chunks formatted into context block, injected into system prompt
4. Messages sent to Ollama streaming API; tokens yielded as SSE `data: {"token": "..."}` events
5. Final SSE event: `data: {"done": true, "sources": [...]}` — frontend attaches source badges
6. Tokens stream into a pre-allocated assistant message slot via `updateLastAssistantMessage`

### Request lifecycle (after fine-tuning)
Steps 2–3 change: retriever only queries the **outcomes** collection (textbook knowledge is in model weights). Context is much shorter → no more context overflow.

### Docker service startup order
```
ollama (healthcheck: ollama list)
  └─► ollama-init (pulls model, exits 0 — skipped on re-runs, model cached in volume)
        └─► backend (service_started, not service_healthy — healthcheck removed)
              └─► frontend (nginx, port 80)
```

nginx proxies `/api/*` → `backend:8000` with `proxy_buffering off` for SSE.
Frontend built with `VITE_API_URL=""` → all API calls use relative paths through nginx.

### Continual learning
`POST /api/outcomes` embeds a scenario+result+lesson in the `outcomes` ChromaDB collection. Retrieved alongside (or instead of, post fine-tune) textbook passages on every query.

### Adding a new LLM engine
`llm/engine.py` exposes `is_available()` and `stream_chat(messages)`. Implement the same interface to swap backends (e.g. llama-cpp-python direct). Update imports in `api/chat.py`.

---

## Key design decisions (rationale for future sessions)

| Decision | Why |
|---|---|
| fastembed over sentence-transformers | sentence-transformers pulls PyTorch (~2 GB); fastembed uses ONNX Runtime (~50 MB) — critical for Docker build time and memory |
| Ingestion as background asyncio task | Running it synchronously blocked uvicorn from serving health checks, causing Docker to mark the container unhealthy before it was ready |
| AbortController 60s frontend timeout | Ollama's first inference after a cold start can take 15–30s to page the model into RAM; 60s gives it room while still failing gracefully |
| `HEALTHCHECK` removed from backend Dockerfile | Docker was running `wget` every 10s; removed in favour of frontend-side timeout |
| phi3:mini (not phi3.5:mini) | `phi3.5:mini` does not exist in the Ollama registry — causes `pull model manifest: file does not exist` |
| ollama-init retry loop | `ollama list` healthcheck passes before the server is fully ready to proxy registry requests — retry loop handles the race |
| OMP_NUM_THREADS=2 on backend | fastembed/ONNX Runtime defaults to using all CPU cores during embedding, saturating the host |
| RAG → fine-tune hybrid plan | RAG alone causes context overflow on phi3:mini's 4096-token window; fine-tuning bakes textbook knowledge into weights, leaving the context window for conversation and outcomes |

---

## Textbook data

`book_data/` is gitignored. Place PDFs there before running — the backend ingests on startup (idempotent).
- *Gray Hat Hacking: The Ethical Hacker's Handbook* (2022) — 662 chunks at 200 words
- *Reversing: Secrets of Reverse Engineering* (2005) — 596 chunks at 200 words
