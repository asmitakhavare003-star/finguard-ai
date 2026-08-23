# Step 7 — Add LangGraph (3 nodes)

## Goal

Keep the **same** Step 6 pipeline, but wire it with **LangGraph**:

```text
START → retrieve_node → reason_and_tool_node → format_output_node → END
```

Maps to full FinGuard: `app/agent/state.py` + `app/agent/graph.py`.

Still **no Qdrant/embeddings** — file retrieve stays as the lite stand-in.

---

## What changed vs Step 6

| Step 6 | Step 7 |
|--------|--------|
| `analyze()` calls 3 functions | LangGraph runs 3 **nodes** |
| Data passed as function args | Shared **`AgentState`** clipboard |
| You order the calls yourself | **Edges** define the order |

**Unchanged:** tools, tool loop, FastAPI, Pydantic schemas, file retrieve idea.

---

## What you need to understand

### 1. AgentState = shared notebook

Fields:

| Field | Filled by |
|-------|-----------|
| `query`, `company_name` | API / initial state |
| `retrieved_docs` | `retrieve_node` |
| `messages` | `reason_and_tool_node` |
| `final_output` | `format_output_node` |

Each node **returns only what it changes**, e.g. `{"retrieved_docs": docs}`.

### 2. Node = one desk

```text
retrieve_node      → find chunks
reason_and_tool_node → LLM + tools
format_output_node → structured FinancialSummaryOutput
```

### 3. Graph wiring = connect the desks

```python
workflow = StateGraph(AgentState)
workflow.add_node(...)
workflow.add_edge(START, "retrieve_node")
...
financial_agent = workflow.compile()
financial_agent.invoke(initial_state)
```

---

## What code to study (priority)

| Priority | Study | Skip deep dive |
|----------|--------|----------------|
| **Must** | `AgentState`, graph wiring (`add_node` / `add_edge` / `compile` / `invoke`) | — |
| **Must** | How each node `return { ... }` updates state | — |
| Skim | `reason_and_tool_node` tool loop | You did this in Step 6 |
| Black box | file retrieve helpers | Step 5 |

---

## How to run

```bash
source .venv/bin/activate
cd learning/07_langgraph
uvicorn app:app --reload --port 8001
```

Open http://localhost:8001/docs — title should say **Step 7 — LangGraph**.

Example:

```json
{
  "company_name": "Apple Inc.",
  "query": "What is the profit margin and debt risk?",
  "fiscal_year": 2023
}
```

Terminal should show:

```text
[node] retrieve_node
[node] reason_and_tool_node
[tool] ...   (sometimes)
[node] format_output_node
```

---

## New concepts

| Idea | Meaning |
|------|---------|
| `TypedDict` | Typed dictionary shape for state |
| `StateGraph` | Build a graph of steps |
| Node | A function that updates state |
| Edge | “After A, go to B” |
| `compile()` | Freeze the graph into a runnable agent |
| `invoke(state)` | Run the whole graph once |
| `Annotated[..., add_messages]` | Messages append instead of overwrite |

---

## Step 6 vs Step 7 one-liner

```text
Step 6: you call retrieve → reason → format
Step 7: LangGraph calls retrieve_node → reason_and_tool_node → format_output_node
```

Same work. New wiring.

When this feels clear, say **“ready for step 8”** (SSE streaming + closer to production FinGuard).
