# FinGuard AI — Career Roadmap (QA → AI Engineer)

Use this document as your follow-along plan. It consolidates requirements from multiple AI Engineer / Agentic AI / RAG roles (including AmEx-style fintech, forward-deployed AI, regulated banking/GCP, and enterprise RAG JDs) and maps them against the FinGuard AI project.

**Goal:** Get into an AI Engineer role using FinGuard as your flagship portfolio project, while closing the gaps these jobs repeatedly ask for.

---

## Combined job requirements (all JDs merged)

Across the roles you shared, hiring teams repeatedly want:

| Theme | What they mean |
|-------|----------------|
| Agentic systems | Multi-step agents that reason, call tools, act |
| RAG | Retrieve from docs/knowledge, ground answers |
| LLM tooling | OpenAI / Anthropic / Azure OpenAI, structured outputs, function calling |
| Orchestration | LangGraph / LangChain (or similar) |
| Python + APIs | Production services, not notebooks |
| Evaluation | Benchmarks, ground truth, failure analysis |
| Observability | Tracing, monitoring, debugging live systems |
| Beyond chatbot | Workflows with schemas, tools, retrieval, APIs |
| Cloud / deploy | Docker → cloud / Kubernetes (AWS / GCP / Azure varies by employer) |
| Regulated / finance mindset | Safety, audit, privacy, explainability |
| Soft skills | Stakeholders, ambiguity, ownership, AI-assisted coding with quality |

**Nice-to-haves (not blockers for every role):** Kafka, gRPC, Go, TypeScript/React UI, OCR, research experience, founder experience.

---

## What FinGuard already covers

### Strong coverage (lead with this in interviews)

- Agentic workflow (LangGraph: retrieve → reason/tools → structured output)
- RAG (PDF → chunk → embed → Qdrant → retrieve)
- Tool calling (profit margin + debt risk)
- Structured outputs / Pydantic schemas + `RiskLevel`
- FastAPI production-style endpoint (`POST /api/v1/analyze` SSE streaming)
- Observability starter (LangSmith + `@trace_latency`)
- Automated tests (Pytest)
- Docker multi-container packaging (`web` + Qdrant + Redis)
- Financial domain framing (10-K style documents)

### Partial / thin

- Redis present in Compose but **not used in app code**
- Tests mostly mocked (good for CI; weak as formal “evaluation”)
- Safety is light (sources field; no hard guardrails)
- Deployment is local Compose, not cloud / Kubernetes
- Single LLM vendor (OpenAI), not Anthropic / Azure OpenAI

### Not covered yet

- Formal evaluation harness / golden dataset
- Kafka / event-driven architecture
- Kubernetes / AWS–GCP–Azure production deploy
- gRPC, Go, TypeScript/React UI
- OCR / image document extraction
- Auth, audit logging, access control, model governance
- Customer-facing FDE artifacts (runbooks, eval reports for stakeholders)

---

## Honest readiness check

| Question | Answer |
|----------|--------|
| Is FinGuard enough alone? | **Enough to start conversations**, not enough to claim full JD match |
| Biggest gap across all roles? | **Evaluation + production failure analysis** |
| Second biggest gap? | **Cloud deploy + ops story** |
| Third biggest gap? | **Safety / audit for finance** |
| Can a QA engineer break in? | **Yes**, if you productize FinGuard, add eval, and interview like an engineer who owns AI system quality |

**Realistic near-term targets**

- AI Engineer / GenAI Engineer / LLM Application Engineer
- Junior–mid backend AI roles
- AI QA → AI Eng hybrid roles

**Stretch targets** (after eval + safety + cloud story)

- AmEx / enterprise fintech agentic roles
- Forward-deployed AI / solutions-style roles

---

## How to use your QA background

Interview framing to practice out loud:

> I come from QA — I already think in failure modes, regressions, and measurable quality. I’m moving into AI engineering by building production-shaped agent systems and applying the same rigor to **LLM evaluation, grounding, and reliability**.

| QA muscle | AI engineering equivalent |
|-----------|---------------------------|
| Test cases | Golden eval sets |
| Severity / priority | Risk of hallucination in finance |
| Regression suites | CI eval smoke tests |
| Bug reports | Model failure analysis writeups |
| Stakeholder updates | Explaining AI limits to non-technical partners |

---

## Roadmap phases

### Phase 0 — Own FinGuard cold (1–2 weeks)

Do this **before** applying broadly.

**Actions**

- [ ] Explain every important file in ~60 seconds:
  - `app/core/config.py`
  - `app/core/observability.py`
  - `app/schemas/financial.py`
  - `app/services/vector_store.py`
  - `app/services/tools.py`
  - `app/agent/state.py`
  - `app/agent/graph.py`
  - `app/main.py`
- [ ] Whiteboard the full architecture without looking at code
- [ ] Prepare crisp answers for:
  - Why LangGraph (not a single prompt)?
  - Why Qdrant?
  - Why SSE instead of one JSON response?
  - Why `SecretStr`?
  - What if retrieval returns nothing?
  - What if revenue is 0 in the margin tool?
- [ ] Record a 3-minute demo video
- [ ] Polish GitHub README walkthrough
- [ ] Write 5 STAR stories (FinGuard + prior QA work)

**Exit criteria:** You can teach FinGuard to another engineer without notes.

---

### Phase 1 — High-ROI project upgrades (2–4 weeks)

Add only what hiring managers keep asking for.

#### 1) Evaluation harness (highest ROI across all JDs)

- [ ] Create 15–30 golden Q&A pairs from `data/sample_10k.pdf`
- [ ] Define metrics:
  - retrieval hit / relevance
  - schema validity (`FinancialSummaryOutput`)
  - no fabricated sources
  - tool correctness (margin / debt risk)
