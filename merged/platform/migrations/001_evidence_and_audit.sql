-- OMNIS PostgreSQL evidence and audit foundation.
-- Apply explicitly to a configured PostgreSQL database; this file is not auto-run.
CREATE SCHEMA IF NOT EXISTS omnis;

CREATE TABLE IF NOT EXISTS omnis.evidence (
    sequence BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_uri TEXT NOT NULL CHECK (source_uri ~ '^https?://'),
    content_sha256 CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    acquired_at TIMESTAMPTZ NOT NULL,
    acquisition_method TEXT NOT NULL,
    declared_license TEXT NOT NULL,
    submitted_by TEXT NOT NULL,
    previous_hash CHAR(64) NOT NULL,
    record_hash CHAR(64) NOT NULL UNIQUE,
    source_authenticity TEXT NOT NULL DEFAULT 'unverified'
        CHECK (source_authenticity IN ('unverified', 'independently_fetched', 'signature_verified'))
);

CREATE TABLE IF NOT EXISTS omnis.audit_event (
    sequence BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    previous_hash CHAR(64) NOT NULL,
    event_hash CHAR(64) NOT NULL UNIQUE
);

-- Application roles should receive INSERT/SELECT only. Do not grant UPDATE/DELETE.
REVOKE UPDATE, DELETE, TRUNCATE ON omnis.evidence FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON omnis.audit_event FROM PUBLIC;
