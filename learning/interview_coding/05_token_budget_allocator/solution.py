"""05 — Token budget allocator (SOLUTION)

Greedy pack in order; skip chunks that don't fit and keep going.
"""

from __future__ import annotations


def count_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return len(text.split())


def allocate_chunks(
    chunks: list[str],
    max_tokens: int,
    reserved_tokens: int = 0,
) -> list[str]:
    budget = max(0, max_tokens - reserved_tokens)
    if budget == 0 or not chunks:
        return []

    selected: list[str] = []
    used = 0
    for chunk in chunks:
        cost = count_tokens(chunk)
        if cost == 0:
            continue
        if used + cost <= budget:
            selected.append(chunk)
            used += cost
        # else: skip this chunk and try later ones
    return selected


if __name__ == "__main__":
    chunks = [
        "one two three",  # 3
        "a b c d e f g h i j",  # 10 — may skip if budget tight
        "hello world",  # 2
    ]
    # budget 10 after reserve 2 from 12
    print(allocate_chunks(chunks, max_tokens=12, reserved_tokens=2))
    # expected: ["one two three", "hello world"]  (3+2=5 <= 10; middle 10 doesn't fit after 3)
