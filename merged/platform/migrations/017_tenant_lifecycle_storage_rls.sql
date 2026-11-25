
-- Require an active tenant and principal for assistant and usage operations.
-- Keep credential revocation possible for suspended members; authentication
-- independently rejects suspended memberships and disabled principals.

DROP POLICY IF EXISTS tenant_assistant_conversation_scope ON omnis.tenant_assistant_conversation;
DROP POLICY IF EXISTS tenant_assistant_conversation_read ON omnis.tenant_assistant_conversation;
DROP POLICY IF EXISTS tenant_assistant_conversation_insert ON omnis.tenant_assistant_conversation;
DROP POLICY IF EXISTS tenant_assistant_conversation_update ON omnis.tenant_assistant_conversation;
CREATE POLICY tenant_assistant_conversation_read ON omnis.tenant_assistant_conversation
 FOR SELECT USING (
  tenant_id = nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_assistant_conversation.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_assistant_conversation_insert ON omnis.tenant_assistant_conversation
 FOR INSERT WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND created_by=nullif(current_setting('omnis.principal_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_assistant_conversation.tenant_id
    AND m.principal_id=created_by
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_assistant_conversation_update ON omnis.tenant_assistant_conversation
 FOR UPDATE
 USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_assistant_conversation.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'))
 WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_assistant_conversation.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));

-- Messages are append-only: readers SELECT and the service INSERTs only.
DROP POLICY IF EXISTS tenant_assistant_message_scope ON omnis.tenant_assistant_message;
DROP POLICY IF EXISTS tenant_assistant_message_read ON omnis.tenant_assistant_message;
DROP POLICY IF EXISTS tenant_assistant_message_insert ON omnis.tenant_assistant_message;
CREATE POLICY tenant_assistant_message_read ON omnis.tenant_assistant_message
 FOR SELECT USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_assistant_message.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_assistant_message_insert ON omnis.tenant_assistant_message
 FOR INSERT WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_assistant_message.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active')
  AND ((role='user' AND actor_id=nullif(current_setting('omnis.principal_id', true), '')::uuid)
    OR (role='assistant' AND actor_id IS NULL)));

-- Quota policy: all active members can read; mutations must be actor-attributed.
DROP POLICY IF EXISTS tenant_usage_policy_scope ON omnis.tenant_usage_policy;
DROP POLICY IF EXISTS tenant_usage_policy_read ON omnis.tenant_usage_policy;
DROP POLICY IF EXISTS tenant_usage_policy_insert ON omnis.tenant_usage_policy;
DROP POLICY IF EXISTS tenant_usage_policy_update ON omnis.tenant_usage_policy;
CREATE POLICY tenant_usage_policy_read ON omnis.tenant_usage_policy
 FOR SELECT USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_policy.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_usage_policy_insert ON omnis.tenant_usage_policy
 FOR INSERT WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND updated_by=nullif(current_setting('omnis.principal_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_policy.tenant_id AND m.principal_id=updated_by
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_usage_policy_update ON omnis.tenant_usage_policy
 FOR UPDATE
 USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_policy.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'))
 WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND updated_by=nullif(current_setting('omnis.principal_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_policy.tenant_id AND m.principal_id=updated_by
    AND m.status='active' AND p.status='active' AND t.status='active'));

-- Minute counters are tenant-scoped and usable only by active tenant actors.
DROP POLICY IF EXISTS tenant_usage_minute_scope ON omnis.tenant_usage_minute;
DROP POLICY IF EXISTS tenant_usage_minute_read ON omnis.tenant_usage_minute;
DROP POLICY IF EXISTS tenant_usage_minute_insert ON omnis.tenant_usage_minute;
DROP POLICY IF EXISTS tenant_usage_minute_update ON omnis.tenant_usage_minute;
CREATE POLICY tenant_usage_minute_read ON omnis.tenant_usage_minute
 FOR SELECT USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_minute.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_usage_minute_insert ON omnis.tenant_usage_minute
 FOR INSERT WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_minute.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_usage_minute_update ON omnis.tenant_usage_minute
 FOR UPDATE
 USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_minute.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'))
 WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_minute.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));

-- Usage events are append-only and attributed to the current principal.
DROP POLICY IF EXISTS tenant_usage_event_scope ON omnis.tenant_usage_event;
DROP POLICY IF EXISTS tenant_usage_event_read ON omnis.tenant_usage_event;
DROP POLICY IF EXISTS tenant_usage_event_insert ON omnis.tenant_usage_event;
CREATE POLICY tenant_usage_event_read ON omnis.tenant_usage_event
 FOR SELECT USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_event.tenant_id
    AND m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND m.status='active' AND p.status='active' AND t.status='active'));
