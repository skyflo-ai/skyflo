"""Memory retrieval -- full-text search with entity extraction and trust-based ranking."""

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..models.memory import MemoryDocumentType, MemoryTrustLevel, MemoryUsageKind
from . import repository as repo
from .schemas import MemoryHit, MemoryScopeHints, MemorySearchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Trust score mapping
# ---------------------------------------------------------------------------

_TRUST_SCORES: Dict[str, float] = {
    MemoryTrustLevel.ADMIN_APPROVED.value: 1.00,
    MemoryTrustLevel.SYSTEM_SEEDED.value: 0.95,
    MemoryTrustLevel.USER_AUTHORED.value: 0.85,
    MemoryTrustLevel.AGENT_DRAFT.value: 0.45,
}

# ---------------------------------------------------------------------------
# Document type boosts for infra tasks
# ---------------------------------------------------------------------------

_DOCTYPE_BOOST: Dict[str, float] = {
    MemoryDocumentType.RUNBOOK.value: 0.9,
    MemoryDocumentType.VERIFICATION_CHECKLIST.value: 0.85,
    MemoryDocumentType.INCIDENT_LESSON.value: 0.8,
    MemoryDocumentType.WORKSPACE_CONVENTION.value: 0.75,
    MemoryDocumentType.SERVICE_CONTEXT.value: 0.7,
    MemoryDocumentType.TOOL_USAGE_LESSON.value: 0.65,
    MemoryDocumentType.USER_PREFERENCE.value: 0.5,
    MemoryDocumentType.CONVERSATION_NOTE.value: 0.3,
    MemoryDocumentType.DREAM_SUMMARY.value: 0.4,
}

# Recency half-life in seconds (30 days)
_RECENCY_HALF_LIFE_SECONDS = 30 * 24 * 3600

# ---------------------------------------------------------------------------
# Entity extractor
# ---------------------------------------------------------------------------


class MemoryEntityExtractor:
    """Extract structured entities from user messages using deterministic regex."""

    _NS_PATTERN = re.compile(
        r"(?:namespace\s+|ns/|-n\s+)([a-z0-9][a-z0-9\-\.]{0,62})",
        re.IGNORECASE,
    )
    _K8S_RESOURCE_PATTERN = re.compile(
        r"(?:deployment|deploy|pod|svc|service|ingress|statefulset|daemonset|job|cronjob)"
        r"[/\s]+([a-z0-9][a-z0-9\-\.]{0,62})",
        re.IGNORECASE,
    )
    _ENV_PATTERN = re.compile(
        r"\b(dev|development|staging|stage|uat|prod|production|preview)\b",
        re.IGNORECASE,
    )
    _SERVICE_PATTERN = re.compile(
        r"(?:service|app|application|component)\s+([a-z0-9][a-z0-9\-_\.]{1,62})",
        re.IGNORECASE,
    )

    def extract(self, text: str) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {
            "namespaces": [],
            "resources": [],
            "environments": [],
            "services": [],
        }

        for match in self._NS_PATTERN.finditer(text):
            val = match.group(1).lower()
            if val not in entities["namespaces"]:
                entities["namespaces"].append(val)

        for match in self._K8S_RESOURCE_PATTERN.finditer(text):
            val = match.group(1).lower()
            if val not in entities["resources"]:
                entities["resources"].append(val)

        for match in self._ENV_PATTERN.finditer(text):
            val = match.group(1).lower()
            if val not in entities["environments"]:
                entities["environments"].append(val)

        for match in self._SERVICE_PATTERN.finditer(text):
            val = match.group(1).lower()
            if val not in entities["services"]:
                entities["services"].append(val)

        return entities


_extractor = MemoryEntityExtractor()


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _recency_score(updated_at: Optional[Any]) -> float:
    """Exponential decay with 30-day half-life."""
    if not updated_at:
        return 0.3
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError:
            return 0.3

    now = datetime.now(timezone.utc)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    age_seconds = (now - updated_at).total_seconds()
    if age_seconds < 0:
        return 1.0
    return math.exp(-math.log(2) * age_seconds / _RECENCY_HALF_LIFE_SECONDS)


def _entity_match_score(row_entities: Any, query_entities: Dict[str, List[str]]) -> float:
    """Score 0-1 based on how many query entities match document entity tags."""
    if not query_entities or not row_entities:
        return 0.0
    if isinstance(row_entities, str):
        import json

        try:
            row_entities = json.loads(row_entities)
        except Exception:
            return 0.0

    all_doc_vals: List[str] = []
    for vals in row_entities.values() if isinstance(row_entities, dict) else []:
        if isinstance(vals, list):
            all_doc_vals.extend([str(v).lower() for v in vals])
        elif vals:
            all_doc_vals.append(str(vals).lower())

    matches = 0
    total_query_entities = 0
    for entity_list in query_entities.values():
        for val in entity_list:
            total_query_entities += 1
            if val.lower() in all_doc_vals:
                matches += 1

    if total_query_entities == 0:
        return 0.0
    return min(1.0, matches / total_query_entities)


