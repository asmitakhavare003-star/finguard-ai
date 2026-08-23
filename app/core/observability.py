"""Tracing and latency observability helpers for FinGuard AI.

``setup_tracing`` configures LangSmith via environment variables consumed by
LangChain/LangGraph. ``trace_latency`` times sync/async callables (e.g. graph
nodes) and logs elapsed milliseconds.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, cast

from app.core.config import settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def setup_tracing() -> bool:
    """Configure LangSmith / LangChain tracing from application settings.

    Reads ``LANGCHAIN_TRACING_V2``, ``LANGCHAIN_API_KEY``, and
    ``LANGCHAIN_PROJECT`` from ``settings`` and mirrors them into process
    environment variables when values are present (LangChain SDKs read these
    env vars at runtime).

    Returns:
        ``True`` if LangSmith tracing is enabled, otherwise ``False``.
    """
    tracing_flag = bool(settings.LANGCHAIN_TRACING_V2)
    api_key = (
        settings.LANGCHAIN_API_KEY.get_secret_value()
        if settings.LANGCHAIN_API_KEY
        else ""
    )
    api_key = api_key.strip() if api_key else ""
    project = (settings.LANGCHAIN_PROJECT or "").strip()

    # LangChain expects string env values ("true" / "false"), not Python bools.
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if tracing_flag else "false"

    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
    if project:
        os.environ["LANGCHAIN_PROJECT"] = project

    # Endpoint is optional but useful when present in settings.
    endpoint = (settings.LANGCHAIN_ENDPOINT or "").strip()
    if endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    enabled = tracing_flag and bool(api_key)
    if not enabled:
        # Avoid partial/noisy tracing attempts when the API key is missing.
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    status = "ENABLED" if enabled else "DISABLED"
    message = f"[OBSERVABILITY] LangSmith tracing is {status}"
    logger.info(message)
    print(message)
    return enabled


def trace_latency(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that logs wall-clock latency for sync or async functions.

    Example log line::

        [LATENCY] retrieve_node completed in 142.30 ms

    Wrap LangGraph node functions so each step's performance is visible in
    local logs during demos and debugging.
    """

    def _log_elapsed(started: float) -> None:
        elapsed_ms = (time.perf_counter() - started) * 1000
        line = f"[LATENCY] {func.__name__} completed in {elapsed_ms:.2f} ms"
        logger.info(line)
        print(line)

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            started = time.perf_counter()
            try:
                return await cast(Callable[P, Awaitable[Any]], func)(*args, **kwargs)
            finally:
                _log_elapsed(started)

        return cast(Callable[P, R], async_wrapper)

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            _log_elapsed(started)

    return cast(Callable[P, R], sync_wrapper)
