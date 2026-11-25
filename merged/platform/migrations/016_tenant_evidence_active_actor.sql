-- Bind every tenant evidence append to the transaction's authenticated principal.
-- Existing rows remain readable and are not rewritten by this policy replacement.
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
