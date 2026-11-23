-- Bind each API credential to exactly one tenant.
-- Existing credentials are safely backfilled only where the principal has one membership.
BEGIN;
ALTER TABLE omnis.api_credential
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT;

-- Temporarily bypass RLS under the migration/table-owner lock so the controlled
-- backfill can see legacy rows even when migration 008 has FORCE ROW LEVEL SECURITY.
ALTER TABLE omnis.api_credential DISABLE ROW LEVEL SECURITY;

UPDATE omnis.api_credential c
SET tenant_id = (
    SELECT min(m.tenant_id::text)::uuid
    FROM omnis.tenant_membership m
    WHERE m.principal_id = c.principal_id
    HAVING count(*) = 1
)
WHERE c.tenant_id IS NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM omnis.api_credential WHERE tenant_id IS NULL) THEN
        RAISE EXCEPTION 'API credentials with ambiguous tenant memberships must be manually reissued before migration 009';
    END IF;
END;
$$;

ALTER TABLE omnis.api_credential ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE omnis.api_credential ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.api_credential FORCE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS api_credential_tenant_principal_idx
    ON omnis.api_credential (tenant_id, principal_id);

DROP POLICY IF EXISTS api_credential_tenant_scope ON omnis.api_credential;
CREATE POLICY api_credential_tenant_scope ON omnis.api_credential
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.principal_id = api_credential.principal_id
              AND m.tenant_id = api_credential.tenant_id
        )
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.principal_id = api_credential.principal_id
              AND m.tenant_id = api_credential.tenant_id
        )
    );

COMMIT;
