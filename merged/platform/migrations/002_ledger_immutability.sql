-- OMNIS PostgreSQL ledger hardening.
-- Apply after 001_evidence_and_audit.sql. This migration intentionally grants
-- no application privileges: provision a dedicated role and grant only the
-- operations required by the deployment after reviewing ownership.

REVOKE ALL ON SCHEMA omnis FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA omnis FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA omnis FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA omnis REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA omnis REVOKE ALL ON SEQUENCES FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'evidence_previous_hash_sha256'
          AND conrelid = 'omnis.evidence'::regclass
    ) THEN
        ALTER TABLE omnis.evidence
            ADD CONSTRAINT evidence_previous_hash_sha256
            CHECK (previous_hash ~ '^[0-9a-f]{64}$');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'evidence_record_hash_sha256'
          AND conrelid = 'omnis.evidence'::regclass
    ) THEN
        ALTER TABLE omnis.evidence
            ADD CONSTRAINT evidence_record_hash_sha256
            CHECK (record_hash ~ '^[0-9a-f]{64}$');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'audit_previous_hash_sha256'
          AND conrelid = 'omnis.audit_event'::regclass
    ) THEN
        ALTER TABLE omnis.audit_event
            ADD CONSTRAINT audit_previous_hash_sha256
            CHECK (previous_hash ~ '^[0-9a-f]{64}$');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'audit_event_hash_sha256'
          AND conrelid = 'omnis.audit_event'::regclass
    ) THEN
        ALTER TABLE omnis.audit_event
            ADD CONSTRAINT audit_event_hash_sha256
            CHECK (event_hash ~ '^[0-9a-f]{64}$');
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION omnis.reject_ledger_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'OMNIS ledger tables are append-only'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS evidence_reject_update_delete ON omnis.evidence;
CREATE TRIGGER evidence_reject_update_delete
    BEFORE UPDATE OR DELETE ON omnis.evidence
    FOR EACH ROW EXECUTE FUNCTION omnis.reject_ledger_mutation();

DROP TRIGGER IF EXISTS evidence_reject_truncate ON omnis.evidence;
CREATE TRIGGER evidence_reject_truncate
    BEFORE TRUNCATE ON omnis.evidence
    FOR EACH STATEMENT EXECUTE FUNCTION omnis.reject_ledger_mutation();

DROP TRIGGER IF EXISTS audit_reject_update_delete ON omnis.audit_event;
CREATE TRIGGER audit_reject_update_delete
    BEFORE UPDATE OR DELETE ON omnis.audit_event
    FOR EACH ROW EXECUTE FUNCTION omnis.reject_ledger_mutation();

DROP TRIGGER IF EXISTS audit_reject_truncate ON omnis.audit_event;
CREATE TRIGGER audit_reject_truncate
    BEFORE TRUNCATE ON omnis.audit_event
    FOR EACH STATEMENT EXECUTE FUNCTION omnis.reject_ledger_mutation();

COMMENT ON FUNCTION omnis.reject_ledger_mutation() IS
    'Rejects UPDATE, DELETE and TRUNCATE against OMNIS append-only ledger tables. Database owners/superusers remain privileged.';
COMMENT ON TABLE omnis.evidence IS
    'Append-only evidence metadata ledger. Hash integrity does not establish source authenticity.';
COMMENT ON TABLE omnis.audit_event IS
    'Append-only audit event ledger. Hash integrity does not establish actor identity.';
