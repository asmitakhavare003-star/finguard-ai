# FinGuard Learning Path (beginner → full project)

Feeling overwhelmed by `app/` is normal. The full project is **not one hard idea** —
it is **many medium ideas stacked**. We learn by building a tiny version first,
then adding one layer at a time.

## Is the Python basic or advanced?

| Level | Examples in FinGuard | Your status |
|-------|----------------------|-------------|
| **Basic** | functions, `if/else`, dicts, lists, strings, `return` | You know this |
| **Comfortable beginner** | modules/files (`import`), classes (light use), type hints (`str`, `Optional`) | Easy to learn |
| **Intermediate** | decorators (`@tool`, `@trace_latency`), `TypedDict`, enums, async generators | New for many beginners |
| **Library knowledge** (not “hard Python”) | FastAPI, Pydantic, LangChain, LangGraph, Qdrant, Docker | New APIs to learn one by one |

So: **you are not “bad at coding.”** You are seeing intermediate Python + several libraries at once.

---

## The ladder (same product, growing complexity)

| Step | Folder | What you build | Maps to full project |
|------|--------|----------------|----------------------|
| 1 | `01_plain_python/` | One script: fake docs + calculator + summary dict | tools + “format output” idea |
| 2 | `02_pydantic/` | Same pipeline + Pydantic input/output models | `app/schemas/` |
| 3 | `03_fastapi/` | Same pipeline as an HTTP JSON API | `app/main.py` (simple) |
| 4 | `04_openai/` | Real OpenAI calls (reason + structured format, no tools) | part of `graph.py` |
| 5 | `05_file_retrieve/` | Retrieve top chunks from a real `.txt` file | `vector_store.py` lite |
| 6 | `06_tools/` | LLM tool calling (margin / debt calculators) | `tools.py` + reason node |
| 7 | `07_langgraph/` | Same pipeline as LangGraph 3 nodes + AgentState | `agent/graph.py` |
| 8 | `08_sse/` | Stream graph progress as SSE (live events) | `app/main.py` |

**Rule:** do not open the next step until you can explain the current step in your own words.

---

## How to use this

1. Finish steps 1 → 7 in order
2. Open `08_sse/README.md`, start uvicorn, try `curl -N` on `/analyze`
3. Compare Step 7 one JSON vs Step 8 event stream
4. Learning ladder complete → bridge to real Qdrant + Phase 0 in `docs/CAREER_ROADMAP.md`
5. Before applying: work through `docs/INTERVIEW_PREP.md` (cheat sheet + checklist)
6. Practice timed coding: `learning/interview_coding/` (Anthropic-style + common AI Eng drills)

The full `app/` folder is the **finished house**.  
`learning/` is the **LEGO bricks**.
