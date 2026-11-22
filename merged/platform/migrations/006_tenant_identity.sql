-- OMNIS tenant identity and API credential foundation.
-- Apply after migrations 001-005. Runtime credentials are high-entropy bearer
-- tokens; only keyed HMAC-SHA256 digests are stored.
CREATE TABLE IF NOT EXISTS omnis.tenant (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
    display_name TEXT NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 160),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS omnis.principal (
    principal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    display_name TEXT NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 160),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT principal_email_normalized CHECK (email = lower(btrim(email))),
    CONSTRAINT principal_email_nonempty CHECK (length(email) BETWEEN 3 AND 320),
    CONSTRAINT principal_email_uq UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS omnis.tenant_membership (
    tenant_id UUID NOT NULL REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    principal_id UUID NOT NULL REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'operator', 'analyst', 'reader')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, principal_id)
);

CREATE TABLE IF NOT EXISTS omnis.api_credential (
    credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id UUID NOT NULL REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    token_prefix TEXT NOT NULL CHECK (length(token_prefix) BETWEEN 8 AND 32),
    token_digest CHAR(64) NOT NULL UNIQUE CHECK (token_digest ~ '^[0-9a-f]{64}$'),
    label TEXT NOT NULL CHECK (length(btrim(label)) BETWEEN 1 AND 100),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tenant_membership_principal_idx
    ON omnis.tenant_membership (principal_id, status);
CREATE INDEX IF NOT EXISTS api_credential_principal_idx
    ON omnis.api_credential (principal_id, revoked_at);

-- Runtime may read identity and membership data but cannot provision or mutate it.
REVOKE ALL ON omnis.tenant, omnis.principal, omnis.tenant_membership, omnis.api_credential FROM PUBLIC;
