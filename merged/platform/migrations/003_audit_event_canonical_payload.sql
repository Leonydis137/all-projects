-- Preserve the exact JSON representation used to hash each audit event.
-- Apply after 001_evidence_and_audit.sql and 002_ledger_immutability.sql.
-- Nullable for safe rollout over a database that may contain legacy rows;
-- legacy rows without event_json cause verification to fail closed.
ALTER TABLE omnis.audit_event
    ADD COLUMN IF NOT EXISTS event_json TEXT;

COMMENT ON COLUMN omnis.audit_event.event_json IS
    'Exact serialized audit-chain body (excluding event_hash) used for deterministic verification.';
