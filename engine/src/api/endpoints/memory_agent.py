"""Internal memory endpoints called by the MCP server for agent tool execution.

These endpoints are NOT user-facing. They are authenticated with a shared
internal API key and expose the memory service operations that the MCP
memory tools invoke via HTTP.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..memory import repository as repo
from ..memory.policy import MemoryPolicyService
from ..memory.retrieval import MemoryRetrievalService
from ..memory.schemas import (
    MemoryDocumentType,
    MemoryPatchRequest,
    MemoryPromoteRequest,
    MemoryRiskLevel,
    MemoryScopeHints,
    MemoryWriteRequest,
)
from ..memory.service import MemoryService, MemoryWriteError
from ..models.memory import MemoryUsageKind

logger = logging.getLogger(__name__)

router = APIRouter()

_service = MemoryService()
_policy = MemoryPolicyService()
_retrieval = MemoryRetrievalService()


def _verify_internal_key(x_internal_api_key: str = Header()) -> None:
    if x_internal_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal API key")


def _safe_uuid(value: Optional[str]) -> Optional[UUID]:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------


class AgentContext(BaseModel):
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    run_id: Optional[str] = None


class MemorySearchBody(AgentContext):
    query: str
    scope_hints: Optional[Dict[str, Any]] = None
    document_types: Optional[List[str]] = None
    max_results: int = Field(default=6, ge=1, le=20)


class MemoryReadBody(AgentContext):
    document_id: Optional[str] = None
    store_slug: Optional[str] = None
    path: Optional[str] = None


class MemoryListBody(AgentContext):
    store_slug: str
    path_prefix: str = "/"


class MemoryHistoryBody(AgentContext):
    document_id: str
    limit: int = Field(default=5, ge=1, le=50)


class MemoryRememberBody(AgentContext):
    target_store_slug: str
    path: str
    title: Optional[str] = None
    document_type: str = "conversation_note"
    content: str
    confidence: int = Field(default=80, ge=0, le=100)
    source_tool_call_ids: List[str] = Field(default_factory=list)
    evidence_summary: str
    tags: List[str] = Field(default_factory=list)
    expected_sha256: Optional[str] = None


class MemoryPatchBody(AgentContext):
    document_id: str
    expected_sha256: str
    new_content: str
    patch_summary: str
    source_tool_call_ids: List[str] = Field(default_factory=list)
    evidence_summary: str


class MemoryProposePromotionBody(AgentContext):
    source_document_id: str
    target_store_slug: str
    target_path: str
    promotion_reason: str
    risk_level: str = "low"
    evidence_summary: str


# ---------------------------------------------------------------------------
# Internal endpoints
# ---------------------------------------------------------------------------


@router.post("/search", dependencies=[Depends(_verify_internal_key)])
async def agent_memory_search(body: MemorySearchBody) -> Dict[str, Any]:
    user_id = _safe_uuid(body.user_id)
    conversation_id = _safe_uuid(body.conversation_id)

    scope_raw = body.scope_hints or {}
    scope_hints = MemoryScopeHints(
        workspace=scope_raw.get("workspace", True),
        user=scope_raw.get("user", True),
        conversation_id=str(conversation_id) if conversation_id else None,
        environment=scope_raw.get("environment"),
        namespace=scope_raw.get("namespace"),
        service=scope_raw.get("service"),
    )

    document_types = None
    if body.document_types:
        valid: List[MemoryDocumentType] = []
        invalid: List[str] = []
        for dt in body.document_types:
            try:
                valid.append(MemoryDocumentType(dt))
            except ValueError:
                invalid.append(dt)
        if invalid:
            return {"error": True, "message": f"Unknown document_type(s): {', '.join(invalid)}"}
        if valid:
            document_types = valid

    results = await _retrieval.search(
        query=body.query,
        user_id=user_id,
        scope_hints=scope_hints,
        conversation_id=str(conversation_id) if conversation_id else None,
        max_results=body.max_results,
        document_types=document_types,
    )

    return {
        "results": [
            {
                "store": r.store_slug,
                "path": r.path,
                "document_id": str(r.document_id),
                "version_id": str(r.version_id) if r.version_id else None,
                "trust_level": r.trust_level.value,
                "document_type": r.document_type.value,
                "status": r.status,
                "score": r.score,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "title": r.title,
                "excerpt": r.excerpt,
            }
            for r in results
        ],
        "warning": "Memory is advisory. Verify live state before acting.",
    }


@router.post("/read", dependencies=[Depends(_verify_internal_key)])
async def agent_memory_read(body: MemoryReadBody) -> Dict[str, Any]:
    user_id = _safe_uuid(body.user_id)
    conversation_id = _safe_uuid(body.conversation_id)
    run_id = body.run_id

    document = None
    if body.document_id:
        doc_uuid = _safe_uuid(body.document_id)
        if not doc_uuid:
            return {"error": True, "message": f"Invalid document_id: {body.document_id!r}"}
        document = await repo.get_document_by_id(doc_uuid)
    elif body.store_slug and body.path:
        store = await repo.get_store_by_slug(body.store_slug)
        if store:
            document = await repo.get_document_by_store_path(store.id, body.path)

    if not document:
        return {"error": True, "message": "Document not found"}

    await document.fetch_related("store")

    decision = await _policy.resolve_read(user_id=user_id, store=document.store)
    if not decision.allowed:
        return {"error": True, "message": f"Access denied: {decision.reason}"}

    if conversation_id and run_id:
        try:
            await repo.record_memory_usage(
                conversation_id=conversation_id,
                run_id=_safe_uuid(run_id),
                document_id=document.id,
                version_id=document.current_version_id,
                usage_kind=MemoryUsageKind.READ,
            )
        except Exception:
            pass

    return {
        "document_id": str(document.id),
        "store_slug": document.store.slug,
        "path": document.path,
        "title": document.title,
        "content": document.content,
        "content_sha256": document.content_sha256,
        "document_type": document.document_type.value,
        "status": document.status.value,
        "trust_level": document.store.trust_level.value,
        "confidence": document.confidence,
        "tags": document.tags,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "version_id": (str(document.current_version_id) if document.current_version_id else None),
    }


@router.post("/list", dependencies=[Depends(_verify_internal_key)])
async def agent_memory_list(body: MemoryListBody) -> Dict[str, Any]:
    user_id = _safe_uuid(body.user_id)

    store = await repo.get_store_by_slug(body.store_slug)
    if not store:
        return {"error": True, "message": f"Store '{body.store_slug}' not found"}

    decision = await _policy.resolve_read(user_id=user_id, store=store)
    if not decision.allowed:
        return {"error": True, "message": f"Access denied: {decision.reason}"}

    documents = await repo.list_documents(
        store_id=store.id,
        path_prefix=body.path_prefix,
        limit=50,
    )

    return {
        "store_slug": body.store_slug,
        "path_prefix": body.path_prefix,
        "documents": [
            {
                "document_id": str(doc.id),
                "path": doc.path,
                "title": doc.title,
                "document_type": doc.document_type.value,
                "status": doc.status.value,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }
            for doc in documents
        ],
    }


@router.post("/history", dependencies=[Depends(_verify_internal_key)])
async def agent_memory_history(body: MemoryHistoryBody) -> Dict[str, Any]:
    user_id = _safe_uuid(body.user_id)
    doc_uuid = _safe_uuid(body.document_id)
    if not doc_uuid:
        return {"error": True, "message": f"Invalid document_id: {body.document_id!r}"}

    doc = await repo.get_document_by_id(doc_uuid)
    if not doc:
        return {"error": True, "message": "Document not found"}

    await doc.fetch_related("store")
    decision = await _policy.resolve_read(user_id=user_id, store=doc.store)
    if not decision.allowed:
        return {"error": True, "message": f"Access denied: {decision.reason}"}

    versions = await repo.get_versions_for_document(doc_uuid, limit=body.limit)

    return {
        "document_id": body.document_id,
        "versions": [
            {
                "version_id": str(v.id),
                "operation": v.operation.value,
                "actor_type": v.actor_type.value,
                "content_sha256": v.content_sha256,
                "redacted": v.redacted_at is not None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


@router.post("/remember", dependencies=[Depends(_verify_internal_key)])
async def agent_memory_remember(body: MemoryRememberBody) -> Dict[str, Any]:
    user_id = _safe_uuid(body.user_id)
    conversation_id = _safe_uuid(body.conversation_id)
    run_id = _safe_uuid(body.run_id)

    try:
        doc_type = MemoryDocumentType(body.document_type)
    except ValueError:
        return {"error": True, "message": f"Unknown document_type: {body.document_type!r}"}

    write_req = MemoryWriteRequest(
        target_store_slug=body.target_store_slug,
        path=body.path,
        title=body.title,
        document_type=doc_type,
        content=body.content,
        confidence=body.confidence,
        tags=body.tags,
        entities={},
        source_tool_call_ids=body.source_tool_call_ids,
        evidence_summary=body.evidence_summary,
        expected_sha256=body.expected_sha256,
    )

    return await _service.agent_remember(
        write_req=write_req,
        actor_user_id=user_id,
        actor_agent_run_id=run_id,
        actor_conversation_id=conversation_id,
    )


@router.post("/patch", dependencies=[Depends(_verify_internal_key)])
async def agent_memory_patch(body: MemoryPatchBody) -> Dict[str, Any]:
    user_id = _safe_uuid(body.user_id)
    conversation_id = _safe_uuid(body.conversation_id)
    run_id = _safe_uuid(body.run_id)

    patch_req = MemoryPatchRequest(
        document_id=body.document_id,
        expected_sha256=body.expected_sha256,
        new_content=body.new_content,
        patch_summary=body.patch_summary,
        source_tool_call_ids=body.source_tool_call_ids,
        evidence_summary=body.evidence_summary,
    )

    return await _service.agent_patch(
        patch_req=patch_req,
        actor_user_id=user_id,
        actor_agent_run_id=run_id,
        actor_conversation_id=conversation_id,
    )


@router.post("/propose-promotion", dependencies=[Depends(_verify_internal_key)])
async def agent_memory_propose_promotion(body: MemoryProposePromotionBody) -> Dict[str, Any]:
    conversation_id = _safe_uuid(body.conversation_id)
    run_id = _safe_uuid(body.run_id)

    try:
        risk = MemoryRiskLevel(body.risk_level)
    except ValueError:
        risk = MemoryRiskLevel.LOW

    promote_req = MemoryPromoteRequest(
        source_document_id=body.source_document_id,
        target_store_slug=body.target_store_slug,
        target_path=body.target_path,
        promotion_reason=body.promotion_reason,
        risk_level=risk,
        evidence_summary=body.evidence_summary,
    )

    try:
        item = await _service.propose_promotion(
            request=promote_req,
            actor_agent_run_id=run_id,
            actor_conversation_id=conversation_id,
        )
    except MemoryWriteError as e:
        return {"error": True, "message": e.reason}

    return {
        "proposed": True,
        "review_item_id": str(item.id),
        "status": "pending_review",
        "message": "Promotion proposal created. Pending admin review.",
    }
