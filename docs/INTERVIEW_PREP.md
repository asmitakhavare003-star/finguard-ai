# FinGuard AI — Interview Prep Guide

**Who this is for:** Asmita (QA → AI Engineer), using FinGuard as the flagship project.

**How to use:**  
1. Finish learning Steps 1–8 + own the real `app/` (Phase 0).  
2. Memorize the **cheat sheet** answers (trade-offs + honest limits).  
3. Tick the **checklist** from eval → deploy before applying broadly.  
4. Practice out loud — narrate decisions; never overclaim infra you haven’t run.  
5. Ship something real + optional public write-up; prefer referrals over cold spray.

Related docs:

- Career phases: [`CAREER_ROADMAP.md`](CAREER_ROADMAP.md)
- Learning ladder: [`../learning/README.md`](../learning/README.md)
- **Interview coding drills:** [`../learning/interview_coding/README.md`](../learning/interview_coding/README.md)
- Project overview: [`../README.md`](../README.md)

---

## 1. One-liner (open every project discussion with this)

> FinGuard is an **agentic RAG API** for financial filings: retrieve relevant chunks → LLM reasons with **deterministic tools** → emit a **strict Pydantic risk summary**, streamed over **SSE**. I chose this over a simple PDF chatbot so the system is auditable, structured, and production-shaped.

**Don’t say:** “I built a PDF chat app.”  
**Do say:** trade-offs, eval, failure modes, cost/latency.

---

## 2. What interviewers actually ask (and what they don’t)

### Typical “AI Engineer” loop (what people report)

| Round type | What shows up | Prep for FinGuard |
|------------|---------------|-------------------|
| Light coding | Clean Python, debug — not always hard LeetCode | Write small functions; narrate |
| Small build | RAG, tool calling, eval harness, or agent workflow | You already have agent + tools; add evals |
| System design | Latency, cost, caching, observability, safety, fallbacks | Sections 5–8 + caching pitfalls below |
| Practical knowledge | Prompting, embeddings, retrieval, evals, failure modes | Learning Steps 1–8 + Phase 0 |

### They usually want

| Theme | Example question |
|-------|------------------|
| Decisions | Why RAG instead of fine-tuning? |
| Evaluation | How did you measure hallucinations? |
| Architecture | Why LangGraph / why tools / why structured output? |
| Cost & latency | How would you cut token spend / response time? |
| Caching (carefully) | Would you cache LLM answers in Redis? |
| Failure modes | What if retrieval returns nothing? Conflicting context? |
| Honesty | Can you *guarantee* no hallucinations? |
| Live coding | Build a simple retriever / fix a hallucination — **narrate** |

### They usually don’t need (for *your* target roles first)

- Deep Transformer math proofs / “define attention” with no use case  
- Heavy LeetCode as the main signal  
- Claiming GPU cluster / tensor-parallel expertise you don’t have  

**Senior infra topics** (vLLM, HPA vs MFU, tensor/pipeline parallelism) sometimes appear at bigger/infra teams. Know the **vocabulary and trade-offs** (section 7b) so you don’t sound naive — but **do not pretend FinGuard runs a GPU farm**. FinGuard is an **application-layer** agent (API + RAG + tools). That’s a valid AI Engineer story.

Study random term quizzes lightly; prioritize **use cases and decisions**.

---

## 2b. Be honest about your level (credibility)

| Claim | OK for FinGuard interviews? |
|-------|------------------------------|
| “I shipped an agentic RAG API with tools, schemas, SSE, Docker” | Yes |
| “I measure quality with evals / guardrails” | Yes after Phase 1 |
| “I deployed to one cloud” | Yes after Phase 2 |
| “I optimized HPA vs MFU on K8s GPU nodes” | **No** — say “I haven’t run that in prod; here’s how I’d think about it…” |
| “Redis semantic cache of all prompts in finance” | **Dangerous** — see caching section |

Interviewers trust engineers who **know their boundary** and still reason about the next layer.

---

## 3. What you already learned (map learning → real app)

| Learning step | Idea | Real FinGuard file |
|---------------|------|--------------------|
| 1 Plain Python | retrieve → reason/tools → format | Design of the whole agent |
| 2 Pydantic | Validated input/output contracts | `app/schemas/financial.py` |
| 3 FastAPI | HTTP JSON API | `app/main.py` (simple shape) |
| 4 OpenAI | LLM reason + structured format | `app/agent/graph.py` |
| 5 File retrieve | Lite RAG idea | `app/services/vector_store.py` (full = Qdrant) |
| 6 Tools | LLM asks, Python calculates | `app/services/tools.py` |
| 7 LangGraph | Shared state + 3 nodes | `app/agent/state.py` + `graph.py` |
| 8 SSE | Stream progress live | `app/main.py` `astream_events` |

