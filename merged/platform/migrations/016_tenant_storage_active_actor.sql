-- Bind tenant evidence submissions and decision-rule mutations to the active
-- principal selected by the authenticated tenant request.
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
              AND m.principal_id::text = tenant_evidence.submitted_by
              AND m.status = 'active'
              AND p.status = 'active'
              AND t.status = 'active'
        )
    );

DROP POLICY IF EXISTS tenant_decision_rule_scope ON omnis.tenant_decision_rule;
CREATE POLICY tenant_decision_rule_scope ON omnis.tenant_decision_rule
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
