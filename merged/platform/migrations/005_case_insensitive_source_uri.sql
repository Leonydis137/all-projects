-- Replace the original case-sensitive URI constraint for existing databases.
ALTER TABLE omnis.evidence
    DROP CONSTRAINT IF EXISTS evidence_source_uri_check;

ALTER TABLE omnis.evidence
    DROP CONSTRAINT IF EXISTS evidence_source_uri_http_check;

ALTER TABLE omnis.evidence
    ADD CONSTRAINT evidence_source_uri_http_check
    CHECK (source_uri ~* '^https?://');
