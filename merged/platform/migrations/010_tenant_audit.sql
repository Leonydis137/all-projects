-- Tenant-local audit chains. The event index and hash predecessor are per tenant.
CREATE TABLE IF NOT EXISTS omnis.tenant_audit_event (
    tenant_id UUID NOT NULL REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    event_index BIGINT NOT NULL CHECK (event_index >= 0),
    occurred_at TIMESTAMPTZ NOT NULL,
    actor UUID NOT NULL REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 160),
    payload JSONB NOT NULL,
    previous_hash CHAR(64) NOT NULL CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
    event_hash CHAR(64) NOT NULL CHECK (event_hash ~ '^[0-9a-f]{64}$'),
    event_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, event_index),
    UNIQUE (tenant_id, event_hash)
);

CREATE INDEX IF NOT EXISTS tenant_audit_event_tenant_time_idx
    ON omnis.tenant_audit_event (tenant_id, occurred_at DESC);

CREATE OR REPLACE FUNCTION omnis.reject_tenant_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'OMNIS tenant audit is append-only'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS tenant_audit_reject_update_delete ON omnis.tenant_audit_event;
CREATE TRIGGER tenant_audit_reject_update_delete
    BEFORE UPDATE OR DELETE ON omnis.tenant_audit_event
    FOR EACH ROW EXECUTE FUNCTION omnis.reject_tenant_audit_mutation();
DROP TRIGGER IF EXISTS tenant_audit_reject_truncate ON omnis.tenant_audit_event;
CREATE TRIGGER tenant_audit_reject_truncate
    BEFORE TRUNCATE ON omnis.tenant_audit_event
    FOR EACH STATEMENT EXECUTE FUNCTION omnis.reject_tenant_audit_mutation();

ALTER TABLE omnis.tenant_audit_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_audit_event FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_audit_event_scope ON omnis.tenant_audit_event;
CREATE POLICY tenant_audit_event_scope ON omnis.tenant_audit_event
    USING (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid)
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_audit_event.tenant_id
              AND m.principal_id = tenant_audit_event.actor
        )
    );

REVOKE ALL ON omnis.tenant_audit_event FROM PUBLIC;