**Bridge still required:** real **embeddings + Qdrant** (not only keyword `.txt` search).

---

## 4. Architecture cheat sheet (60-second whiteboard)

```text
PDF / report
  → chunk + embed (OpenAI)
  → Qdrant (financial_reports)

Client POST /api/v1/analyze
  → FastAPI validates FinancialQueryInput
  → LangGraph AgentState
       1. retrieve_node      (top-k chunks)
       2. reason_and_tool_node (LLM + margin/debt tools)
       3. format_output_node (FinancialSummaryOutput)
  → SSE: status → nodes → tools → final_output → done
```

**Shared state fields:** `query`, `company_name`, `retrieved_docs`, `messages`, `final_output`.

---

## 5. Trade-off cheat sheet (memorize these)

Practice: **what I built → why not the other way → cost/accuracy note**.

### Why RAG instead of fine-tuning?

| RAG (what we did) | Fine-tuning |
|-------------------|-------------|
| Docs change → re-ingest | Retrain / expensive |
| Citations / sources possible | Knowledge baked into weights |
| Cheaper for small/changing corpus | Better for style/behavior at scale |

**Say:** “For SEC-style filings that update and must be grounded, RAG is cheaper and safer than fine-tuning. Fine-tuning doesn’t give me easy citations or instant doc updates.”

### Why not stuff the whole PDF into the prompt?

- Context limits and cost explode  
- Noisy irrelevant pages confuse the model  
- Retrieval keeps only top-k relevant chunks  

### Why LangGraph (not one single prompt)?

- Separate concerns: retrieve / reason+tools / format  
- Shared state is inspectable  
- Easier to stream node progress and debug  
- Tools loop cleanly in the reason step  

**Say:** “One mega-prompt is harder to test and observe. Nodes let me validate retrieval, tools, and schema separately.”

### Why tools for margin / debt (not let the LLM invent math)?

- Exact arithmetic belongs in Python  
- LLM decides *when*; code does *what*  
- Finance interviews love this (reduces numeric hallucination)

### Why structured output / Pydantic / RiskLevel enum?

- API contract for clients and tests  
- Rejects `"kinda high"` — only LOW/MEDIUM/HIGH/CRITICAL  
- Second LLM call formats free analysis into a schema  

### Why SSE instead of one JSON response?

- Long agent runs need progress for UX and debugging  
- Client sees retrieve → tools → final without hanging  
- Trade-off: more complex client than a single POST JSON  

### Why Qdrant + embeddings (vs keyword search)?

| Keyword (learning Step 5) | Vectors (full app) |
|---------------------------|--------------------|
| Fast to learn | Matches meaning (“liquidity” ≈ “cash position”) |
| Misses synonyms | Needs embed API + vector DB |

**Say:** “Keyword search taught the RAG *shape*. Production uses embeddings so retrieval is semantic.”

### Why `gpt-4o-mini`?

- Lower cost/latency for portfolio + demos  
- Trade-off: weaker than larger models on hard reasoning  
- Structure + tools compensate for some weakness  

### Why SecretStr / settings?

- Avoid leaking API keys in logs/prints  
- Fail fast if OpenAI key missing  

### Index / scale vocabulary (say even if you use Qdrant)

- Small demo corpus → simple similarity is fine  
- Millions of vectors → need ANN (e.g. HNSW-style indexes) for speed  
- You don’t need to implement FAISS in FinGuard; you need the **trade-off sentence**

---

## 6. Evaluation & hallucination cheat sheet

**If asked “how did you evaluate?”** — do not say “it looked good in the UI.”

### Honest answer: can you make the LLM never hallucinate?

**Short answer interviewers respect:**

> You can’t fully guarantee no hallucinations. `temperature=0` and JSON/schema help **shape and consistency**, but they don’t fix **bad or conflicting context**. If retrieved chunks disagree, or an agent’s memory/docs drift from reality, the model can still invent or blend facts. Stronger models fail less often — not never.

**What you *can* do (FinGuard story):**

| Layer | How it reduces (not eliminates) risk |
|-------|--------------------------------------|
| Retrieval grounding | Answer from docs; cite sources |
| Tools | Exact math outside the LLM |
| Structured output | Valid schema / enums |
| Guardrails | Refuse when no docs / low confidence |
| Evals | Measure failure rate on a golden set |
| Observability | Trace bad runs; fix systematically |