- [ ] Add script e.g. `scripts/eval_rag.py`
- [ ] Publish a short eval section in README (numbers + 1 failure you fixed)

#### 2) Safety / guardrails

- [ ] If no docs retrieved → refuse or return low-confidence response
- [ ] Do not invent metrics when tools were not called
- [ ] Log tool calls + sources (simple audit trail)

#### 3) Ingest API

- [ ] Add `POST /api/v1/ingest` so RAG is a product capability, not a one-liner script

#### 4) Use Redis for something real

- [ ] Rate-limit `/api/v1/analyze` **or** cache identical queries
- [ ] Update README so Redis is an honest part of the architecture (still not Kafka, but stronger)

#### 5) Optional but strong: second model provider

- [ ] Add Anthropic **or** Azure OpenAI behind a thin client switch

**Exit criteria:** You can show eval numbers + a concrete failure you found and fixed.

---

### Phase 2 — Production / cloud credibility (3–6 weeks)

You do not need enterprise Kubernetes mastery. You need **one credible deploy path**.

**Actions**

- [ ] Pick **one** cloud and deploy FastAPI + Qdrant:
  - GCP Cloud Run / GKE, **or**
  - AWS ECS / EKS, **or**
  - Azure Container Apps
- [ ] Use secrets manager (not committed `.env` in prod)
- [ ] Add basic logging + health checks
- [ ] Add CI: run `pytest` on pull requests
- [ ] Write a 1-page production runbook (deploy, rollback, on-call checks)
- [ ] Learn Kafka concepts enough to discuss (optional tiny local producer/consumer demo helps AmEx-style JDs)

**Exit criteria:** “I deployed FinGuard to X; here’s how I’d monitor and roll back.”

---

### Phase 3 — Interview system (ongoing)

Study by theme, not random tutorials.

| Topic | Depth needed | Status |
|-------|----------------|--------|
| Prompt engineering | Practical patterns + failure cases | [ ] |
| RAG deep dive | Chunking, hybrid search, rerank, citations | [ ] |
| Agents | Tool calling, loops, state, human-in-the-loop | [ ] |
| Evaluation | Faithfulness, context precision, tool accuracy | [ ] |
| Python backend | Async, APIs, errors, testing | [ ] |
| System design | “Design a financial RAG agent” on a whiteboard | [ ] |
| Responsible AI | PII, audit, access control, hallucination risk | [ ] |

**Practice**

- [ ] 20 AI / system-design questions out loud each week
- [ ] 2 mock interviews per week once Phase 1 is underway

---

### Phase 4 — Role targeting (when applying)

Do not spray the same story everywhere.

| Role type | Lead with | How to handle gaps |
|-----------|-----------|--------------------|
| AmEx / fintech agentic | Agent + RAG + tools + finance safety | K8s/Kafka = design next-step answer |
| Enterprise RAG / banking | Docs, compliance language, eval, audit | Add OCR only if targeting doc-heavy roles |
| Forward-deployed AI (Callosum-style) | Eval report + customer narrative + integration | Platform accelerators = learning plan |
| Full-stack AI | Tiny React SSE UI if that JD requires FE | Skip UI if role is backend-heavy |

---

## 8-week execution plan

| Week | Focus | Done |
|------|--------|------|
| 1–2 | Master FinGuard + demo video + GitHub polish | [ ] |
| 3–4 | Eval harness + guardrails + ingest API | [ ] |
| 5 | Redis usage + stronger tests (1–2 real integration tests) | [ ] |
| 6–7 | Deploy to one cloud + CI | [ ] |
| 8 | Mock interviews + apply to 10–15 well-matched roles | [ ] |

Start applying once **Phase 0–1 are solid**. Keep shipping Phase 2 while interviewing.

---

## What you do **not** need before applying

- PhD / research papers
- Perfect Kafka + Kubernetes + Go + React all at once
- Waiting until the project looks “fully enterprise”

---

## Must-prepare talking points (even before coding more)

Practice these even if not fully implemented yet:

1. **Correctness & safety in finance** — hallucinations, citation grounding, refusal on missing data, PII, audit trails
2. **Evaluation** — how you measure retrieval quality, tool accuracy, structured-output validity
3. **Production failure modes** — Qdrant down, OpenAI timeout, bad PDF, wrong tool args, SSE disconnect
4. **Why LangGraph** vs plain chain / single ReAct agent
5. **Tradeoffs** — chunk size, top-k, embedding model, structured output vs free text

---

## Suggested next implementation order (in this repo)

When you are ready to code again, do this order for maximum interview ROI:

1. Evaluation harness (`scripts/eval_rag.py` + golden set)
2. Ingest API + guardrails
3. Redis rate limit or query cache
4. CI + one cloud deploy
5. Optional: React SSE mini-UI / second LLM provider / Kafka demo

---

## Reference materials in this repo

- Project overview: [`README.md`](../README.md)
- Interview prep + cheat sheet + checklist: [`INTERVIEW_PREP.md`](INTERVIEW_PREP.md)
- Manual build steps: [`MANUAL_SETUP_STEPS.md`](MANUAL_SETUP_STEPS.md)
- Learning ladder: [`../learning/README.md`](../learning/README.md)
- Core agent: `app/agent/graph.py`
- RAG: `app/services/vector_store.py`
- API: `app/main.py`
- Tests: `tests/`

---

## Bottom line

FinGuard is the **right kind of project** for these roles. It proves agentic AI + RAG + tools + schemas + FastAPI.

To clear interviews and qualify more broadly:

1. Master the project line-by-line  
2. Add **evaluation + safety**  
3. Build one **production/cloud** story  
4. Sell your QA background as **AI quality / failure analysis expertise**

You can get into AI engineering from QA — treat this file as the checklist and tick boxes weekly.