def _rank_row(
    row: Dict[str, Any],
    query_entities: Dict[str, List[str]],
) -> float:
    text_score = float(row.get("text_score") or 0.0)
    trust_level = str(row.get("trust_level") or "agent_draft")
    trust_score = _TRUST_SCORES.get(trust_level, 0.3)
    doc_type = str(row.get("document_type") or "conversation_note")
    doc_type_boost = _DOCTYPE_BOOST.get(doc_type, 0.3)
    entity_score = _entity_match_score(row.get("entities"), query_entities)
    recency = _recency_score(row.get("updated_at"))

    return (
        0.45 * min(1.0, text_score)
        + 0.20 * trust_score
        + 0.15 * entity_score
        + 0.10 * doc_type_boost
        + 0.10 * recency
    )


def _make_excerpt(content: str, max_chars: int = 1200) -> str:
    if not content:
        return ""
    content = content.strip()
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rsplit(" ", 1)[0] + " ..."


# ---------------------------------------------------------------------------
# Retrieval service
# ---------------------------------------------------------------------------


class MemoryRetrievalService:
    async def get_accessible_store_ids(
        self,
        user_id: Optional[UUID],
        scope_hints: Optional[MemoryScopeHints],
        conversation_id: Optional[str],
    ) -> List[UUID]:
        stores = await repo.list_stores(
            owner_user_id=user_id,
            include_archived=False,
        )
        accessible: List[UUID] = []
        for store in stores:
            from ..models.memory import MemoryScopeType

            if store.scope_type == MemoryScopeType.WORKSPACE:
                accessible.append(store.id)
            elif store.scope_type == MemoryScopeType.USER:
                if user_id and (store.owner_user_id is None or store.owner_user_id == user_id):
                    accessible.append(store.id)
            elif store.scope_type == MemoryScopeType.CONVERSATION:
                if user_id is not None:
                    accessible.append(store.id)
        return accessible

    async def search(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        scope_hints: Optional[MemoryScopeHints] = None,
        conversation_id: Optional[str] = None,
        max_results: int = 6,
        include_drafts: bool = False,
        document_types: Optional[List[MemoryDocumentType]] = None,
    ) -> List[MemorySearchResult]:
        store_ids = await self.get_accessible_store_ids(user_id, scope_hints, conversation_id)
        if not store_ids:
            return []

        rows = await repo.fts_search(
            query=query,
            store_ids=store_ids,
            max_results=max_results * 3,  # over-fetch for re-ranking
            include_drafts=include_drafts,
            document_types=document_types,
        )

        if not rows:
            return []

        query_entities = _extractor.extract(query)

        scored = [(r, _rank_row(r, query_entities)) for r in rows]
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)

        results: List[MemorySearchResult] = []
        for row, score in ranked[:max_results]:
            results.append(
                MemorySearchResult(
                    store_slug=str(row.get("store_slug") or ""),
                    path=str(row.get("path") or ""),
                    document_id=UUID(str(row["id"])),
                    version_id=UUID(str(row["current_version_id"]))
                    if row.get("current_version_id")
                    else None,
                    trust_level=MemoryTrustLevel(str(row.get("trust_level") or "agent_draft")),
                    document_type=MemoryDocumentType(
                        str(row.get("document_type") or "conversation_note")
                    ),
                    status=row.get("status") or "active",
                    score=round(score, 4),
                    updated_at=row.get("updated_at") or datetime.now(timezone.utc),
                    excerpt=_make_excerpt(str(row.get("content") or "")),
                    title=row.get("title"),
                )
            )

        return results

    async def retrieve_for_turn(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        conversation_id: Optional[str] = None,
        run_id: Optional[str] = None,
        max_docs: int = 6,
        token_budget: int = 2200,
    ) -> List[MemoryHit]:
        """
        Retrieve memory documents for injection into the model context.
        Respects token budget by truncating excerpts.
        """
        scope_hints = MemoryScopeHints(workspace=True, user=True, conversation_id=conversation_id)
        results = await self.search(
            query=query,
            user_id=user_id,
            scope_hints=scope_hints,
            conversation_id=conversation_id,
            max_results=max_docs,
            include_drafts=False,
        )

        hits: List[MemoryHit] = []
        total_chars = 0
        char_budget = token_budget * 4  # rough approximation: 1 token ~ 4 chars

        for result in results:
            excerpt = result.excerpt
            remaining = char_budget - total_chars
            if remaining <= 0:
                break
            if len(excerpt) > remaining:
                excerpt = excerpt[:remaining].rsplit(" ", 1)[0] + " ..."

            hit = MemoryHit(
                document_id=str(result.document_id),
                version_id=str(result.version_id) if result.version_id else None,
                store_slug=result.store_slug,
                path=result.path,
                trust_level=result.trust_level,
                document_type=result.document_type,
                excerpt=excerpt,
                title=result.title,
                updated_at=result.updated_at,
                score=result.score,
            )
            hits.append(hit)
            total_chars += len(excerpt) + 200  # 200 chars for metadata overhead

        if hits and conversation_id and run_id:
            try:
                await repo.record_memory_usage_bulk(
                    conversation_id=UUID(conversation_id),
                    run_id=UUID(run_id),
                    entries=[
                        {
                            "document_id": UUID(hit.document_id),
                            "version_id": UUID(hit.version_id) if hit.version_id else None,
                            "usage_kind": MemoryUsageKind.INJECTED,
                        }
                        for hit in hits
                    ],
                )
            except Exception as e:
                logger.debug(f"Failed to record memory usage: {e}")

        return hits