**Agent / “Agents.md” style trap (good senior-sounding example):**

> If an agent edits code but a markdown “instructions” file still describes the old world, context is **conflicting**. The model may follow the stale file, the new code, or mix both. Evals and refresh of agent memory/docs matter as much as temperature.

**Don’t say:** “JSON mode means it can’t hallucinate.”  
**Do say:** “We reduce risk with grounding, tools, schema, refusal, and evals — and we design for failure when context conflicts.”

### Target eval story (after Phase 1)

1. **Golden set:** 15–30 Q&A pairs from the sample 10-K  
2. **Metrics:**  
   - Retrieval: did the right chunks appear?  
   - Schema: valid `FinancialSummaryOutput`?  
   - Sources: no invented file names?  
   - Tools: margin/debt match Python when numbers exist?  
3. **One failure:** e.g. Tesla query still answered with Apple docs → fixed by refusal when company not in corpus / empty retrieve  

**Until Phase 1 is done, honest answer:**

> “Today I have schema validation and mocked tests. My next milestone is a golden eval harness measuring retrieval, schema validity, source faithfulness, and tool correctness — that’s how I’ll quantify hallucinations, not eliminate them.”

### Hallucination mitigations interviewers like

- Refuse or low-confidence when **no docs** retrieved  
- Don’t invent metrics if tools weren’t called  
- Always return **sources** from retrieval metadata  
- Tools for numeric claims  
- Eval harness + failure writeups (your QA strength)  

---

## 7. Cost, latency & caching (say this carefully)

### Cost & latency levers (FinGuard)

| Lever | FinGuard angle |
|-------|----------------|
| Smaller model | `gpt-4o-mini` |
| Fewer tokens | top-k chunks, not whole PDF |
| Fewer LLM calls | Currently 2 (reason + format) — quality vs cost trade-off |
| App-level cache | Exact same query → cache **only if** safe (see below) |
| Streaming | SSE improves *perceived* latency, not FLOPs |

**Say:** “I optimize cost by retrieving less context and using a small model — without skipping grounding.”

### Caching: Redis “similar prompt → same answer” is often wrong for finance

Many tutorials cache by **embedding similarity of the user query** in Redis and return a prior response.

| Idea | Problem in enterprise / FinGuard-like apps |
|------|--------------------------------------------|
| Vector-similar queries share one answer | Near-duplicate queries can still need different answers; **privacy** if prompts/answers contain sensitive data |
| “Same response for similar questions” | Unsafe for personalized / regulated finance; vector match ≠ semantic equivalence you can trust |
| Good fit | Mostly **stateless public FAQs**, not private financial analysis |

**Safer app-level caching (if you add Redis in Phase 1):**

- Prefer **exact** request hash (same company + query + fiscal year + maybe doc version)  
- Short TTL  
- Never cache across users if prompts can contain private data  
- Or use Redis for **rate limiting**, not answer reuse  

**Inference-level caching (know the vocabulary — you don’t run this in FinGuard):**

- Production LLM serving often uses **KV / prefix caching** near the GPU (exact shared prefixes), not “embed the prompt and Redis-similarity the whole answer to every similar user”  
- That is different from application Redis semantic cache  

**Interview line:**

> “For FinGuard I’d cache only exact identical public-safe requests or rate-limit with Redis. I wouldn’t return another user’s answer because two queries were ‘close’ in embedding space — especially in finance. Prefix/KV caching at the inference layer is a different, more appropriate optimization when you run your own models.”

### 7b. LLM serving vs normal microservices (stretch vocabulary)

Scaling a **stateless CRUD API** ≠ scaling **LLM inference**.

| Classic backend | LLM serving (high level) |
|-----------------|---------------------------|
| HPA on CPU/RPS | GPUs, VRAM, batching, model parallelism |
| Spin more pods under load | Wasted spend if pods are idle GPU / poor **MFU** (model FLOPs utilization) |
| Easy horizontal scale | Tensor / pipeline parallelism, memory-aware scheduling matter |

**Your honest FinGuard position:**

> “FinGuard calls a hosted LLM API today, so my scaling story is API rate limits, caching, timeouts, and app replicas — not vLLM on K8s. If we self-hosted, I’d care about GPU utilization and serving stack, not only HPA replica count.”

Don’t fake GPU ops experience. Do show you know **naive HPA ≠ smart LLM scale**.

---

## 8. Failure modes (practice these)

