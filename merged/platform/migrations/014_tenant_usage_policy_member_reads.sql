-- Allow every active member of a tenant to read its quota policy.
-- The previous SELECT policy incorrectly required updated_by to equal the
-- current principal, hiding the policy from other members and making quota
-- enforcement fail open for those callers.
DROP POLICY IF EXISTS tenant_usage_policy_scope ON omnis.tenant_usage_policy;
CREATE POLICY tenant_usage_policy_scope ON omnis.tenant_usage_policy
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
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
