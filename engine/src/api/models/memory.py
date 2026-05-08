"""Memory system ORM models."""

import uuid
from enum import Enum

from tortoise import fields
from tortoise.models import Model


class MemoryScopeType(str, Enum):
    WORKSPACE = "workspace"
    USER = "user"
    CONVERSATION = "conversation"


class MemoryTrustLevel(str, Enum):
    SYSTEM_SEEDED = "system_seeded"
    ADMIN_APPROVED = "admin_approved"
    USER_AUTHORED = "user_authored"
    AGENT_DRAFT = "agent_draft"


class MemoryAccessMode(str, Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    DRAFT_WRITE = "draft_write"


class MemoryDocumentType(str, Enum):
    USER_PREFERENCE = "user_preference"
    WORKSPACE_CONVENTION = "workspace_convention"
    RUNBOOK = "runbook"
    INCIDENT_LESSON = "incident_lesson"
    SERVICE_CONTEXT = "service_context"
    TOOL_USAGE_LESSON = "tool_usage_lesson"
    VERIFICATION_CHECKLIST = "verification_checklist"
    CONVERSATION_NOTE = "conversation_note"
    DREAM_SUMMARY = "dream_summary"


class MemoryDocumentStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    CANDIDATE = "candidate"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    REDACTED = "redacted"


class MemoryOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    PATCH = "patch"
    DELETE = "delete"
    REDACT = "redact"
    PROMOTE = "promote"


class MemoryActorType(str, Enum):
    USER = "user"
    ADMIN = "admin"
    AGENT = "agent"
    SYSTEM = "system"
    DREAM = "dream"


class MemoryEvidenceKind(str, Enum):
    USER_STATEMENT = "user_statement"
    TOOL_RESULT = "tool_result"
    APPROVED_MUTATION = "approved_mutation"
    VERIFICATION_RESULT = "verification_result"
    INCIDENT_SUMMARY = "incident_summary"
    ADMIN_ENTRY = "admin_entry"
    DREAM_INFERENCE = "dream_inference"


class MemoryRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MemoryUsageKind(str, Enum):
    INJECTED = "injected"
    READ = "read"
    WRITTEN = "written"
    PROPOSED = "proposed"


class DreamType(str, Enum):
    SESSION_REFLECTION = "session_reflection"
    INCIDENT_REFLECTION = "incident_reflection"
    STORE_COMPACTION = "store_compaction"
    RUNBOOK_PROMOTION = "runbook_promotion"
    USER_MEMORY_CLEANUP = "user_memory_cleanup"


class DreamStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class DreamReviewAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    ARCHIVE = "archive"
    MERGE = "merge"
    PROMOTE = "promote"
    REJECT_EXISTING = "reject_existing"


class DreamReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    SUPERSEDED = "superseded"


class MemoryStore(Model):
    """Scoped container that groups memory documents by ownership and trust level."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(max_length=160)
    slug = fields.CharField(max_length=160, unique=True, index=True)
    description = fields.TextField(default="")
    scope_type = fields.CharEnumField(MemoryScopeType, max_length=40)
    trust_level = fields.CharEnumField(MemoryTrustLevel, max_length=40)
    default_access = fields.CharEnumField(MemoryAccessMode, max_length=40)
    owner_user_id = fields.UUIDField(null=True, index=True)
    archived_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    documents: fields.ReverseRelation["MemoryDocument"]
    versions: fields.ReverseRelation["MemoryVersion"]

    class Meta:
        table = "memory_stores"

    def __str__(self) -> str:
        return f"<MemoryStore {self.slug}>"


class MemoryDocument(Model):
    """A single knowledge unit inside a memory store."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    store = fields.ForeignKeyField("models.MemoryStore", related_name="documents")
    path = fields.CharField(max_length=512)
    title = fields.CharField(max_length=240, null=True)
    content = fields.TextField()
    content_sha256 = fields.CharField(max_length=64, index=True)
    content_size_bytes = fields.IntField(default=0)
    document_type = fields.CharEnumField(MemoryDocumentType, max_length=60)
    status = fields.CharEnumField(
        MemoryDocumentStatus, max_length=40, default=MemoryDocumentStatus.ACTIVE
    )
    tags = fields.JSONField(default=list)
    entities = fields.JSONField(default=dict)
    confidence = fields.IntField(default=100)
    current_version_id = fields.UUIDField(null=True)
    created_by_user_id = fields.UUIDField(null=True)
    created_by_agent_run_id = fields.UUIDField(null=True)
    created_by_conversation_id = fields.UUIDField(null=True)
    deleted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    versions: fields.ReverseRelation["MemoryVersion"]
    source_refs: fields.ReverseRelation["MemorySourceRef"]

    class Meta:
        table = "memory_documents"

    def __str__(self) -> str:
        return f"<MemoryDocument {self.path}>"


class MemoryVersion(Model):
    """Immutable write-ahead log entry for every memory document mutation."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    store = fields.ForeignKeyField("models.MemoryStore", related_name="versions")
    document = fields.ForeignKeyField("models.MemoryDocument", related_name="versions", null=True)
    path = fields.CharField(max_length=512)
    operation = fields.CharEnumField(MemoryOperation, max_length=40)
    content = fields.TextField(null=True)
    content_sha256 = fields.CharField(max_length=64, null=True)
    content_size_bytes = fields.IntField(null=True)
    previous_version_id = fields.UUIDField(null=True)
    actor_type = fields.CharEnumField(MemoryActorType, max_length=40)
    actor_user_id = fields.UUIDField(null=True)
    actor_agent_run_id = fields.UUIDField(null=True)
    actor_conversation_id = fields.UUIDField(null=True)
    actor_dream_id = fields.UUIDField(null=True)
    redacted_at = fields.DatetimeField(null=True)
    redacted_by_user_id = fields.UUIDField(null=True)
    redaction_reason = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    source_refs: fields.ReverseRelation["MemorySourceRef"]

    class Meta:
        table = "memory_versions"

    def __str__(self) -> str:
        return f"<MemoryVersion {self.id} op={self.operation}>"


class MemorySourceRef(Model):
    """Evidence provenance for a memory document or version."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    document = fields.ForeignKeyField("models.MemoryDocument", related_name="source_refs")
    version = fields.ForeignKeyField("models.MemoryVersion", related_name="source_refs", null=True)
    conversation_id = fields.UUIDField(null=True)
    run_id = fields.UUIDField(null=True)
    tool_call_id = fields.CharField(max_length=160, null=True)
    tool_name = fields.CharField(max_length=160, null=True)
    tool_args_hash = fields.CharField(max_length=64, null=True)
    tool_result_hash = fields.CharField(max_length=64, null=True)
    evidence_summary = fields.TextField()
    evidence_kind = fields.CharEnumField(MemoryEvidenceKind, max_length=60)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "memory_source_refs"

    def __str__(self) -> str:
        return f"<MemorySourceRef {self.id} kind={self.evidence_kind}>"


class ConversationMemoryUsage(Model):
    """Audit record of which memory documents were used in a given run."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    conversation_id = fields.UUIDField(index=True)
    run_id = fields.UUIDField(index=True)
    document_id = fields.UUIDField()
    version_id = fields.UUIDField(null=True)
    usage_kind = fields.CharEnumField(MemoryUsageKind, max_length=40)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "conversation_memory_usage"

    def __str__(self) -> str:
        return f"<ConversationMemoryUsage run={self.run_id} doc={self.document_id}>"


class DreamJob(Model):
    """Async reflection job that reads memory and produces candidate output stores."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    workspace_id = fields.UUIDField(null=True, index=True)
    dream_type = fields.CharEnumField(DreamType, max_length=60)
    status = fields.CharEnumField(DreamStatus, max_length=40, default=DreamStatus.PENDING)
    input_store_ids = fields.JSONField(default=list)
    input_conversation_ids = fields.JSONField(default=list)
    input_run_ids = fields.JSONField(default=list)
    output_store_id = fields.UUIDField(null=True)
    model = fields.CharField(max_length=160)
    instructions = fields.TextField(null=True)
    usage_json = fields.JSONField(default=dict)
    error = fields.TextField(null=True)
    created_by_user_id = fields.UUIDField(null=True)
    started_at = fields.DatetimeField(null=True)
    ended_at = fields.DatetimeField(null=True)
    canceled_at = fields.DatetimeField(null=True)
    archived_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    review_items: fields.ReverseRelation["DreamReviewItem"]

    class Meta:
        table = "dream_jobs"

    def __str__(self) -> str:
        return f"<DreamJob {self.id} type={self.dream_type} status={self.status}>"


class DreamReviewItem(Model):
    """A single reviewable candidate change produced by a dream job."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    dream = fields.ForeignKeyField("models.DreamJob", related_name="review_items")
    source_document_id = fields.UUIDField(null=True)
    candidate_document_id = fields.UUIDField(null=True)
    target_store_id = fields.UUIDField(null=True)
    target_path = fields.CharField(max_length=512)
    action = fields.CharEnumField(DreamReviewAction, max_length=40)
    status = fields.CharEnumField(
        DreamReviewStatus, max_length=40, default=DreamReviewStatus.PENDING
    )
    diff_json = fields.JSONField(default=dict)
    rationale = fields.TextField()
    risk_level = fields.CharEnumField(MemoryRiskLevel, max_length=20, default=MemoryRiskLevel.LOW)
    reviewed_by_user_id = fields.UUIDField(null=True)
    reviewed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dream_review_items"

    def __str__(self) -> str:
        return f"<DreamReviewItem {self.id} action={self.action} status={self.status}>"
