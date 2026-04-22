# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SecurityAI is a lightweight AI assistant for developing secure networks/applications and pen-testing tools. It is grounded in curated security textbooks (`book_data/`) and is designed to run on memory-constrained devices. The frontend is complete; the LLM backend is the next milestone.

## Commands

```bash
npm run dev      # start Vite dev server on http://localhost:5173
npm run build    # TypeScript check + production build → dist/
npm run lint     # ESLint
npm run preview  # serve the production build locally
```

## Stack

- **Frontend**: React 19 + TypeScript + Tailwind CSS v4 + Vite 6
- **Icons**: lucide-react
- **Markdown/code rendering**: react-markdown + react-syntax-highlighter (Prism, oneDark theme)
- **Backend** (planned): lightweight local LLM, trained/fine-tuned on `book_data/` PDFs

## Architecture

```
src/
  types/index.ts          # shared types: Message, Conversation, Category, Source
  hooks/useConversation.ts # all conversation state — CRUD + message appending
  components/
    Sidebar.tsx            # category filter + conversation history list
    ChatWindow.tsx         # message list + empty-state starters per category
    MessageBubble.tsx      # markdown renderer, code blocks with copy, source badges
    ChatInput.tsx          # auto-growing textarea, Enter to send, Shift+Enter newline
  App.tsx                  # composes Sidebar + ChatWindow; owns handleSend + loading state
```

### Data flow

1. User types in `ChatInput` → `onSend` bubbles up to `App.handleSend`
2. `App` appends the user message via `useConversation.appendMessage`, sets `isLoading`
3. The backend call (currently a placeholder) resolves → assistant message appended with optional `sources[]`
4. `ChatWindow` auto-scrolls to bottom via `useEffect` + `bottomRef`

### Categories

Five categories drive both the sidebar filter and `ChatWindow` empty-state starters:
`general` | `secure-dev` | `pen-testing` | `reverse-engineering` | `network-security`

### Backend integration point

In `App.tsx`, replace the `setTimeout` stub in `handleSend` with a `fetch` (or SDK call) to the local LLM API. The assistant reply should conform to `{ content: string; sources?: Source[] }`. The `Source` type references `book`, `chapter`, and optional `page`.

## Textbook data

`book_data/` contains the PDFs used as the AI's knowledge base (gitignored from commits):
- *Gray Hat Hacking: The Ethical Hacker's Handbook* (2022)
- *Reversing: Secrets of Reverse Engineering* (2005)

The backend pipeline will parse these PDFs, chunk the text, embed it, and store it for RAG retrieval.
