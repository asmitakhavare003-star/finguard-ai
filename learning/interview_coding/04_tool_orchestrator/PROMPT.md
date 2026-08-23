# 04 — Tool-use orchestrator

## Interview prompt (≈ Anthropic + FinGuard)

You have a fake “LLM” that sometimes requests tools. Implement an orchestrator:

```python
def run_with_tools(
    user_message: str,
    llm_call,          # callable(messages) -> dict
    tools: dict[str, callable],
    max_steps: int = 5,
) -> str:
```

`llm_call(messages)` returns either:

```python
{"type": "final", "content": "the answer"}
# or
{"type": "tool_call", "name": "calculate_margin", "args": {"net_income": 97, "revenue": 383}}
```

Your job:

1. Start with `[{"role": "user", "content": user_message}]`
2. Call `llm_call`
3. If tool_call → run the Python tool → append a tool result message → call LLM again
4. If final → return content
5. Stop with an error string if `max_steps` exceeded or unknown tool

### Talk about failure modes

- Infinite tool loops → `max_steps`
- Unknown / malicious tool names
- Bad args (missing keys, wrong types)
- Tool throws exceptions

### Time box

45–60 minutes.
