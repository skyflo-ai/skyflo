"""SSE event emission helpers for the memory system."""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..utils.clock import now_ms
from .schemas import MemoryHit

EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


async def emit_memory_context_loaded(
    callback: Optional[EventCallback],
    run_id: str,
    hits: List[MemoryHit],
) -> None:
    if not callback or not hits:
        return
    await callback(
        {
            "type": "memory.context.loaded",
            "run_id": run_id,
            "documents": [
                {
                    "document_id": hit.document_id,
                    "store_slug": hit.store_slug,
                    "path": hit.path,
                    "trust_level": hit.trust_level.value,
                    "version_id": hit.version_id,
                    "used_as": "advisory_context",
                }
                for hit in hits
            ],
            "timestamp": now_ms(),
        }
    )


async def emit_memory_search(
    callback: Optional[EventCallback],
    run_id: str,
    query: str,
    results_count: int,
) -> None:
    if not callback:
        return
    await callback(
        {
            "type": "memory.search",
            "run_id": run_id,
            "query": query,
            "results_count": results_count,
            "timestamp": now_ms(),
        }
    )


async def emit_memory_write_created(
    callback: Optional[EventCallback],
    run_id: str,
    store_slug: str,
    path: str,
    document_id: str,
    document_type: str,
) -> None:
    if not callback:
        return
    await callback(
        {
            "type": "memory.write.created",
            "run_id": run_id,
            "store_slug": store_slug,
            "path": path,
            "document_id": document_id,
            "document_type": document_type,
            "timestamp": now_ms(),
        }
    )


async def emit_memory_write_blocked(
    callback: Optional[EventCallback],
    run_id: str,
    reason: str,
    severity: str,
) -> None:
    if not callback:
        return
    await callback(
        {
            "type": "memory.write.blocked",
            "run_id": run_id,
            "reason": reason,
            "severity": severity,
            "timestamp": now_ms(),
        }
    )


async def emit_memory_policy_denied(
    callback: Optional[EventCallback],
    run_id: str,
    operation: str,
    store_slug: str,
    reason: str,
) -> None:
    if not callback:
        return
    await callback(
        {
            "type": "memory.policy.denied",
            "run_id": run_id,
            "operation": operation,
            "store_slug": store_slug,
            "reason": reason,
            "timestamp": now_ms(),
        }
    )


async def emit_memory_promotion_proposed(
    callback: Optional[EventCallback],
    run_id: str,
    source_document_id: str,
    target_store_slug: str,
) -> None:
    if not callback:
        return
    await callback(
        {
            "type": "memory.promotion.proposed",
            "run_id": run_id,
            "source_document_id": source_document_id,
            "target_store_slug": target_store_slug,
            "timestamp": now_ms(),
        }
    )


async def emit_memory_safety_flagged(
    callback: Optional[EventCallback],
    run_id: str,
    finding_count: int,
    severity: str,
) -> None:
    if not callback:
        return
    await callback(
        {
            "type": "memory.safety.flagged",
            "run_id": run_id,
            "finding_count": finding_count,
            "severity": severity,
            "timestamp": now_ms(),
        }
    )
