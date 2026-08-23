"""04 — Tool orchestrator (SOLUTION)

Same idea as FinGuard reason_and_tool_node / Step 6 tool loop.
"""

from __future__ import annotations

from typing import Any, Callable


def run_with_tools(
    user_message: str,
    llm_call: Callable[[list[dict]], dict],
    tools: dict[str, Callable[..., Any]],
    max_steps: int = 5,
) -> str:
    messages: list[dict] = [{"role": "user", "content": user_message}]

    for step in range(max_steps):
        response = llm_call(messages)
        rtype = response.get("type")

        if rtype == "final":
            return str(response.get("content", ""))

        if rtype == "tool_call":
            name = response.get("name")
            args = response.get("args") or {}
            if name not in tools:
                return f"error: unknown tool '{name}'"
            try:
                result = tools[name](**args)
            except TypeError as exc:
                return f"error: bad tool args for '{name}': {exc}"
            except Exception as exc:  # noqa: BLE001
                return f"error: tool '{name}' failed: {exc}"

            messages.append({"role": "assistant", "content": str(response)})
            messages.append({"role": "tool", "name": name, "content": str(result)})
            continue

        return f"error: unexpected llm response type '{rtype}'"

    return "error: max_steps exceeded (possible tool loop)"


def calculate_margin(net_income: float, revenue: float) -> dict:
    if revenue == 0:
        return {"error": "division by zero", "profit_margin_pct": None}
    return {"profit_margin_pct": round((net_income / revenue) * 100, 2)}


def demo_llm(messages: list[dict]) -> dict:
    has_tool_result = any(m.get("role") == "tool" for m in messages)
    if not has_tool_result:
        return {
            "type": "tool_call",
            "name": "calculate_margin",
            "args": {"net_income": 97.0, "revenue": 383.0},
        }
    tool_msg = [m for m in messages if m.get("role") == "tool"][-1]
    return {
        "type": "final",
        "content": f"Profit margin result: {tool_msg['content']}",
    }


if __name__ == "__main__":
    print(
        run_with_tools(
            "What is the margin?",
            demo_llm,
            {"calculate_margin": calculate_margin},
        )
    )
