from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "memory_stores" (
            "id" UUID NOT NULL PRIMARY KEY,
            "name" VARCHAR(160) NOT NULL,
            "slug" VARCHAR(160) NOT NULL UNIQUE,
            "description" TEXT NOT NULL DEFAULT '',
            "scope_type" VARCHAR(40) NOT NULL,
            "trust_level" VARCHAR(40) NOT NULL,
            "default_access" VARCHAR(40) NOT NULL,
            "owner_user_id" UUID,
            "archived_at" TIMESTAMPTZ,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_memory_stores_slug" ON "memory_stores" ("slug");
        CREATE INDEX IF NOT EXISTS "idx_memory_stores_owner" ON "memory_stores" ("owner_user_id");

        CREATE TABLE IF NOT EXISTS "memory_documents" (
            "id" UUID NOT NULL PRIMARY KEY,
            "store_id" UUID NOT NULL REFERENCES "memory_stores" ("id") ON DELETE CASCADE,
            "path" VARCHAR(512) NOT NULL,
            "title" VARCHAR(240),
            "content" TEXT NOT NULL,
            "content_sha256" VARCHAR(64) NOT NULL,
            "content_size_bytes" INT NOT NULL DEFAULT 0,
            "document_type" VARCHAR(60) NOT NULL,
            "status" VARCHAR(40) NOT NULL DEFAULT 'active',
            "tags" JSONB NOT NULL DEFAULT '[]',
            "entities" JSONB NOT NULL DEFAULT '{}',
            "confidence" INT NOT NULL DEFAULT 100,
            "current_version_id" UUID,
            "created_by_user_id" UUID,
            "created_by_agent_run_id" UUID,
            "created_by_conversation_id" UUID,
            "deleted_at" TIMESTAMPTZ,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_memory_documents_sha256" ON "memory_documents" ("content_sha256");
        CREATE INDEX IF NOT EXISTS "idx_memory_documents_store_status" ON "memory_documents" ("store_id", "status");
        CREATE INDEX IF NOT EXISTS "idx_memory_documents_doc_type" ON "memory_documents" ("document_type");
        CREATE INDEX IF NOT EXISTS "idx_memory_documents_entities" ON "memory_documents" USING GIN ("entities");
        CREATE INDEX IF NOT EXISTS "idx_memory_documents_tags" ON "memory_documents" USING GIN ("tags");
        CREATE UNIQUE INDEX IF NOT EXISTS "uq_memory_documents_store_path_live"
            ON "memory_documents" ("store_id", "path")
            WHERE "deleted_at" IS NULL;

        ALTER TABLE "memory_documents"
            ADD COLUMN IF NOT EXISTS "search_vector" tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce("title", '')), 'A') ||
                setweight(to_tsvector('english', coalesce("content", '')), 'B')
            ) STORED;
        CREATE INDEX IF NOT EXISTS "idx_memory_documents_search_vector"
            ON "memory_documents" USING GIN ("search_vector");

        CREATE TABLE IF NOT EXISTS "memory_versions" (
            "id" UUID NOT NULL PRIMARY KEY,
            "store_id" UUID NOT NULL REFERENCES "memory_stores" ("id") ON DELETE CASCADE,
            "document_id" UUID REFERENCES "memory_documents" ("id") ON DELETE SET NULL,
            "path" VARCHAR(512) NOT NULL,
            "operation" VARCHAR(40) NOT NULL,
            "content" TEXT,
            "content_sha256" VARCHAR(64),
            "content_size_bytes" INT,
            "previous_version_id" UUID,
            "actor_type" VARCHAR(40) NOT NULL,
            "actor_user_id" UUID,
            "actor_agent_run_id" UUID,
            "actor_conversation_id" UUID,
            "actor_dream_id" UUID,
            "redacted_at" TIMESTAMPTZ,
            "redacted_by_user_id" UUID,
            "redaction_reason" TEXT,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_memory_versions_document" ON "memory_versions" ("document_id");
        CREATE INDEX IF NOT EXISTS "idx_memory_versions_store" ON "memory_versions" ("store_id");

        CREATE TABLE IF NOT EXISTS "memory_source_refs" (
            "id" UUID NOT NULL PRIMARY KEY,
            "document_id" UUID NOT NULL REFERENCES "memory_documents" ("id") ON DELETE CASCADE,
            "version_id" UUID REFERENCES "memory_versions" ("id") ON DELETE SET NULL,
            "conversation_id" UUID,
            "run_id" UUID,
            "tool_call_id" VARCHAR(160),
            "tool_name" VARCHAR(160),
            "tool_args_hash" VARCHAR(64),
            "tool_result_hash" VARCHAR(64),
            "evidence_summary" TEXT NOT NULL,
            "evidence_kind" VARCHAR(60) NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_memory_source_refs_document" ON "memory_source_refs" ("document_id");

        -- conversation_id and run_id are intentionally unkeyed for audit preservation:
        -- usage history must survive conversation deletion.
        -- document_id uses CASCADE so orphaned usage rows are cleaned up with the document.
        CREATE TABLE IF NOT EXISTS "conversation_memory_usage" (
            "id" UUID NOT NULL PRIMARY KEY,
            "conversation_id" UUID NOT NULL,
            "run_id" UUID NOT NULL,
            "document_id" UUID NOT NULL REFERENCES "memory_documents" ("id") ON DELETE CASCADE,
            "version_id" UUID REFERENCES "memory_versions" ("id") ON DELETE SET NULL,
            "usage_kind" VARCHAR(40) NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_conv_memory_usage_conversation" ON "conversation_memory_usage" ("conversation_id");
        CREATE INDEX IF NOT EXISTS "idx_conv_memory_usage_run" ON "conversation_memory_usage" ("run_id");

        CREATE TABLE IF NOT EXISTS "dream_jobs" (
            "id" UUID NOT NULL PRIMARY KEY,
            "workspace_id" UUID,
            "dream_type" VARCHAR(60) NOT NULL,
            "status" VARCHAR(40) NOT NULL DEFAULT 'pending',
            "input_store_ids" JSONB NOT NULL DEFAULT '[]',
            "input_conversation_ids" JSONB NOT NULL DEFAULT '[]',
            "input_run_ids" JSONB NOT NULL DEFAULT '[]',
            "output_store_id" UUID,
            "model" VARCHAR(160) NOT NULL,
            "instructions" TEXT,
            "usage_json" JSONB NOT NULL DEFAULT '{}',
            "error" TEXT,
            "created_by_user_id" UUID,
            "started_at" TIMESTAMPTZ,
            "ended_at" TIMESTAMPTZ,
            "canceled_at" TIMESTAMPTZ,
            "archived_at" TIMESTAMPTZ,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_dream_jobs_status" ON "dream_jobs" ("status");
        CREATE INDEX IF NOT EXISTS "idx_dream_jobs_workspace" ON "dream_jobs" ("workspace_id");

        CREATE TABLE IF NOT EXISTS "dream_review_items" (
            "id" UUID NOT NULL PRIMARY KEY,
            "dream_id" UUID NOT NULL REFERENCES "dream_jobs" ("id") ON DELETE CASCADE,
            "source_document_id" UUID,
            "candidate_document_id" UUID,
            "target_store_id" UUID,
            "target_path" VARCHAR(512) NOT NULL,
            "action" VARCHAR(40) NOT NULL,
            "status" VARCHAR(40) NOT NULL DEFAULT 'pending',
            "diff_json" JSONB NOT NULL DEFAULT '{}',
            "rationale" TEXT NOT NULL,
            "risk_level" VARCHAR(20) NOT NULL DEFAULT 'low',
            "reviewed_by_user_id" UUID,
            "reviewed_at" TIMESTAMPTZ,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_dream_review_items_dream" ON "dream_review_items" ("dream_id");
        CREATE INDEX IF NOT EXISTS "idx_dream_review_items_status" ON "dream_review_items" ("status");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "dream_review_items";
        DROP TABLE IF EXISTS "dream_jobs";
        DROP TABLE IF EXISTS "conversation_memory_usage";
        DROP TABLE IF EXISTS "memory_source_refs";
        DROP TABLE IF EXISTS "memory_versions";
        DROP TABLE IF EXISTS "memory_documents";
        DROP TABLE IF EXISTS "memory_stores";
    """
