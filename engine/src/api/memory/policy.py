"""Memory access policy engine."""

import logging
from typing import Optional
from uuid import UUID

from ..models.memory import (
    MemoryAccessMode,
    MemoryDocumentType,
    MemoryOperation,
    MemoryScopeType,
    MemoryStore,
)
from .schemas import MemoryPolicyDecision

logger = logging.getLogger(__name__)

# Slugs that are workspace-level and never directly writable by the agent
_WORKSPACE_READ_ONLY_SLUGS = frozenset({"workspace_conventions", "workspace_runbooks"})


class MemoryPolicyService:
    async def resolve_read(
        self,
        user_id: Optional[UUID],
        store: MemoryStore,
    ) -> MemoryPolicyDecision:
        """Determine whether a user/agent can read documents in this store."""
        if store.archived_at is not None:
            return MemoryPolicyDecision(
                allowed=False,
                reason="Store is archived",
                effective_access=MemoryAccessMode.READ_ONLY,
            )

        if store.scope_type == MemoryScopeType.WORKSPACE:
            if user_id is None:
                # Unauthenticated: allow workspace_conventions only
                allowed = store.slug == "workspace_conventions"
                return MemoryPolicyDecision(
                    allowed=allowed,
                    reason="Unauthenticated access"
                    if not allowed
                    else "Public workspace convention",
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            return MemoryPolicyDecision(
                allowed=True,
                reason="Authenticated user can read workspace stores",
                effective_access=MemoryAccessMode.READ_ONLY,
            )

        if store.scope_type == MemoryScopeType.USER:
            if user_id is None:
                return MemoryPolicyDecision(
                    allowed=False,
                    reason="Unauthenticated cannot read user memory",
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            if store.owner_user_id is not None and store.owner_user_id != user_id:
                return MemoryPolicyDecision(
                    allowed=False,
                    reason="Cannot read another user's memory",
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            return MemoryPolicyDecision(
                allowed=True,
                reason="User owns this store",
                effective_access=MemoryAccessMode.READ_WRITE,
            )

        if store.scope_type == MemoryScopeType.CONVERSATION:
            if user_id is None:
                return MemoryPolicyDecision(
                    allowed=False,
                    reason="Unauthenticated cannot access conversation memory",
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            return MemoryPolicyDecision(
                allowed=True,
                reason="Authenticated user can read conversation memory",
                effective_access=MemoryAccessMode.READ_WRITE,
            )

        return MemoryPolicyDecision(
            allowed=False,
            reason=f"Unknown scope type: {store.scope_type}",
            effective_access=MemoryAccessMode.READ_ONLY,
        )

    async def resolve_write(
        self,
        user_id: Optional[UUID],
        store: MemoryStore,
        document_type: Optional[MemoryDocumentType] = None,
        operation: MemoryOperation = MemoryOperation.CREATE,
    ) -> MemoryPolicyDecision:
        """Determine whether the agent can write to this store/document combination."""
        if store.archived_at is not None:
            return MemoryPolicyDecision(
                allowed=False,
                reason="Store is archived",
                effective_access=MemoryAccessMode.READ_ONLY,
            )

        # Workspace stores: never writable directly by the agent
        if store.slug in _WORKSPACE_READ_ONLY_SLUGS:
            return MemoryPolicyDecision(
                allowed=False,
                reason=f"Store '{store.slug}' is read-only. Use memory_propose_promotion to suggest changes.",
                effective_access=MemoryAccessMode.READ_ONLY,
            )

        if store.scope_type == MemoryScopeType.WORKSPACE:
            return MemoryPolicyDecision(
                allowed=False,
                reason="Workspace stores require admin write access",
                effective_access=MemoryAccessMode.READ_ONLY,
            )

        if store.scope_type == MemoryScopeType.CONVERSATION:
            if user_id is None:
                return MemoryPolicyDecision(
                    allowed=False,
                    reason="Unauthenticated cannot write conversation memory",
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            return MemoryPolicyDecision(
                allowed=True,
                reason="Agent can write conversation memory",
                effective_access=MemoryAccessMode.READ_WRITE,
            )

        if store.scope_type == MemoryScopeType.USER:
            if user_id is None:
                return MemoryPolicyDecision(
                    allowed=False,
                    reason="Unauthenticated cannot write user memory",
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            if store.owner_user_id is not None and store.owner_user_id != user_id:
                return MemoryPolicyDecision(
                    allowed=False,
                    reason="Cannot write to another user's memory store",
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            # Agent can only write user_preference type to user stores; caller must supply type
            if document_type is None or document_type != MemoryDocumentType.USER_PREFERENCE:
                return MemoryPolicyDecision(
                    allowed=False,
                    reason=(
                        "Agent can only write user_preference to user_memory; "
                        f"got {document_type.value if document_type else 'None'}"
                    ),
                    effective_access=MemoryAccessMode.READ_ONLY,
                )
            return MemoryPolicyDecision(
                allowed=True,
                reason="Agent can write user preferences",
                effective_access=MemoryAccessMode.READ_WRITE,
            )

        return MemoryPolicyDecision(
            allowed=False,
            reason=f"Write not permitted for scope: {store.scope_type}",
            effective_access=MemoryAccessMode.READ_ONLY,
        )

    async def resolve_admin_write(self, is_admin: bool, store: MemoryStore) -> MemoryPolicyDecision:
        """Determine whether an admin API user can write to this store."""
        if not is_admin:
            return MemoryPolicyDecision(
                allowed=False,
                reason="Admin role required for direct store write",
                effective_access=MemoryAccessMode.READ_ONLY,
            )
        return MemoryPolicyDecision(
            allowed=True,
            reason="Admin write permitted",
            effective_access=MemoryAccessMode.READ_WRITE,
        )

    def can_delete(self, is_admin: bool) -> MemoryPolicyDecision:
        if is_admin:
            return MemoryPolicyDecision(
                allowed=True,
                reason="Admin can delete",
                effective_access=MemoryAccessMode.READ_WRITE,
            )
        return MemoryPolicyDecision(
            allowed=False,
            reason="Only admins can delete memory documents",
            effective_access=MemoryAccessMode.READ_ONLY,
        )

    def can_redact(self, is_admin: bool) -> MemoryPolicyDecision:
        if is_admin:
            return MemoryPolicyDecision(
                allowed=True,
                reason="Admin can redact versions",
                effective_access=MemoryAccessMode.READ_WRITE,
            )
        return MemoryPolicyDecision(
            allowed=False,
            reason="Only admins can redact memory versions",
            effective_access=MemoryAccessMode.READ_ONLY,
        )