| Failure | What you’d do |
|---------|----------------|
| Retrieval empty | Refuse / low confidence; don’t invent metrics |
| Conflicting chunks / stale agent docs | Detect conflict; prefer refuse or ask clarify; refresh memory |
| Revenue = 0 in margin tool | Tool returns error; LLM shouldn’t divide blindly |
| OpenAI timeout | Retry/backoff; SSE `error` event; health still up |
| Qdrant down | Clear 5xx / error event; don’t silently answer from memory |
| Bad / scanned PDF | Ingest fails; validate text chunks exist |
| SSE client disconnect | Server stops generating; no crash |
| Wrong company in query | Docs are Apple-only → must not claim Tesla facts |
| Semantic cache hit on private data | Don’t use vector Redis answer-sharing across users |

---

## 9. Live coding: how to narrate

While building a tiny retriever or fixing hallucination:

1. “I’ll split text into chunks so we can retrieve subsets.”  
2. “I’ll score or embed and take top-k.”  
3. “I’ll return source + text so the LLM can cite.”  
4. “If nothing matches, I’ll return empty and refuse later.”  
5. Mention scale: “For millions of vectors I’d use ANN/HNSW-style indexing.”

Silence loses interviews. Imperfect code + clear architecture talk wins.

**Practice kit (timed):** [`learning/interview_coding/README.md`](../learning/interview_coding/README.md)
— retrieval scorer, retriever, hallucination guard, tool orchestrator, token budget, mini eval.

---

## 10. QA → AI Engineer framing

> I come from QA — I already think in failure modes and measurable quality. I’m moving into AI engineering by building production-shaped agents and applying the same rigor to **LLM evaluation, grounding, and reliability**.

| QA muscle | AI equivalent |
|-----------|----------------|
| Test cases | Golden eval sets |
| Severity | Hallucination risk in finance |
| Regression suites | CI eval smoke tests |
| Bug reports | Failure analysis writeups |

---

## 11. Files you must explain in ~60 seconds each

- [ ] `app/core/config.py` — settings, SecretStr  
- [ ] `app/core/observability.py` — LangSmith, latency  
- [ ] `app/schemas/financial.py` — input/output/RiskLevel  
- [ ] `app/services/vector_store.py` — ingest + retrieve  
- [ ] `app/services/tools.py` — margin / debt tools  
- [ ] `app/agent/state.py` — AgentState  
- [ ] `app/agent/graph.py` — three nodes + compile  
- [ ] `app/main.py` — SSE streaming  

---

## 12. Master checklist before applying

### A. Learning ladder (done when you can teach each step)

- [ ] Step 1 — plain pipeline  
- [ ] Step 2 — Pydantic contracts  
- [ ] Step 3 — FastAPI JSON  
- [ ] Step 4 — OpenAI reason + structured output  
- [ ] Step 5 — file retrieve idea  
- [ ] Step 6 — tool calling loop  
- [ ] Step 7 — LangGraph state + nodes  
- [ ] Step 8 — SSE `astream_events`  

### B. Bridge to real app

- [ ] Run Qdrant locally or via Compose  
- [ ] Ingest `data/sample_10k.pdf`  
- [ ] Hit real `POST /api/v1/analyze` and read SSE events  
- [ ] Explain embeddings vs keyword retrieve  

### C. Phase 0 — Own FinGuard cold

- [ ] Whiteboard architecture with no notes  
- [ ] 60-second file explanations (section 11)  
- [ ] Trade-off answers (section 5) out loud  
- [ ] Hallucination honesty (section 6) out loud — “can’t fully eliminate”  
- [ ] Caching pitfalls (section 7) out loud  
- [ ] Failure modes (section 8) out loud  
- [ ] 3-minute demo video  
- [ ] README polished (trade-offs + results, not only features)  
- [ ] 5 STAR stories (FinGuard + QA)  
- [ ] Optional: short public write-up (LinkedIn/GitHub) on one trade-off or eval result  

### D. Phase 1 — Eval → product quality

- [ ] Golden set 15–30 Q&As  
- [ ] Eval script (retrieval, schema, sources, tools)  
- [ ] README: numbers + **one failure fixed**  
- [ ] Guardrail: empty retrieve → refuse / low confidence  
- [ ] Don’t invent metrics without tools/context  
- [ ] Log tool calls + sources (simple audit)  
- [ ] `POST /api/v1/ingest` (or equivalent)  
- [ ] Redis: prefer **rate-limit** or **exact-hash** cache with TTL — **not** vector-similar answer sharing for finance  
- [ ] Document why semantic Redis answer-cache is unsafe for private prompts  
- [ ] Stronger tests (1–2 integration beyond pure mocks)  

### E. Phase 2 — Deploy story

