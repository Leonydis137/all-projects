-- Bind tenant evidence and decision-rule mutations to the authenticated
-- transaction principal, and reject writes by inactive tenant identities.
DROP POLICY IF EXISTS tenant_evidence_tenant_isolation ON omnis.tenant_evidence;
CREATE POLICY tenant_evidence_tenant_isolation ON omnis.tenant_evidence
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND submitted_by = nullif(current_setting('omnis.principal_id', true), '')
        AND EXISTS (
            SELECT 1
            FROM omnis.tenant_membership AS m
            JOIN omnis.principal AS p ON p.principal_id = m.principal_id
            JOIN omnis.tenant AS t ON t.tenant_id = m.tenant_id
            WHERE m.tenant_id = tenant_evidence.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
              AND p.status = 'active'
              AND t.status = 'active'
        )
    );

DROP POLICY IF EXISTS tenant_decision_rule_scope ON omnis.tenant_decision_rule;
DROP POLICY IF EXISTS tenant_decision_rule_select ON omnis.tenant_decision_rule;
DROP POLICY IF EXISTS tenant_decision_rule_insert ON omnis.tenant_decision_rule;
DROP POLICY IF EXISTS tenant_decision_rule_update ON omnis.tenant_decision_rule;
DROP POLICY IF EXISTS tenant_decision_rule_delete ON omnis.tenant_decision_rule;

CREATE POLICY tenant_decision_rule_select ON omnis.tenant_decision_rule
    FOR SELECT
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
    );

CREATE POLICY tenant_decision_rule_insert ON omnis.tenant_decision_rule
    FOR INSERT
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND updated_by = nullif(current_setting('omnis.principal_id', true), '')::uuid
        AND EXISTS (
            SELECT 1
            FROM omnis.tenant_membership AS m
            JOIN omnis.principal AS p ON p.principal_id = m.principal_id
            JOIN omnis.tenant AS t ON t.tenant_id = m.tenant_id
            WHERE m.tenant_id = tenant_decision_rule.tenant_id
              AND m.principal_id = tenant_decision_rule.updated_by
              AND m.status = 'active'
              AND p.status = 'active'
              AND t.status = 'active'
        )
    );

CREATE POLICY tenant_decision_rule_update ON omnis.tenant_decision_rule
    FOR UPDATE
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND updated_by = nullif(current_setting('omnis.principal_id', true), '')::uuid
        AND EXISTS (
            SELECT 1
            FROM omnis.tenant_membership AS m
            JOIN omnis.principal AS p ON p.principal_id = m.principal_id
            JOIN omnis.tenant AS t ON t.tenant_id = m.tenant_id
            WHERE m.tenant_id = tenant_decision_rule.tenant_id
              AND m.principal_id = tenant_decision_rule.updated_by
              AND m.status = 'active'
              AND p.status = 'active'
              AND t.status = 'active'
        )
    );

CREATE POLICY tenant_decision_rule_delete ON omnis.tenant_decision_rule
    FOR DELETE
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1
            FROM omnis.tenant_membership AS m
            JOIN omnis.principal AS p ON p.principal_id = m.principal_id
            JOIN omnis.tenant AS t ON t.tenant_id = m.tenant_id
            WHERE m.tenant_id = tenant_decision_rule.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
              AND p.status = 'active'
              AND t.status = 'active'
        )
    );
