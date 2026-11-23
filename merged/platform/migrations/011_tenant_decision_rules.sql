-- Tenant-owned decision rules. Rules are isolated by forced RLS and audited transactionally.
CREATE TABLE IF NOT EXISTS omnis.tenant_decision_rule (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    name TEXT NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 120),
    field TEXT NOT NULL CHECK (field ~ '^[A-Za-z_][A-Za-z0-9_.]{0,127}$'),
    comparison TEXT NOT NULL CHECK (comparison IN ('>', '>=', '<', '<=', '==', '!=')),
    value JSONB NOT NULL,
    action TEXT NOT NULL CHECK (length(btrim(action)) BETWEEN 1 AND 160),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority BETWEEN -100000 AND 100000),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID NOT NULL REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    updated_by UUID NOT NULL REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tenant_decision_rule_name_uq UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS tenant_decision_rule_order_idx
    ON omnis.tenant_decision_rule (tenant_id, enabled, priority DESC, created_at, rule_id);

ALTER TABLE omnis.tenant_decision_rule ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_decision_rule FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_decision_rule_scope ON omnis.tenant_decision_rule;
CREATE POLICY tenant_decision_rule_scope ON omnis.tenant_decision_rule
    USING (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid)
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_decision_rule.tenant_id
              AND m.principal_id = tenant_decision_rule.updated_by
              AND m.status = 'active'
        )
    );

REVOKE ALL ON omnis.tenant_decision_rule FROM PUBLIC;
