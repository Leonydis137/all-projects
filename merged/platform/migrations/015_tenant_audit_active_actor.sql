-- Require tenant audit writes to be attributed to the transaction's authenticated
-- principal, and reject writes by suspended members, disabled principals, or
-- suspended tenants. Reads remain tenant-scoped by the existing USING clause.
DROP POLICY IF EXISTS tenant_audit_event_scope ON omnis.tenant_audit_event;
CREATE POLICY tenant_audit_event_scope ON omnis.tenant_audit_event
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND actor = nullif(current_setting('omnis.principal_id', true), '')::uuid
        AND EXISTS (
            SELECT 1
            FROM omnis.tenant_membership AS m
            JOIN omnis.principal AS p ON p.principal_id = m.principal_id
            JOIN omnis.tenant AS t ON t.tenant_id = m.tenant_id
            WHERE m.tenant_id = tenant_audit_event.tenant_id
              AND m.principal_id = tenant_audit_event.actor
              AND m.status = 'active'
              AND p.status = 'active'
              AND t.status = 'active'
        )
    );
