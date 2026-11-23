-- Tenant-isolated assistant conversations and append-only message history.
CREATE TABLE IF NOT EXISTS omnis.tenant_assistant_conversation (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES omnis.tenant(tenant_id) ON DELETE RESTRICT,
    created_by UUID NOT NULL REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    title TEXT NOT NULL DEFAULT 'New conversation'
        CHECK (length(btrim(title)) BETWEEN 1 AND 160),
    message_count INTEGER NOT NULL DEFAULT 0 CHECK (message_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tenant_assistant_conversation_tenant_id_uq UNIQUE (tenant_id, conversation_id)
);

CREATE INDEX IF NOT EXISTS tenant_assistant_conversation_recent_idx
    ON omnis.tenant_assistant_conversation (tenant_id, updated_at DESC, conversation_id);

CREATE TABLE IF NOT EXISTS omnis.tenant_assistant_message (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    message_index INTEGER NOT NULL CHECK (message_index > 0),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 24000),
    actor_id UUID REFERENCES omnis.principal(principal_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tenant_assistant_message_conversation_fk
        FOREIGN KEY (tenant_id, conversation_id)
        REFERENCES omnis.tenant_assistant_conversation (tenant_id, conversation_id)
        ON DELETE RESTRICT,
    CONSTRAINT tenant_assistant_message_index_uq
        UNIQUE (tenant_id, conversation_id, message_index),
    CONSTRAINT tenant_assistant_message_actor_ck
        CHECK ((role = 'user' AND actor_id IS NOT NULL) OR (role = 'assistant' AND actor_id IS NULL))
);

CREATE INDEX IF NOT EXISTS tenant_assistant_message_history_idx
    ON omnis.tenant_assistant_message (tenant_id, conversation_id, message_index);

ALTER TABLE omnis.tenant_assistant_conversation ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_assistant_conversation FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_assistant_conversation_scope ON omnis.tenant_assistant_conversation;
CREATE POLICY tenant_assistant_conversation_scope ON omnis.tenant_assistant_conversation
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_assistant_conversation.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND created_by = nullif(current_setting('omnis.principal_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_assistant_conversation.tenant_id
              AND m.principal_id = created_by
              AND m.status = 'active'
        )
    );

ALTER TABLE omnis.tenant_assistant_message ENABLE ROW LEVEL SECURITY;
ALTER TABLE omnis.tenant_assistant_message FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_assistant_message_scope ON omnis.tenant_assistant_message;
CREATE POLICY tenant_assistant_message_scope ON omnis.tenant_assistant_message
    USING (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_assistant_message.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
    )
    WITH CHECK (
        tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
        AND EXISTS (
            SELECT 1 FROM omnis.tenant_membership m
            WHERE m.tenant_id = tenant_assistant_message.tenant_id
              AND m.principal_id = nullif(current_setting('omnis.principal_id', true), '')::uuid
              AND m.status = 'active'
        )
        AND (
            (role = 'user' AND actor_id = nullif(current_setting('omnis.principal_id', true), '')::uuid)
            OR (role = 'assistant' AND actor_id IS NULL)
        )
    );

REVOKE ALL ON omnis.tenant_assistant_conversation, omnis.tenant_assistant_message FROM PUBLIC;
