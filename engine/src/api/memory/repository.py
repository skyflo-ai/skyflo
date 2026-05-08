"""Database query layer for the memory system."""

import hashlib
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from ..models.memory import (
    ConversationMemoryUsage,
    MemoryDocument,
    MemoryDocumentType,
    MemorySourceRef,
    MemoryStore,
    MemoryUsageKind,
    MemoryVersion,
)

logger = logging.getLogger(__name__)


def sha256_of(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Store queries
# ---------------------------------------------------------------------------


async def get_store_by_id(store_id: UUID) -> Optional[MemoryStore]:
    try:
        return await MemoryStore.get(id=store_id)
    except DoesNotExist:
        return None


async def get_store_by_slug(slug: str) -> Optional[MemoryStore]:
    try:
        return await MemoryStore.get(slug=slug, archived_at__isnull=True)
    except DoesNotExist:
        return None


async def list_stores(
    owner_user_id: Optional[UUID] = None,
    include_archived: bool = False,
) -> List[MemoryStore]:
    q = MemoryStore.all()
    if not include_archived:
        q = q.filter(archived_at__isnull=True)
    if owner_user_id is not None:
        q = q.filter(Q(owner_user_id=owner_user_id) | Q(owner_user_id__isnull=True))
    return await q.order_by("scope_type", "slug")


# ---------------------------------------------------------------------------
# Document queries
# ---------------------------------------------------------------------------


async def get_document_by_id(document_id: UUID) -> Optional[MemoryDocument]:
    try:
        return await MemoryDocument.get(id=document_id, deleted_at__isnull=True).select_related(
            "store"
        )
    except DoesNotExist:
        return None


async def get_document_by_store_path(store_id: UUID, path: str) -> Optional[MemoryDocument]:
    try:
        return await MemoryDocument.get(
            store_id=store_id, path=path, deleted_at__isnull=True
        ).select_related("store")
    except DoesNotExist:
        return None


async def list_documents(
    store_id: UUID,
    path_prefix: str = "/",
    document_types: Optional[List[MemoryDocumentType]] = None,
    include_deleted: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> List[MemoryDocument]:
    q = MemoryDocument.filter(store_id=store_id)
    if not include_deleted:
        q = q.filter(deleted_at__isnull=True)
    if path_prefix and path_prefix != "/":
        q = q.filter(path__startswith=path_prefix)
    if document_types:
        q = q.filter(document_type__in=[dt.value for dt in document_types])
    return await q.order_by("path").offset(offset).limit(limit)


# ---------------------------------------------------------------------------
# Full-text search
# ---------------------------------------------------------------------------


async def fts_search(
    query: str,
    store_ids: List[UUID],
    max_results: int = 10,
    include_drafts: bool = False,
    document_types: Optional[List[MemoryDocumentType]] = None,
) -> List[Dict[str, Any]]:
    """
    Run Postgres full-text search on memory_documents via raw SQL.
    Returns list of dicts with document fields plus ts_rank score.
    """
    if not query.strip() or not store_ids:
        return []

    # All dynamic values are passed as positional parameters to avoid SQL injection.
    # $1 = query, $2 = max_results, $3 = store_id array, $4 = doc_type array (optional)
    params: List[Any] = [query, max_results, [str(sid) for sid in store_ids]]

    if include_drafts:
        status_clause = "AND md.status = ANY(ARRAY['active', 'draft', 'candidate'])"
    else:
        status_clause = "AND md.status = 'active'"

    type_clause = ""
    if document_types:
        params.append([dt.value for dt in document_types])
        type_clause = f"AND md.document_type = ANY(${len(params)}::text[])"

    sql = f"""
        SELECT
            md.id,
            md.store_id,
            md.path,
            md.title,
            md.content,
            md.content_sha256,
            md.document_type,
            md.status,
            md.tags,
            md.entities,
            md.confidence,
            md.current_version_id,
            md.updated_at,
            ts_rank(md.search_vector, plainto_tsquery('english', $1)) AS text_score,
            ms.slug AS store_slug,
            ms.trust_level
        FROM memory_documents md
        JOIN memory_stores ms ON ms.id = md.store_id
        WHERE
            md.store_id = ANY($3::uuid[])
            AND md.deleted_at IS NULL
            AND md.search_vector @@ plainto_tsquery('english', $1)
            {status_clause}
            {type_clause}
        ORDER BY text_score DESC
        LIMIT $2
    """

    from tortoise import connections

    conn = connections.get("default")
    try:
        rows = await conn.execute_query_dict(sql, params)
        return rows
    except Exception as e:
        logger.error(f"FTS query failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Version queries
# ---------------------------------------------------------------------------


async def get_versions_for_document(document_id: UUID, limit: int = 10) -> List[MemoryVersion]:
    return await MemoryVersion.filter(document_id=document_id).order_by("-created_at").limit(limit)


async def create_version(
    store_id: UUID,
    document_id: Optional[UUID],
    path: str,
    operation: str,
    content: Optional[str],
    actor_type: str,
    actor_user_id: Optional[UUID] = None,
    actor_agent_run_id: Optional[UUID] = None,
    actor_conversation_id: Optional[UUID] = None,
    previous_version_id: Optional[UUID] = None,
) -> MemoryVersion:
    sha = sha256_of(content) if content is not None else None
    return await MemoryVersion.create(
        store_id=store_id,
        document_id=document_id,
        path=path,
        operation=operation,
        content=content,
        content_sha256=sha,
        content_size_bytes=len(content.encode("utf-8")) if content else 0,
        previous_version_id=previous_version_id,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        actor_agent_run_id=actor_agent_run_id,
        actor_conversation_id=actor_conversation_id,
    )


# ---------------------------------------------------------------------------
# Source ref queries
# ---------------------------------------------------------------------------


async def create_source_ref(
    document_id: UUID,
    version_id: Optional[UUID],
    evidence_summary: str,
    evidence_kind: str,
    conversation_id: Optional[UUID] = None,
    run_id: Optional[UUID] = None,
    tool_call_id: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> MemorySourceRef:
    return await MemorySourceRef.create(
        document_id=document_id,
        version_id=version_id,
        conversation_id=conversation_id,
        run_id=run_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        evidence_summary=evidence_summary,
        evidence_kind=evidence_kind,
    )


async def get_source_refs_for_document(document_id: UUID) -> List[MemorySourceRef]:
    return await MemorySourceRef.filter(document_id=document_id).order_by("-created_at")


# ---------------------------------------------------------------------------
# Memory usage audit
# ---------------------------------------------------------------------------


async def record_memory_usage(
    conversation_id: UUID,
    run_id: UUID,
    document_id: UUID,
    version_id: Optional[UUID],
    usage_kind: MemoryUsageKind,
) -> None:
    try:
        await ConversationMemoryUsage.create(
            conversation_id=conversation_id,
            run_id=run_id,
            document_id=document_id,
            version_id=version_id,
            usage_kind=usage_kind,
        )
    except Exception as e:
        logger.error(f"Failed to record memory usage: {e}")


async def record_memory_usage_bulk(
    conversation_id: UUID,
    run_id: UUID,
    entries: List[Dict[str, Any]],
) -> None:
    """Insert multiple usage records in a single round-trip.

    Each entry must contain: document_id (UUID), version_id (UUID | None),
    usage_kind (MemoryUsageKind).
    """
    if not entries:
        return
    try:
        instances = [
            ConversationMemoryUsage(
                conversation_id=conversation_id,
                run_id=run_id,
                document_id=e["document_id"],
                version_id=e.get("version_id"),
                usage_kind=e["usage_kind"],
            )
            for e in entries
        ]
        await ConversationMemoryUsage.bulk_create(instances)
    except Exception as e:
        logger.error(f"Failed to bulk record memory usage: {e}")


async def get_memory_usage_for_run(run_id: UUID) -> List[ConversationMemoryUsage]:
    return await ConversationMemoryUsage.filter(run_id=run_id).order_by("created_at")
