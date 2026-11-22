-- Add optional client idempotency keys to evidence submissions.
-- Existing rows remain valid and are not assigned synthetic keys.
ALTER TABLE omnis.evidence
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS evidence_idempotency_key_uq
    ON omnis.evidence (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
