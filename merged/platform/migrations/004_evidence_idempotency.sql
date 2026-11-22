-- Add optional client idempotency keys to evidence submissions.
-- Existing rows remain valid and are not assigned synthetic keys.
ALTER TABLE omnis.evidence
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- CONCURRENTLY avoids blocking ordinary evidence writes while the index is built.
-- This migration intentionally runs outside a transaction because PostgreSQL
-- does not permit CREATE INDEX CONCURRENTLY inside a transaction block.
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS evidence_idempotency_key_uq
    ON omnis.evidence (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
