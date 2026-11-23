-- Tenant context is transaction-local and enforced by PostgreSQL, not only API filters.
-- The runtime role must not own these tables or have BYPASSRLS.
ALTER TABLE omnis.tenant ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_identity_scope ON omnis.tenant;
CREATE POLICY tenant_identity_scope ON omnis.tenant
    USING (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid);

ALTER TABLE omnis.tenant_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_membership FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_membership_scope ON omnis.tenant_membership;
CREATE POLICY tenant_membership_scope ON omnis.tenant_membership
    USING (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid);

ALTER TABLE omnis.api_credential ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.api_credential FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS api_credential_tenant_scope ON omnis.api_credential;
CREATE POLICY api_credential_tenant_scope ON omnis.api_credential
    USING (EXISTS (
        SELECT 1 FROM omnis.tenant_membership m
        WHERE m.principal_id = api_credential.principal_id
          AND m.tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM omnis.tenant_membership m
        WHERE m.principal_id = api_credential.principal_id
          AND m.tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
    ));

REVOKE ALL ON omnis.tenant, omnis.tenant_membership, omnis.api_credential FROM PUBLIC;
