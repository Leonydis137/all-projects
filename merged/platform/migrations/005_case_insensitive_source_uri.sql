-- Replace the original case-sensitive URI constraint atomically.
-- NOT VALID keeps initial constraint installation short; VALIDATE performs
-- the table scan with a lock mode that permits ordinary INSERT/UPDATE/DELETE.
BEGIN;
ALTER TABLE omnis.evidence
    DROP CONSTRAINT IF EXISTS evidence_source_uri_check;

ALTER TABLE omnis.evidence
    DROP CONSTRAINT IF EXISTS evidence_source_uri_http_check;

ALTER TABLE omnis.evidence
    ADD CONSTRAINT evidence_source_uri_http_check
    CHECK (source_uri ~* '^https?://') NOT VALID;

ALTER TABLE omnis.evidence
    VALIDATE CONSTRAINT evidence_source_uri_http_check;
COMMIT;
