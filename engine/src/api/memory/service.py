"""MemoryService -- core CRUD with versioning, policy, and safety enforcement."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from ..models.memory import (
    DreamReviewAction,
    DreamReviewItem,
    DreamReviewStatus,
    MemoryActorType,
    MemoryDocument,
    MemoryDocumentStatus,
    MemoryOperation,
    MemoryScopeType,
    MemoryStore,
    MemoryVersion,
)
from . import repository as repo
from .policy import MemoryPolicyService
from .safety import MemorySafetyScanner
from .schemas import (
    MemoryDocumentCreate,
    MemoryDocumentUpdate,
    MemoryPatchRequest,
    MemoryPromoteRequest,
    MemoryStoreCreate,
    MemoryStoreUpdate,
    MemoryWriteRequest,
)

logger = logging.getLogger(__name__)

_policy = MemoryPolicyService()
_safety = MemorySafetyScanner()


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class MemoryWriteError(Exception):
    def __init__(
        self, reason: str, is_conflict: bool = False, conflict_data: Optional[Dict] = None
    ):
        super().__init__(reason)
        self.reason = reason
        self.is_conflict = is_conflict
        self.conflict_data = conflict_data or {}


class MemoryService:
    # ---------------------------------------------------------------------------
    # Store operations
    # ---------------------------------------------------------------------------

    async def create_store(self, data: MemoryStoreCreate) -> MemoryStore:
        return await MemoryStore.create(
            name=data.name,
            slug=data.slug,
            description=data.description,
            scope_type=data.scope_type,
            trust_level=data.trust_level,
            default_access=data.default_access,
            owner_user_id=data.owner_user_id,
        )

    async def update_store(self, store_id: UUID, data: MemoryStoreUpdate) -> Optional[MemoryStore]:
        store = await repo.get_store_by_id(store_id)
        if not store:
            return None
        if data.name is not None:
            store.name = data.name
        if data.description is not None:
            store.description = data.description
        if data.trust_level is not None:
            store.trust_level = data.trust_level
        if data.default_access is not None:
            store.default_access = data.default_access
        await store.save()
        return store

    async def archive_store(self, store_id: UUID) -> Optional[MemoryStore]:
        store = await repo.get_store_by_id(store_id)
        if not store:
            return None
        store.archived_at = datetime.now(timezone.utc)
        await store.save()
        return store

    # ---------------------------------------------------------------------------
    # Document creation
    # ---------------------------------------------------------------------------

    async def create_document(
        self,
        store: MemoryStore,
        data: MemoryDocumentCreate,
        actor_type: MemoryActorType = MemoryActorType.USER,
        actor_user_id: Optional[UUID] = None,
        actor_agent_run_id: Optional[UUID] = None,
        actor_conversation_id: Optional[UUID] = None,
    ) -> MemoryDocument:
        sha = _sha256(data.content)
        byte_size = len(data.content.encode("utf-8"))

        async with in_transaction():
            document = await MemoryDocument.create(
                store=store,
                path=data.path,
                title=data.title,
                content=data.content,
                content_sha256=sha,
                content_size_bytes=byte_size,
                document_type=data.document_type,
                status=data.status,
                tags=data.tags,
                entities=data.entities,
                confidence=data.confidence,
                created_by_user_id=actor_user_id,
                created_by_agent_run_id=actor_agent_run_id,
                created_by_conversation_id=actor_conversation_id,
            )

            version = await repo.create_version(
                store_id=store.id,
                document_id=document.id,
                path=data.path,
                operation=MemoryOperation.CREATE.value,
                content=data.content,
                actor_type=actor_type.value,
                actor_user_id=actor_user_id,
                actor_agent_run_id=actor_agent_run_id,
                actor_conversation_id=actor_conversation_id,
            )

            document.current_version_id = version.id
            await document.save()

        return document

    # ---------------------------------------------------------------------------
    # Document update (full replace with SHA check)
    # ---------------------------------------------------------------------------

    async def update_document(
        self,
        document_id: UUID,
        data: MemoryDocumentUpdate,
        actor_type: MemoryActorType = MemoryActorType.USER,
        actor_user_id: Optional[UUID] = None,
        actor_agent_run_id: Optional[UUID] = None,
        actor_conversation_id: Optional[UUID] = None,
    ) -> MemoryDocument:
        async with in_transaction():
            document = (
                await MemoryDocument.filter(id=document_id, deleted_at__isnull=True)
                .select_for_update()
                .first()
            )
            if not document:
                raise MemoryWriteError(f"Document {document_id} not found")

            if document.content_sha256 != data.expected_sha256:
                raise MemoryWriteError(
                    reason="Stale SHA -- document was modified since last read",
                    is_conflict=True,
                    conflict_data={
                        "current_sha256": document.content_sha256,
                    },
                )

            new_content = data.content if data.content is not None else document.content
            sha = _sha256(new_content)
            byte_size = len(new_content.encode("utf-8"))
            prev_version_id = document.current_version_id

            if data.title is not None:
                document.title = data.title
            document.content = new_content
            document.content_sha256 = sha
            document.content_size_bytes = byte_size
            if data.tags is not None:
                document.tags = data.tags
            if data.entities is not None:
                document.entities = data.entities
            if data.confidence is not None:
                document.confidence = data.confidence
            if data.status is not None:
                document.status = data.status

            version = await repo.create_version(
                store_id=document.store_id,
                document_id=document.id,
                path=document.path,
                operation=MemoryOperation.UPDATE.value,
                content=new_content,
                actor_type=actor_type.value,
                actor_user_id=actor_user_id,
                actor_agent_run_id=actor_agent_run_id,
                actor_conversation_id=actor_conversation_id,
                previous_version_id=prev_version_id,
            )

            document.current_version_id = version.id
            await document.save()

        return document

    # ---------------------------------------------------------------------------
    # Document patch (content-only with SHA check)
    # ---------------------------------------------------------------------------

    async def patch_document(
        self,
        document_id: UUID,
        expected_sha256: str,
        new_content: str,
        actor_type: MemoryActorType = MemoryActorType.AGENT,
        actor_user_id: Optional[UUID] = None,
        actor_agent_run_id: Optional[UUID] = None,
        actor_conversation_id: Optional[UUID] = None,
    ) -> MemoryDocument:
        async with in_transaction():
            document = (
                await MemoryDocument.filter(id=document_id, deleted_at__isnull=True)
                .select_for_update()
                .first()
            )
            if not document:
                raise MemoryWriteError(f"Document {document_id} not found")

            if document.content_sha256 != expected_sha256:
                raise MemoryWriteError(
                    reason="Stale SHA -- document was modified since last read",
                    is_conflict=True,
                    conflict_data={
                        "current_sha256": document.content_sha256,
                        "latest_excerpt": document.content[:200],
                    },
                )

            sha = _sha256(new_content)
            byte_size = len(new_content.encode("utf-8"))
            prev_version_id = document.current_version_id

            document.content = new_content
            document.content_sha256 = sha
            document.content_size_bytes = byte_size

            version = await repo.create_version(
                store_id=document.store_id,
                document_id=document.id,
                path=document.path,
                operation=MemoryOperation.PATCH.value,
                content=new_content,
                actor_type=actor_type.value,
                actor_user_id=actor_user_id,
                actor_agent_run_id=actor_agent_run_id,
                actor_conversation_id=actor_conversation_id,
                previous_version_id=prev_version_id,
            )

            document.current_version_id = version.id
            await document.save()

        return document

    # ---------------------------------------------------------------------------
    # Soft delete
    # ---------------------------------------------------------------------------

    async def delete_document(
        self,
        document_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> bool:
        document = await repo.get_document_by_id(document_id)
        if not document:
            return False

        version = await repo.create_version(
            store_id=document.store_id,
            document_id=document.id,
            path=document.path,
            operation=MemoryOperation.DELETE.value,
            content=None,
            actor_type=MemoryActorType.USER.value,
            actor_user_id=actor_user_id,
            previous_version_id=document.current_version_id,
        )

        document.deleted_at = datetime.now(timezone.utc)
        document.status = MemoryDocumentStatus.ARCHIVED
        document.current_version_id = version.id
        await document.save()
        return True

    # ---------------------------------------------------------------------------
    # Redact a version
    # ---------------------------------------------------------------------------

    async def redact_version(
        self,
        version_id: UUID,
        admin_user_id: UUID,
        reason: str,
    ) -> Optional[MemoryVersion]:
        try:
            version = await MemoryVersion.get(id=version_id)
        except DoesNotExist:
            return None

        version.redacted_at = datetime.now(timezone.utc)
        version.redacted_by_user_id = admin_user_id
        version.redaction_reason = reason
        version.content = None
        version.content_sha256 = None
        await version.save()
        return version

    # ---------------------------------------------------------------------------
    # Propose promotion (agent tool)
    # ---------------------------------------------------------------------------

    async def propose_promotion(
        self,
        request: MemoryPromoteRequest,
        actor_agent_run_id: Optional[UUID] = None,
        actor_conversation_id: Optional[UUID] = None,
    ) -> DreamReviewItem:
        """Create a pending DreamReviewItem for admin review."""
        source_doc = await repo.get_document_by_id(UUID(request.source_document_id))
        if not source_doc:
            raise MemoryWriteError(
                f"Source document {request.source_document_id} not found or has been deleted"
            )

        target_store = await repo.get_store_by_slug(request.target_store_slug)
        target_store_id = target_store.id if target_store else None

        from ..config import settings
        from ..models.memory import DreamJob, DreamStatus, DreamType

        # Reuse a single shared promotion queue job rather than creating one per call.
        # In Phase 1 there is no worker; the job is a required FK anchor only.
        dream, _ = await DreamJob.get_or_create(
            dream_type=DreamType.RUNBOOK_PROMOTION,
            status=DreamStatus.PENDING,
            defaults={
                "model": settings.LLM_MODEL or "unknown",
                "instructions": "Phase 1 promotion review queue",
            },
        )

        item = await DreamReviewItem.create(
            dream=dream,
            source_document_id=request.source_document_id,
            target_store_id=target_store_id,
            target_path=request.target_path,
            action=DreamReviewAction.PROMOTE,
            status=DreamReviewStatus.PENDING,
            rationale=request.promotion_reason,
            risk_level=request.risk_level,
            diff_json={
                "evidence_summary": request.evidence_summary,
                "source_document_id": request.source_document_id,
                "target_store_slug": request.target_store_slug,
            },
        )

        return item

    # ---------------------------------------------------------------------------
    # Agent write entrypoint (used by memory virtual tools)
    # ---------------------------------------------------------------------------

    async def agent_remember(
        self,
        write_req: MemoryWriteRequest,
        actor_user_id: Optional[UUID] = None,
        actor_agent_run_id: Optional[UUID] = None,
        actor_conversation_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Validate policy + safety, then create or update a memory document.
        Returns a dict suitable for tool result content.
        """
        store = await repo.get_store_by_slug(write_req.target_store_slug)
        if not store:
            return {"error": True, "message": f"Unknown store slug: {write_req.target_store_slug}"}

        policy = await _policy.resolve_write(
            user_id=actor_user_id,
            store=store,
            document_type=write_req.document_type,
        )
        if not policy.allowed:
            return {"error": True, "message": f"Policy denied: {policy.reason}"}

        from ..config import settings as _settings

        if _settings.MEMORY_REQUIRE_SOURCE_REFS and not write_req.evidence_summary:
            return {
                "error": True,
                "message": "evidence_summary is required (MEMORY_REQUIRE_SOURCE_REFS is enabled)",
            }

        safety = _safety.scan_write(write_req.content, store.scope_type)
        if not safety.allowed:
            descriptions = "; ".join(f.description for f in safety.findings)
            return {
                "error": True,
                "blocked": True,
                "severity": safety.severity,
                "message": f"Content blocked by safety scanner: {descriptions}",
            }

        existing = await repo.get_document_by_store_path(store.id, write_req.path)

        if existing:
            # Optimistic concurrency: if the caller supplied an expected SHA, verify it.
            if write_req.expected_sha256 and existing.content_sha256 != write_req.expected_sha256:
                return {
                    "error": True,
                    "type": "memory_conflict",
                    "message": (
                        "Memory changed since last read. "
                        "Re-read and retry with updated expected_sha256."
                    ),
                    "current_sha256": existing.content_sha256,
                }

            async with in_transaction():
                existing.content = write_req.content
                existing.content_sha256 = _sha256(write_req.content)
                existing.content_size_bytes = len(write_req.content.encode("utf-8"))
                existing.confidence = write_req.confidence
                if write_req.tags:
                    existing.tags = write_req.tags
                if write_req.entities:
                    existing.entities = write_req.entities

                version = await repo.create_version(
                    store_id=store.id,
                    document_id=existing.id,
                    path=write_req.path,
                    operation=MemoryOperation.UPDATE.value,
                    content=write_req.content,
                    actor_type=MemoryActorType.AGENT.value,
                    actor_agent_run_id=actor_agent_run_id,
                    actor_conversation_id=actor_conversation_id,
                    previous_version_id=existing.current_version_id,
                )
                existing.current_version_id = version.id
                await existing.save()

            if write_req.evidence_summary:
                await repo.create_source_ref(
                    document_id=existing.id,
                    version_id=version.id,
                    evidence_summary=write_req.evidence_summary,
                    evidence_kind="tool_result"
                    if write_req.source_tool_call_ids
                    else "incident_summary",
                    conversation_id=actor_conversation_id,
                    run_id=actor_agent_run_id,
                    tool_call_id=write_req.source_tool_call_ids[0]
                    if write_req.source_tool_call_ids
                    else None,
                )

            return {
                "created": False,
                "updated": True,
                "document_id": str(existing.id),
                "version_id": str(version.id),
                "store_slug": store.slug,
                "path": write_req.path,
            }

        # Create new document
        doc_data = MemoryDocumentCreate(
            path=write_req.path,
            title=write_req.title,
            content=write_req.content,
            document_type=write_req.document_type,
            status=MemoryDocumentStatus.DRAFT
            if store.scope_type == MemoryScopeType.WORKSPACE
            else MemoryDocumentStatus.ACTIVE,
            tags=write_req.tags,
            entities=write_req.entities,
            confidence=write_req.confidence,
        )

        document = await self.create_document(
            store=store,
            data=doc_data,
            actor_type=MemoryActorType.AGENT,
            actor_agent_run_id=actor_agent_run_id,
            actor_conversation_id=actor_conversation_id,
        )

        if write_req.evidence_summary:
            await repo.create_source_ref(
                document_id=document.id,
                version_id=document.current_version_id,
                evidence_summary=write_req.evidence_summary,
                evidence_kind="tool_result"
                if write_req.source_tool_call_ids
                else "incident_summary",
                conversation_id=actor_conversation_id,
                run_id=actor_agent_run_id,
                tool_call_id=write_req.source_tool_call_ids[0]
                if write_req.source_tool_call_ids
                else None,
            )

        return {
            "created": True,
            "updated": False,
            "document_id": str(document.id),
            "version_id": str(document.current_version_id),
            "store_slug": store.slug,
            "path": write_req.path,
        }

    async def agent_patch(
        self,
        patch_req: MemoryPatchRequest,
        actor_user_id: Optional[UUID] = None,
        actor_agent_run_id: Optional[UUID] = None,
        actor_conversation_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        document = await repo.get_document_by_id(UUID(patch_req.document_id))
        if not document:
            return {"error": True, "message": f"Document {patch_req.document_id} not found"}

        await document.fetch_related("store")

        policy = await _policy.resolve_write(
            user_id=actor_user_id,
            store=document.store,
            document_type=document.document_type,
        )
        if not policy.allowed:
            return {"error": True, "message": f"Policy denied: {policy.reason}"}

        safety = _safety.scan_write(patch_req.new_content, document.store.scope_type)
        if not safety.allowed:
            descriptions = "; ".join(f.description for f in safety.findings)
            return {
                "error": True,
                "blocked": True,
                "severity": safety.severity,
                "message": f"Content blocked by safety scanner: {descriptions}",
            }

        store_slug = document.store.slug
        doc_path = document.path
        doc_type = document.document_type.value

        try:
            updated = await self.patch_document(
                document_id=UUID(patch_req.document_id),
                expected_sha256=patch_req.expected_sha256,
                new_content=patch_req.new_content,
                actor_type=MemoryActorType.AGENT,
                actor_agent_run_id=actor_agent_run_id,
                actor_conversation_id=actor_conversation_id,
            )
        except MemoryWriteError as e:
            if e.is_conflict:
                return {
                    "error": True,
                    "type": "memory_conflict",
                    "message": "Memory changed since it was read. Re-read, merge, and retry.",
                    **e.conflict_data,
                }
            return {"error": True, "message": e.reason}

        if patch_req.evidence_summary:
            await repo.create_source_ref(
                document_id=updated.id,
                version_id=updated.current_version_id,
                evidence_summary=patch_req.evidence_summary,
                evidence_kind="tool_result"
                if patch_req.source_tool_call_ids
                else "incident_summary",
                conversation_id=actor_conversation_id,
                run_id=actor_agent_run_id,
                tool_call_id=patch_req.source_tool_call_ids[0]
                if patch_req.source_tool_call_ids
                else None,
            )

        return {
            "patched": True,
            "document_id": str(updated.id),
            "version_id": str(updated.current_version_id),
            "new_sha256": updated.content_sha256,
            "store_slug": store_slug,
            "path": doc_path,
            "document_type": doc_type,
        }
