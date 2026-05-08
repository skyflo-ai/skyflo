"""Pydantic schemas and shared enums for the memory system."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..models.memory import (
    DreamReviewAction,
    DreamReviewStatus,
    DreamStatus,
    DreamType,
    MemoryAccessMode,
    MemoryActorType,
    MemoryDocumentStatus,
    MemoryDocumentType,
    MemoryEvidenceKind,
    MemoryOperation,
    MemoryRiskLevel,
    MemoryScopeType,
    MemoryTrustLevel,
)

__all__ = [
    "MemoryScopeType",
    "MemoryTrustLevel",
    "MemoryAccessMode",
    "MemoryDocumentType",
    "MemoryDocumentStatus",
    "MemoryOperation",
    "MemoryActorType",
    "MemoryEvidenceKind",
    "MemoryRiskLevel",
    "DreamType",
    "DreamStatus",
    "DreamReviewAction",
    "DreamReviewStatus",
    "MemoryStoreRead",
    "MemoryStoreCreate",
    "MemoryStoreUpdate",
    "MemoryDocumentRead",
    "MemoryDocumentCreate",
    "MemoryDocumentUpdate",
    "MemoryVersionRead",
    "MemorySourceRefRead",
    "MemorySourceRefCreate",
    "MemorySearchRequest",
    "MemorySearchResult",
    "MemorySearchResponse",
    "MemoryWriteRequest",
    "MemoryPatchRequest",
    "MemoryPromoteRequest",
    "MemoryConflictError",
    "MemoryPolicyDecision",
    "MemorySafetyFinding",
    "MemorySafetyResult",
    "MemoryHit",
    "MemoryScopeHints",
    "MemoryRedactVersionBody",
]


# ---------------------------------------------------------------------------
# Store schemas
# ---------------------------------------------------------------------------


class MemoryStoreCreate(BaseModel):
    name: str = Field(max_length=160)
    slug: str = Field(max_length=160)
    description: str = ""
    scope_type: MemoryScopeType
    trust_level: MemoryTrustLevel
    default_access: MemoryAccessMode
    owner_user_id: Optional[uuid.UUID] = None


class MemoryStoreUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=160)
    description: Optional[str] = None
    trust_level: Optional[MemoryTrustLevel] = None
    default_access: Optional[MemoryAccessMode] = None


class MemoryStoreRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str
    scope_type: MemoryScopeType
    trust_level: MemoryTrustLevel
    default_access: MemoryAccessMode
    owner_user_id: Optional[uuid.UUID]
    archived_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Document schemas
# ---------------------------------------------------------------------------


class MemoryDocumentCreate(BaseModel):
    path: str = Field(max_length=512)
    title: Optional[str] = Field(default=None, max_length=240)
    content: str
    document_type: MemoryDocumentType
    status: MemoryDocumentStatus = MemoryDocumentStatus.ACTIVE
    tags: List[str] = Field(default_factory=list)
    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: int = Field(default=100, ge=0, le=100)


class MemoryDocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=240)
    content: Optional[str] = None
    expected_sha256: str
    tags: Optional[List[str]] = None
    entities: Optional[Dict[str, Any]] = None
    confidence: Optional[int] = Field(default=None, ge=0, le=100)
    status: Optional[MemoryDocumentStatus] = None


class MemoryDocumentRead(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    path: str
    title: Optional[str]
    content: str
    content_sha256: str
    content_size_bytes: int
    document_type: MemoryDocumentType
    status: MemoryDocumentStatus
    tags: List[str]
    entities: Dict[str, Any]
    confidence: int
    current_version_id: Optional[uuid.UUID]
    created_by_user_id: Optional[uuid.UUID]
    created_by_agent_run_id: Optional[uuid.UUID]
    created_by_conversation_id: Optional[uuid.UUID]
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Version schemas
# ---------------------------------------------------------------------------


class MemoryVersionRead(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    document_id: Optional[uuid.UUID]
    path: str
    operation: MemoryOperation
    content: Optional[str]
    content_sha256: Optional[str]
    content_size_bytes: Optional[int]
    previous_version_id: Optional[uuid.UUID]
    actor_type: MemoryActorType
    actor_user_id: Optional[uuid.UUID]
    actor_agent_run_id: Optional[uuid.UUID]
    actor_conversation_id: Optional[uuid.UUID]
    redacted_at: Optional[datetime]
    redaction_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Source ref schemas
# ---------------------------------------------------------------------------


class MemorySourceRefCreate(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    run_id: Optional[uuid.UUID] = None
    tool_call_id: Optional[str] = Field(default=None, max_length=160)
    tool_name: Optional[str] = Field(default=None, max_length=160)
    tool_args_hash: Optional[str] = Field(default=None, max_length=64)
    tool_result_hash: Optional[str] = Field(default=None, max_length=64)
    evidence_summary: str
    evidence_kind: MemoryEvidenceKind


class MemorySourceRefRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version_id: Optional[uuid.UUID]
    conversation_id: Optional[uuid.UUID]
    run_id: Optional[uuid.UUID]
    tool_call_id: Optional[str]
    tool_name: Optional[str]
    evidence_summary: str
    evidence_kind: MemoryEvidenceKind
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Search schemas
# ---------------------------------------------------------------------------


class MemoryScopeHints(BaseModel):
    workspace: bool = True
    user: bool = True
    conversation_id: Optional[str] = None
    environment: Optional[str] = None
    namespace: Optional[str] = None
    service: Optional[str] = None


class MemorySearchRequest(BaseModel):
    query: str
    scope_hints: Optional[MemoryScopeHints] = None
    document_types: Optional[List[MemoryDocumentType]] = None
    max_results: int = Field(default=6, ge=1, le=20)
    include_drafts: bool = False


class MemorySearchResult(BaseModel):
    store_slug: str
    path: str
    document_id: uuid.UUID
    version_id: Optional[uuid.UUID]
    trust_level: MemoryTrustLevel
    document_type: MemoryDocumentType
    status: MemoryDocumentStatus
    score: float
    updated_at: datetime
    excerpt: str
    title: Optional[str]


class MemorySearchResponse(BaseModel):
    results: List[MemorySearchResult]
    warning: str = "Memory is advisory. Verify live state before acting."


# ---------------------------------------------------------------------------
# Write request schemas (agent tools)
# ---------------------------------------------------------------------------


class MemoryWriteRequest(BaseModel):
    target_store_slug: str
    path: str
    title: Optional[str] = None
    document_type: MemoryDocumentType
    content: str
    confidence: int = Field(default=80, ge=0, le=100)
    tags: List[str] = Field(default_factory=list)
    entities: Dict[str, Any] = Field(default_factory=dict)
    source_tool_call_ids: List[str] = Field(default_factory=list)
    evidence_summary: str
    expected_sha256: Optional[str] = None


class MemoryPatchRequest(BaseModel):
    document_id: str
    expected_sha256: str
    new_content: str
    patch_summary: str
    source_tool_call_ids: List[str] = Field(default_factory=list)
    evidence_summary: str


class MemoryPromoteRequest(BaseModel):
    source_document_id: str
    target_store_slug: str
    target_path: str
    promotion_reason: str
    risk_level: MemoryRiskLevel = MemoryRiskLevel.LOW
    evidence_summary: str


# ---------------------------------------------------------------------------
# Policy and safety schemas
# ---------------------------------------------------------------------------


class MemoryPolicyDecision(BaseModel):
    allowed: bool
    requires_review: bool = False
    reason: str
    effective_access: MemoryAccessMode


class MemorySafetyFinding(BaseModel):
    pattern_name: str
    severity: str
    description: str
    redacted: bool = False


class MemorySafetyResult(BaseModel):
    allowed: bool
    redacted_content: Optional[str]
    findings: List[MemorySafetyFinding]
    severity: str  # none | low | medium | high | critical


# ---------------------------------------------------------------------------
# Memory hit (injected into model context)
# ---------------------------------------------------------------------------


class MemoryHit(BaseModel):
    document_id: str
    version_id: Optional[str]
    store_slug: str
    path: str
    trust_level: MemoryTrustLevel
    document_type: MemoryDocumentType
    excerpt: str
    title: Optional[str]
    updated_at: Optional[datetime]
    score: float
    source_summary: Optional[str] = None

    def minimal(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "version_id": self.version_id,
            "store_slug": self.store_slug,
            "path": self.path,
            "trust_level": self.trust_level.value,
        }


# ---------------------------------------------------------------------------
# Conflict error
# ---------------------------------------------------------------------------


class MemoryConflictError(BaseModel):
    error: bool = True
    type: str = "memory_conflict"
    message: str = "Memory changed since it was read. Re-read, merge, and retry."
    current_sha256: str
    latest_excerpt: str


class MemoryRedactVersionBody(BaseModel):
    reason: str
