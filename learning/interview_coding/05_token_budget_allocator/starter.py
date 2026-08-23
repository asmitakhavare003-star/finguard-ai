"""05 — Token budget allocator (STARTER)"""

from __future__ import annotations


def count_tokens(text: str) -> int:
    """Toy tokenizer: whitespace word count."""
    # TODO
    raise NotImplementedError


def allocate_chunks(
    chunks: list[str],
    max_tokens: int,
    reserved_tokens: int = 0,
) -> list[str]:
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    chunks = [
        "one two three",          # 3
        "a b c d e f g h i j",  # 10
        "hello world",            # 2
    ]
    print(allocate_chunks(chunks, max_tokens=12, reserved_tokens=2))
