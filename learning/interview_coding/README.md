# Interview Coding Practice Kit

Practice problems based on what AI Engineer / Anthropic-style screens often ask:

> Build something that works and reason about failure modes — **not** LeetCode Hard.

## How to practice (like a 60-min phone screen)

For each exercise:

1. Open `PROMPT.md` only (not `solution.py`)
2. Start a timer (**45–60 min**)
3. Code in `starter.py` (fill the TODOs)
4. **Narrate out loud** the whole time (or record yourself)
5. End with: “failure modes I’d mention in the interview”
6. Only then read `solution.py` and compare

Run a solution check:

```bash
cd learning/interview_coding
python -m pytest tests/ -q
# or run one file:
python 01_retrieval_scorer/solution.py
```

No OpenAI key needed — these are pure Python.

## Exercise map

| # | Folder | What they often ask | Maps to |
|---|--------|---------------------|---------|
| 01 | `01_retrieval_scorer/` | Score query vs chunk relevance | Anthropic “retrieval scorer” |
| 02 | `02_simple_retriever/` | Build a mini RAG retriever | Common live coding |
| 03 | `03_hallucination_guard/` | Refuse / fix unsafe answers | “Fix a hallucination” |
| 04 | `04_tool_orchestrator/` | LLM requests tools → you run them | Anthropic + FinGuard tools |
| 05 | `05_token_budget_allocator/` | Fit chunks into a token budget | Anthropic “token-budget allocator” |
| 06 | `06_mini_eval/` | Tiny eval harness | “How do you evaluate?” |

## Interview narration cheat phrases

While coding, say things like:

- “I’ll start with a working baseline, then call out edge cases.”
- “Empty input should return empty / refuse — not invent answers.”
- “For a million vectors I’d use ANN/HNSW; for this toy corpus keyword/score is fine.”
- “This reduces hallucinations; it doesn’t eliminate them.”

## Link to FinGuard

These skills show up in FinGuard as:

- Retriever / scorer → `vector_store.py` + learning Step 5  
- Tool orchestrator → `tools.py` + Step 6  
- Guardrails → Phase 1 safety  
- Eval → Phase 1 eval harness  
- Token budget → why we use top-k, not the whole PDF  

Also see: [`docs/INTERVIEW_PREP.md`](../../docs/INTERVIEW_PREP.md)