- [ ] One cloud deploy (FastAPI + Qdrant) — **shipped**, not only local demo  
- [ ] Secrets manager (not committed prod `.env`)  
- [ ] Health checks + basic logging / observability  
- [ ] CI: pytest on PRs  
- [ ] 1-page runbook (deploy, rollback, checks)  
- [ ] Fallbacks story: timeout, empty retrieve, provider down  
- [ ] Optional: Kafka concepts for fintech JDs  
- [ ] Optional stretch vocab: HPA ≠ MFU / why LLM serving differs (section 7b) — without overclaiming  

### F. Interview system (ongoing)

- [ ] 20 AI/system-design questions out loud / week  
- [ ] 2 mock interviews / week once Phase 1 underway  
- [ ] Practice live “build a retriever” narrating  
- [ ] Practice “fix this hallucination” narrating  
- [ ] Practice: “Can you guarantee no hallucinations?” (honest answer)  
- [ ] Practice: “Would you Redis-cache similar prompts?” (finance-safe answer)  
- [ ] Timed drills in [`learning/interview_coding/`](../learning/interview_coding/) (scorer, retriever, guard, tools, token budget, eval)  

### G. Visibility & applications

- [ ] Phase 0 solid  
- [ ] Phase 1 eval + at least guardrails (ingest/Redis can be in progress)  
- [ ] Keep shipping Phase 2 while interviewing  
- [ ] Prefer **referrals** and startups that care about shipped work  
- [ ] Niche story ready: e.g. **evals + agent orchestration + finance safety**  
- [ ] Cold big-tech spray is last resort; reach out with portfolio proof  

**You do not need** perfect K8s GPU ops + Kafka + Go + React before first applications.  
**You do need** a deployed-or-deployable system, edge cases, and the ability to explain trade-offs.

---

## 13. Suggested study order (max ROI)

1. Finish Step 8 understanding + Qdrant bridge  
2. Memorize trade-off cheat sheet (section 5) + hallucination honesty (section 6)  
3. Build **eval harness** (highest interview ROI)  
4. Guardrails + ingest  
5. Redis **rate-limit or exact cache** (avoid unsafe semantic answer-cache)  
6. Cloud deploy + CI + runbook (proof you can ship)  
7. Mock interviews + one public write-up of a trade-off/eval result  

---

## 14. Portfolio & job-search reality (from recent engineer advice)

Projects matter **only if** they show you can ship something real:

| Weak signal | Strong signal |
|-------------|----------------|
| Notebook / tutorial clone | Deployed or Compose-run API with edge cases |
| “I called OpenAI” | Trade-offs, evals, logging, failure modes |
| Ten shallow demos | **1–2 deep** projects in a niche (evals, agents, cost) |

**What moves the needle:**

1. Referrals from people who saw your work  
2. Public proof: GitHub README with eval numbers, short posts on trade-offs  
3. Startups often care more about **what you can do** than pedigree  

**If starting focus for FinGuard niche:**  
**Agent orchestration + evals + finance safety** (tools, schemas, grounding, guardrails).

Cold-apply everywhere without a portfolio story rarely works. Apply with proof; ask for intros.

---

## 15. Quick self-test (pass before applying)

Answer without notes:

1. Why RAG not fine-tuning for FinGuard?  
2. Why tools for profit margin?  
3. Why two LLM calls (reason + format)?  
4. What is AgentState for?  
5. What SSE events does a client see?  
6. Can you guarantee no hallucinations? What do you do instead?  
7. What if retrieval returns nothing? What if context conflicts?  
8. Would you cache similar prompts in Redis for a finance app? Why / why not?  
9. How will you measure quality (evals)?  
10. How would you cut cost ~30% without killing grounding?  
11. What is your FinGuard boundary vs GPU/vLLM infra?  

If any answer is fuzzy — study that section again before spraying applications.

---

## 16. Bottom line

FinGuard is the **right kind of project** if you sell **decisions, evals, safety, and shipping** — not “I followed a tutorial.”

Interviews reward:

- **why / why not**  
- **honest limits** (hallucinations, caching, infra boundary)  
- **measured quality**  
- **failure analysis** (your QA edge)  
- **something real that runs**

Your path:

```text
Learn (Steps 1–8) → Own (Phase 0) → Prove quality (Phase 1 eval)
  → Ship once (Phase 2) → Niche write-ups + referrals
  → Interview while narrating trade-offs
```

Tick the checklist. Practice the cheat sheet out loud. Lead with decisions. Never overclaim GPU ops you haven’t done — reason about them instead.
