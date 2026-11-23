-- Durable tenant usage metering, rolling-minute rate limits, and configurable monthly quotas.
CREATE TABLE IF NOT EXISTS omnis.tenant_usage_policy (
    tenant_id UUID PRIMARY KEY REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    monthly_request_limit BIGINT CHECK (monthly_request_limit IS NULL OR monthly_request_limit >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by UUID REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS omnis.tenant_usage_minute (
    tenant_id UUID NOT NULL REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    window_start TIMESTAMPTZ NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0 CHECK (request_count >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, window_start)
);

CREATE TABLE IF NOT EXISTS omnis.tenant_usage_event (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    principal_id UUID NOT NULL REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    operation TEXT NOT NULL CHECK (length(operation) BETWEEN 1 AND 120),
    units INTEGER NOT NULL DEFAULT 1 CHECK (units > 0),
    outcome TEXT NOT NULL CHECK (outcome IN ('accepted', 'rate_limited', 'quota_exceeded')),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tenant_usage_event_period_idx
    ON omnis.tenant_usage_event (tenant_id, occurred_at DESC, outcome);
CREATE INDEX IF NOT EXISTS tenant_usage_event_principal_idx
    ON omnis.tenant_usage_event (tenant_id, principal_id, occurred_at DESC);

ALTER TABLE omnis.tenant_usage_policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_usage_policy FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_usage_policy_scope ON omnis.tenant_usage_policy;
CREATE POLICY tenant_usage_policy_scope ON omnis.tenant_usage_policy
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND updated_by = nullif(current_setting('omnis.principal_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_usage_policy.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_usage_policy.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
    );

ALTER TABLE omnis.tenant_usage_minute ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_usage_minute FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_usage_minute_scope ON omnis.tenant_usage_minute;
CREATE POLICY tenant_usage_minute_scope ON omnis.tenant_usage_minute
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_usage_minute.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_usage_minute.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
    );

ALTER TABLE omnis.tenant_usage_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_usage_event FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_usage_event_scope ON omnis.tenant_usage_event;
CREATE POLICY tenant_usage_event_scope ON omnis.tenant_usage_event
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_usage_event.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_usage_event.tenant_id
              AND m.principal_id = tenant_usage_event.principal_id
              AND m.status = 'active'
        )
    );

REVOKE ALL ON omnis.tenant_usage_policy, omnis.tenant_usage_minute, omnis.tenant_usage_event FROM PUBLIC;
