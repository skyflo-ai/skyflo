"""Memory API endpoints."""

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import rate_limit_dependency
from ..memory import repository as repo
from ..memory.policy import MemoryPolicyService
from ..memory.retrieval import MemoryRetrievalService
from ..memory.schemas import (
    MemoryDocumentCreate,
    MemoryDocumentType,
    MemoryDocumentUpdate,
    MemoryRedactVersionBody,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStoreCreate,
    MemoryStoreUpdate,
)
from ..memory.service import MemoryService, MemoryWriteError
from ..models.memory import MemoryActorType
from ..services.auth import fastapi_users

logger = logging.getLogger(__name__)

router = APIRouter()
_service = MemoryService()
_policy = MemoryPolicyService()
_retrieval = MemoryRetrievalService()


def _is_admin(user) -> bool:
    return getattr(user, "is_superuser", False) or getattr(user, "role", "") == "admin"


def _require_auth(user) -> None:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as err:
        raise HTTPException(status_code=422, detail=f"Invalid {label}: {value!r}") from err


# ---------------------------------------------------------------------------
# Store endpoints
# ---------------------------------------------------------------------------


@router.post("/stores", dependencies=[rate_limit_dependency])
async def create_store(
    body: MemoryStoreCreate,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    store = await _service.create_store(body)
    return {"status": "success", "store_id": str(store.id), "slug": store.slug}


@router.get("/stores")
async def list_stores(
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    _require_auth(user)
    user_id = getattr(user, "id", None)
    stores = await repo.list_stores(owner_user_id=user_id)
    accessible = []
    for s in stores:
        decision = await _policy.resolve_read(user_id=user_id, store=s)
        if decision.allowed:
            accessible.append(s)
    return {
        "stores": [
            {
                "id": str(s.id),
                "slug": s.slug,
                "name": s.name,
                "scope_type": s.scope_type.value,
                "trust_level": s.trust_level.value,
                "default_access": s.default_access.value,
                "archived_at": s.archived_at.isoformat() if s.archived_at else None,
            }
            for s in accessible
        ]
    }


@router.get("/stores/{store_id}")
async def get_store(
    store_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    _require_auth(user)
    store = await repo.get_store_by_id(_parse_uuid(store_id, "store_id"))
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    user_id = getattr(user, "id", None)
    decision = await _policy.resolve_read(user_id=user_id, store=store)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    return {
        "id": str(store.id),
        "slug": store.slug,
        "name": store.name,
        "description": store.description,
        "scope_type": store.scope_type.value,
        "trust_level": store.trust_level.value,
        "default_access": store.default_access.value,
        "owner_user_id": str(store.owner_user_id) if store.owner_user_id else None,
        "archived_at": store.archived_at.isoformat() if store.archived_at else None,
        "created_at": store.created_at.isoformat(),
        "updated_at": store.updated_at.isoformat(),
    }


@router.patch("/stores/{store_id}")
async def update_store(
    store_id: str,
    body: MemoryStoreUpdate,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    store = await _service.update_store(_parse_uuid(store_id, "store_id"), body)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return {"status": "success", "store_id": str(store.id)}


@router.post("/stores/{store_id}/archive")
async def archive_store(
    store_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    store = await _service.archive_store(_parse_uuid(store_id, "store_id"))
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return {"status": "success", "archived_at": store.archived_at.isoformat()}


# ---------------------------------------------------------------------------
# Document endpoints
# ---------------------------------------------------------------------------


@router.get("/stores/{store_id}/documents")
async def list_documents(
    store_id: str,
    path_prefix: str = Query(default="/"),
    document_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    _require_auth(user)
    store = await repo.get_store_by_id(_parse_uuid(store_id, "store_id"))
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    user_id = getattr(user, "id", None)
    decision = await _policy.resolve_read(user_id=user_id, store=store)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    doc_types = None
    if document_type:
        try:
            doc_types = [MemoryDocumentType(document_type)]
        except ValueError as err:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid document_type: {document_type}",
            ) from err

    docs = await repo.list_documents(
        store_id=_parse_uuid(store_id, "store_id"),
        path_prefix=path_prefix,
        document_types=doc_types,
        limit=limit,
        offset=offset,
    )
    return {
        "store_id": store_id,
        "documents": [
            {
                "id": str(d.id),
                "path": d.path,
                "title": d.title,
                "document_type": d.document_type.value,
                "status": d.status.value,
                "confidence": d.confidence,
                "tags": d.tags,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in docs
        ],
    }


@router.post("/stores/{store_id}/documents")
async def create_document(
    store_id: str,
    body: MemoryDocumentCreate,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    store = await repo.get_store_by_id(_parse_uuid(store_id, "store_id"))
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    user_id = getattr(user, "id", None)
    policy = await _policy.resolve_admin_write(_is_admin(user), store)
    if not policy.allowed:
        raise HTTPException(status_code=403, detail=policy.reason)

    document = await _service.create_document(
        store=store,
        data=body,
        actor_type=MemoryActorType.ADMIN,
        actor_user_id=user_id,
    )
    return {"status": "success", "document_id": str(document.id), "path": document.path}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    _require_auth(user)
    doc = await repo.get_document_by_id(_parse_uuid(document_id, "document_id"))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    user_id = getattr(user, "id", None)
    decision = await _policy.resolve_read(user_id=user_id, store=doc.store)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    return {
        "id": str(doc.id),
        "store_id": str(doc.store_id),
        "store_slug": doc.store.slug,
        "path": doc.path,
        "title": doc.title,
        "content": doc.content,
        "content_sha256": doc.content_sha256,
        "document_type": doc.document_type.value,
        "status": doc.status.value,
        "confidence": doc.confidence,
        "tags": doc.tags,
        "entities": doc.entities,
        "current_version_id": str(doc.current_version_id) if doc.current_version_id else None,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    body: MemoryDocumentUpdate,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        doc = await _service.update_document(
            document_id=_parse_uuid(document_id, "document_id"),
            data=body,
            actor_type=MemoryActorType.ADMIN,
            actor_user_id=getattr(user, "id", None),
        )
    except MemoryWriteError as e:
        if e.is_conflict:
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "memory_conflict",
                    "message": e.reason,
                    "current_sha256": e.conflict_data.get("current_sha256"),
                },
            ) from e
        raise HTTPException(status_code=400, detail=e.reason) from e
    return {
        "status": "success",
        "document_id": str(doc.id),
        "version_id": str(doc.current_version_id),
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    deleted = await _service.delete_document(
        document_id=_parse_uuid(document_id, "document_id"),
        actor_user_id=getattr(user, "id", None),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "success", "deleted": True}


# ---------------------------------------------------------------------------
# Version endpoints
# ---------------------------------------------------------------------------


@router.get("/documents/{document_id}/versions")
async def get_document_versions(
    document_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    _require_auth(user)
    doc_uuid = _parse_uuid(document_id, "document_id")
    doc = await repo.get_document_by_id(doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    user_id = getattr(user, "id", None)
    decision = await _policy.resolve_read(user_id=user_id, store=doc.store)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    versions = await repo.get_versions_for_document(doc_uuid, limit=limit)
    return {
        "document_id": document_id,
        "versions": [
            {
                "id": str(v.id),
                "operation": v.operation.value,
                "actor_type": v.actor_type.value,
                "content_sha256": v.content_sha256,
                "redacted": v.redacted_at is not None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


@router.post("/versions/{version_id}/redact")
async def redact_version(
    version_id: str,
    body: MemoryRedactVersionBody,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    version = await _service.redact_version(
        version_id=_parse_uuid(version_id, "version_id"),
        admin_user_id=user.id,
        reason=body.reason,
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"status": "success", "redacted_at": version.redacted_at.isoformat()}


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------


@router.post("/search", dependencies=[rate_limit_dependency])
async def search_memory(
    body: MemorySearchRequest,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> MemorySearchResponse:
    _require_auth(user)
    user_id = getattr(user, "id", None)
    results = await _retrieval.search(
        query=body.query,
        user_id=user_id,
        scope_hints=body.scope_hints,
        max_results=body.max_results,
        include_drafts=body.include_drafts,
        document_types=body.document_types,
    )
    return MemorySearchResponse(results=results)
