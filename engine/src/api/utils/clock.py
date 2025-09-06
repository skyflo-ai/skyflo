from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Optional


def now_ms() -> int:
    """Wall-clock epoch time in whole milliseconds (UTC)."""
    return time.time_ns() // 1_000_000


def now_ns() -> int:
    """Wall-clock epoch time in nanoseconds (UTC)."""
    return time.time_ns()


def now_iso_ms() -> str:
    """ISO-8601 UTC with millisecond precision (e.g., 2025-08-30T06:59:12.123Z)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def monotonic_start_ns() -> int:
    """Monotonic reference point for measuring durations."""
    return time.monotonic_ns()


def since_ms(start_ns: int, end_ns: Optional[int] = None) -> float:
    """Elapsed milliseconds using a monotonic clock."""
    end = end_ns if end_ns is not None else time.monotonic_ns()
    return (end - start_ns) / 1_000_000.0
