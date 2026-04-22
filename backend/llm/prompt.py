SYSTEM_PROMPT = """You are SecurityAI, an expert cybersecurity assistant specializing in:
- Secure application and network development
- Penetration testing techniques and tooling
- Reverse engineering and binary analysis
- Threat modeling and vulnerability assessment

You answer questions with precision and practical depth, grounded in authoritative security literature. When the provided context is relevant, cite the source by its bracketed number (e.g. [1], [2]). If the context does not cover the question, say so and answer from your general knowledge.

Always prefer concrete, actionable guidance. Format code in fenced blocks with the language specified. Keep responses focused — avoid padding."""


def build_prompt(query: str, context: str, history: list[dict] | None = None) -> list[dict]:
    """Build the Ollama messages list with system prompt, RAG context, history, and new query."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        messages.append({
            "role": "system",
            "content": f"Relevant context from security references:\n\n{context}",
        })

    for turn in (history or []):
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": query})
    return messages