CREATE POLICY tenant_usage_event_insert ON omnis.tenant_usage_event
 FOR INSERT WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership m
   JOIN omnis.principal p ON p.principal_id=m.principal_id
   JOIN omnis.tenant t ON t.tenant_id=m.tenant_id
   WHERE m.tenant_id=tenant_usage_event.tenant_id AND m.principal_id=tenant_usage_event.principal_id
    AND m.status='active' AND p.status='active' AND t.status='active'));

-- Suspended members' credential metadata remains visible to tenant admins and
-- revocable; issuance requires an active membership and active principal.
DROP POLICY IF EXISTS api_credential_tenant_scope ON omnis.api_credential;
DROP POLICY IF EXISTS api_credential_read ON omnis.api_credential;
DROP POLICY IF EXISTS api_credential_insert ON omnis.api_credential;
DROP POLICY IF EXISTS api_credential_revoke ON omnis.api_credential;
CREATE POLICY api_credential_read ON omnis.api_credential
 FOR SELECT USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership actor_m
   JOIN omnis.principal actor_p ON actor_p.principal_id=actor_m.principal_id
   JOIN omnis.tenant actor_t ON actor_t.tenant_id=actor_m.tenant_id
   WHERE actor_m.tenant_id=api_credential.tenant_id
    AND actor_m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND actor_m.status='active' AND actor_p.status='active' AND actor_t.status='active')
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership target_m
   JOIN omnis.tenant target_t ON target_t.tenant_id=target_m.tenant_id
   WHERE target_m.tenant_id=api_credential.tenant_id
    AND target_m.principal_id=api_credential.principal_id AND target_t.status='active'));
CREATE POLICY api_credential_insert ON omnis.api_credential
 FOR INSERT WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership actor_m
   JOIN omnis.principal actor_p ON actor_p.principal_id=actor_m.principal_id
   JOIN omnis.tenant actor_t ON actor_t.tenant_id=actor_m.tenant_id
   WHERE actor_m.tenant_id=api_credential.tenant_id
    AND actor_m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND actor_m.status='active' AND actor_p.status='active' AND actor_t.status='active')
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership target_m
   JOIN omnis.principal target_p ON target_p.principal_id=target_m.principal_id
   JOIN omnis.tenant target_t ON target_t.tenant_id=target_m.tenant_id
   WHERE target_m.tenant_id=api_credential.tenant_id AND target_m.principal_id=api_credential.principal_id
    AND target_m.status='active' AND target_p.status='active' AND target_t.status='active'));
CREATE POLICY api_credential_revoke ON omnis.api_credential
 FOR UPDATE
 USING (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership actor_m
   JOIN omnis.principal actor_p ON actor_p.principal_id=actor_m.principal_id
   JOIN omnis.tenant actor_t ON actor_t.tenant_id=actor_m.tenant_id
   WHERE actor_m.tenant_id=api_credential.tenant_id
    AND actor_m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND actor_m.status='active' AND actor_p.status='active' AND actor_t.status='active')
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership target_m
   JOIN omnis.tenant target_t ON target_t.tenant_id=target_m.tenant_id
   WHERE target_m.tenant_id=api_credential.tenant_id
    AND target_m.principal_id=api_credential.principal_id AND target_t.status='active'))
 WITH CHECK (
  tenant_id=nullif(current_setting('omnis.tenant_id', true), '')::uuid
  AND revoked_at IS NOT NULL
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership actor_m
   JOIN omnis.principal actor_p ON actor_p.principal_id=actor_m.principal_id
   JOIN omnis.tenant actor_t ON actor_t.tenant_id=actor_m.tenant_id
   WHERE actor_m.tenant_id=api_credential.tenant_id
    AND actor_m.principal_id=nullif(current_setting('omnis.principal_id', true), '')::uuid
    AND actor_m.status='active' AND actor_p.status='active' AND actor_t.status='active')
  AND EXISTS (SELECT 1 FROM omnis.tenant_membership target_m
   JOIN omnis.tenant target_t ON target_t.tenant_id=target_m.tenant_id
   WHERE target_m.tenant_id=api_credential.tenant_id
    AND target_m.principal_id=api_credential.principal_id AND target_t.status='active'));
