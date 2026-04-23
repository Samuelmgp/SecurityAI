# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SecurityAI is a lightweight AI assistant for developing secure networks/applications and pen-testing tools. It is grounded in curated security textbooks (`book_data/`) and is designed to run on memory-constrained devices. Both frontend and backend are implemented; the system is ready for Ollama + model setup.

## Commands

### Docker (recommended — single command startup)
```bash
docker compose up --build      # builds images, pulls model (~2.3 GB first run), starts all services
# Frontend → http://localhost
# Backend  → http://localhost:8000
# Ollama   → http://localhost:11434

docker compose down            # stop all services (volumes preserved)
docker compose down -v         # stop and delete all volumes (wipes model + vector DB)

OLLAMA_MODEL=mistral:7b docker compose up   # override the default model
```

### Local development (without Docker)
```bash
# Terminal 1 — frontend
npm run dev      # Vite dev server → http://localhost:5173
npm run build    # TypeScript check + production build → dist/
npm run lint

# Terminal 2 — backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload     # → http://localhost:8000

# Terminal 3 — Ollama (install from https://ollama.com)
ollama serve
ollama pull phi3:mini       # ~2.3 GB, run once
```

## Stack

- **Frontend**: React 19 + TypeScript + Tailwind CSS v4 + Vite 6 + lucide-react
- **Backend**: FastAPI + uvicorn (Python 3.11+)
- **Inference**: Ollama (wraps llama.cpp) — default model `phi3:mini`
- **RAG**: ChromaDB (embedded, persistent) + `BAAI/bge-small-en-v1.5` sentence-transformers embeddings
- **PDF parsing**: PyMuPDF (fitz)
- **Orchestration**: Docker Compose — 4 services: `ollama`, `ollama-init`, `backend`, `frontend`

## Architecture

```
src/                              # React frontend
  types/index.ts                  # Message, Conversation, Category, Source
  hooks/useConversation.ts        # conversation CRUD + streaming message mutation
  components/
    Sidebar.tsx                   # category filter + history list
    ChatWindow.tsx                # message list + per-category empty-state
    MessageBubble.tsx             # markdown + syntax-highlighted code + source badges
    ChatInput.tsx                 # auto-resizing textarea
  App.tsx                         # SSE stream consumer; owns handleSend

backend/
  main.py                         # FastAPI app; runs ingest_all() on startup
  config.py                       # pydantic-settings (reads backend/.env)
  api/
    chat.py      POST /api/chat   # SSE streaming: RAG → prompt → Ollama token stream
    health.py    GET  /api/health # LLM availability + chunk counts
    outcomes.py  POST /api/outcomes, GET /api/outcomes
  rag/
    ingest.py                     # PDF → page text → chunks → embed → ChromaDB upsert (idempotent)
    chunker.py                    # word-count splitter with overlap
    retriever.py                  # queries textbooks + outcomes collections, returns ranked RetrievedChunk[]
  llm/
    engine.py                     # Ollama /api/chat wrapper with async token streaming
    prompt.py                     # system prompt + RAG context injection
  learning/
    store.py                      # outcomes ChromaDB collection — record_outcome / list_outcomes
  data/chroma/                    # gitignored — persistent vector DB
```

### Request lifecycle

1. Frontend `POST /api/chat` with `{ query, history[], category }`
2. `retriever.retrieve(query)` — cosine search across **textbooks** + **outcomes** collections
3. Top chunks formatted into context block and injected into system prompt
4. Messages list sent to Ollama streaming API; tokens yielded as SSE `data: {"token": "..."}` events
5. Final SSE event: `data: {"done": true, "sources": [...]}` — frontend attaches source badges
6. Frontend streams tokens into a pre-allocated assistant message slot via `updateLastAssistantMessage`

### Continual learning

`POST /api/outcomes` stores a scenario + result + lesson as an embedded document in the `outcomes` ChromaDB collection. The retriever queries this collection on every request (with half the weight of textbooks) so learned knowledge surfaces automatically.

### Adding a new LLM engine

The `llm/engine.py` module exposes two functions: `is_available()` and `stream_chat(messages)`. To swap backends (e.g. llama-cpp-python), implement the same interface and update the imports in `api/chat.py`.

## Docker service startup order

```
ollama (healthcheck: ollama list)
  └─► ollama-init (pulls model, exits 0)
        └─► backend (healthcheck: GET /api/health)
              └─► frontend (nginx, port 80)
```

`ollama-init` is `restart: "no"` — on subsequent `docker compose up` it is skipped because the model is already in the `ollama_models` volume.

nginx proxies `/api/*` → `backend:8000` with `proxy_buffering off` to support SSE streaming. The frontend is built with `VITE_API_URL=""` so all API calls use relative paths and go through nginx — no hardcoded hosts in the image.

## Textbook data

`book_data/` is gitignored. Place PDFs there before starting — the backend ingests them on startup (idempotent, skips already-stored chunks). In Docker, `book_data/` is bind-mounted read-only into the backend container.
- *Gray Hat Hacking: The Ethical Hacker's Handbook* (2022)
- *Reversing: Secrets of Reverse Engineering* (2005)
