"""
Step 1 — Mini FinGuard (plain Python only)

This is the SAME IDEA as the big project, with almost everything removed:

  Full FinGuard:  FastAPI → LangGraph → Qdrant → OpenAI → tools → Pydantic → SSE
  This mini:      question → fake docs → calculator → summary dict → print

If you understand this file, you understand ~60% of the *design*.
The rest of FinGuard is "production packaging" around this idea.
"""


# ---------------------------------------------------------------------------
# 1) Fake "documents" (in the real app these come from a PDF in Qdrant)
# ---------------------------------------------------------------------------

# {} is one dict, so total 2 dict
FAKE_DOCUMENTS = [
    {
        "source": "sample_10k.pdf",
        "text": "Apple Inc. reported revenue of 383000000000 and net income of 97000000000.",
        "revenue": 383_000_000_000,
        "net_income": 97_000_000_000,
        "debt_to_equity": 1.5,
    },
    {
        "source": "sample_10k.pdf",
        "text": "Liquidity remained strong. Cash and equivalents were substantial.",
        "revenue": None,
        "net_income": None,
        "debt_to_equity": None,
    },
]


# ---------------------------------------------------------------------------
# 2) Retrieve — pretend we searched a database; just return the fake docs
#    Later in FinGuard: app/services/vector_store.py + retrieve_node
# ---------------------------------------------------------------------------

def fake_retrieve(query: str) -> list:
    """Return documents that might help answer the query.

    Beginner note:
    - Input: a string (the user question)
    - Output: a list of dicts (our fake documents)
    For now we ignore the query and always return FAKE_DOCUMENTS.
    """
    print(f"[retrieve] Searching for: {query}")
    return FAKE_DOCUMENTS


# ---------------------------------------------------------------------------
# 3) Tool — a normal calculator (NOT an AI)
#    Later in FinGuard: app/services/tools.py
# ---------------------------------------------------------------------------

def calculate_profit_margin(net_income: float, revenue: float) -> float:
    """Profit margin % = (net_income / revenue) * 100."""
    if revenue == 0:
        raise ValueError("Revenue cannot be zero")
    return round((net_income / revenue) * 100, 2)


def assess_debt_risk(debt_to_equity: float) -> str:
    """Simple rules — same idea as tools.py in the real project."""
    if debt_to_equity > 2.0:
        return "HIGH_DEBT_RISK"
    if debt_to_equity > 1.0:
        return "MODERATE_DEBT_RISK"
    return "LOW_DEBT_RISK"


# ---------------------------------------------------------------------------
# 4) Reason — look at docs, maybe call tools, decide risk
#    Later in FinGuard: reason_and_tool_node (but an LLM decides there)
# ---------------------------------------------------------------------------

def reason_over_docs(company_name: str, docs: list) -> dict:
    """Use documents + calculators to build intermediate findings.

    Beginner note: in the real app, an LLM reads the docs and CHOOSES
    whether to call tools. Here WE hard-code that logic so you can see it.
    """
    revenue = None
    net_income = None
    debt_to_equity = None

    for doc in docs:
        if doc.get("revenue") is not None:
            revenue = doc["revenue"]
        if doc.get("net_income") is not None:
            net_income = doc["net_income"]
        if doc.get("debt_to_equity") is not None:
            debt_to_equity = doc["debt_to_equity"]

    profit_margin = None
    if revenue is not None and net_income is not None:
        profit_margin = calculate_profit_margin(net_income, revenue)
        print(f"[tool] profit_margin = {profit_margin}%")

    debt_label = None
    if debt_to_equity is not None:
        debt_label = assess_debt_risk(debt_to_equity)
        print(f"[tool] debt risk = {debt_label}")

    # Very simple risk rule (in the real app the LLM + schema choose RiskLevel)
    if debt_label == "HIGH_DEBT_RISK":
        risk_level = "HIGH"
    elif debt_label == "MODERATE_DEBT_RISK":
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "company_name": company_name,
        "revenue": revenue,
        "net_income": net_income,
        "debt_to_equity": debt_to_equity,
        "profit_margin": profit_margin,
        "debt_label": debt_label,
        "risk_level": risk_level,
        # for each doc (each dict) in docs, take the value at key "source"
        "sources": list({doc["source"] for doc in docs}),
    }


# ---------------------------------------------------------------------------
# 5) Format — final structured answer (a dict)
#    Later in FinGuard: format_output_node + FinancialSummaryOutput (Pydantic)
# ---------------------------------------------------------------------------

def build_summary(findings: dict, query: str) -> dict:
    """Turn findings into the final response shape."""
    summary_text = (
        f"For query '{query}': "
        f"{findings['company_name']} has profit margin "
        f"{findings['profit_margin']}% and debt label "
        f"{findings['debt_label']}. Overall risk: {findings['risk_level']}."
    )

    return {
        "company_name": findings["company_name"],
        "metrics": {
            "revenue": findings["revenue"],
            "net_income": findings["net_income"],
            "debt_to_equity": findings["debt_to_equity"],
            "profit_margin": findings["profit_margin"],
        },
        "risk_level": findings["risk_level"],
        "summary":  summary_text,
        "sources": findings["sources"],
        "analyst": "Asmita"
    }


# ---------------------------------------------------------------------------
# 6) Pipeline — this is the "graph" with no LangGraph
#    Later in FinGuard: app/agent/graph.py (3 nodes connected)
# ---------------------------------------------------------------------------

def analyze(company_name: str, query: str) -> dict:
    """End-to-end mini pipeline."""
    docs = fake_retrieve(query)                 # node 1: retrieve
    findings = reason_over_docs(company_name, docs)  # node 2: reason + tools
    final_output = build_summary(findings, query)    # node 3: format
    return final_output


# ---------------------------------------------------------------------------
# 7) "User" runs the program (like calling the API later)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    COMPANY = "Apple Inc."
    USER_QUERY = "What is the this company's revenue?"

    print("=== Mini FinGuard (Step 1) ===\n")
    result = analyze(COMPANY, USER_QUERY)

    print("\n=== Final output (like API response) ===")
    # On a dict, .items() gives you pairs of (key, value).
    for key, value in result.items():
        print(f"  {key}: {value}")
