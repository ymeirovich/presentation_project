# src/common/backoff.py
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar
from googleapiclient.errors import HttpError

T = TypeVar("T")
log = logging.getLogger("backoff")


def retryable_http(e: Exception) -> bool:
    """
    Decide if an HTTP error is transient and worth retrying.
    Covers common Google API status codes.
    """
    if isinstance(e, HttpError):
        status = getattr(e, "status_code", None) or getattr(getattr(e, "resp", None), "status", None)
        return status in (429, 500, 502, 503, 504)
    return False


def backoff(fn: Callable[[], T], attempts: int = 4, base: float = 0.6) -> T:
    """
    Exponential backoff wrapper.
    Tries 'attempts' times, waits base * 2^i between retries.
    Raises last exception if all fail.
    """
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i >= attempts - 1 or not retryable_http(e):
                raise
            delay = base * (2 ** i)
            log.warning("Retry after %.2fs (%s)", delay, type(e).__name__)
            time.sleep(delay)
    # unreachable
    raise RuntimeError("backoff failed unexpectedly")
