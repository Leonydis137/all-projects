-- Tenant-scoped evidence ledger with database-enforced row isolation.
CREATE TABLE IF NOT EXISTS omnis.tenant_evidence (
    sequence BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    source_uri TEXT NOT NULL CHECK (source_uri ~* '^https?://'),
    content_sha256 CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    acquired_at TIMESTAMPTZ NOT NULL,
    acquisition_method TEXT NOT NULL,
    declared_license TEXT NOT NULL,
    submitted_by TEXT NOT NULL,
    record_json JSONB NOT NULL,
    previous_hash CHAR(64) NOT NULL CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
    record_hash CHAR(64) NOT NULL CHECK (record_hash ~ '^[0-9a-f]{64}$'),
    idempotency_key TEXT,
    UNIQUE (tenant_id, record_hash)
);

CREATE UNIQUE INDEX IF NOT EXISTS tenant_evidence_idempotency_uq
    ON omnis.tenant_evidence (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS tenant_evidence_tenant_sequence_idx
    ON omnis.tenant_evidence (tenant_id, sequence DESC);

CREATE OR REPLACE FUNCTION omnis.reject_tenant_evidence_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'OMNIS tenant evidence is append-only'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS tenant_evidence_reject_update_delete ON omnis.tenant_evidence;
CREATE TRIGGER tenant_evidence_reject_update_delete
    BEFORE UPDATE OR DELETE ON omnis.tenant_evidence
    FOR EACH ROW EXECUTE FUNCTION omnis.reject_tenant_evidence_mutation();
DROP TRIGGER IF EXISTS tenant_evidence_reject_truncate ON omnis.tenant_evidence;
CREATE TRIGGER tenant_evidence_reject_truncate
    BEFORE TRUNCATE ON omnis.tenant_evidence
    FOR EACH STATEMENT EXECUTE FUNCTION omnis.reject_tenant_evidence_mutation();

ALTER TABLE omnis.tenant_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_evidence FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_evidence_tenant_isolation ON omnis.tenant_evidence;
CREATE POLICY tenant_evidence_tenant_isolation ON omnis.tenant_evidence
    USING (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid);

REVOKE ALL ON omnis.tenant_evidence FROM PUBLIC;
