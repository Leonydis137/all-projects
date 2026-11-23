"""PostgreSQL-backed tenant assistant conversation storage."""
from __future__ import annotations

from typing import Any, Callable
from uuid import UUID


class TenantConversationError(ValueError):
    """A conversation is invalid or does not belong to the selected tenant."""


class TenantConversationUnavailable(RuntimeError):
    """Tenant conversation storage is not configured or unavailable."""


class TenantAssistantStore:
    def __init__(self, dsn: str, connect_factory: Callable[[], Any] | None = None):
        if not isinstance(dsn, str) or not dsn.strip():
            raise TenantConversationUnavailable("PostgreSQL tenant conversations are not configured")
        self.dsn, self.connect_factory = dsn, connect_factory

    def _connect(self):
        if self.connect_factory:
            return self.connect_factory()
        try:
            from psycopg.rows import dict_row
            from .postgres_connection import connect_postgres
            return connect_postgres(self.dsn, dict_row, statement_timeout_ms=8000)
        except Exception as exc:
            raise TenantConversationUnavailable("tenant conversation storage is unavailable") from exc

    @staticmethod
    def _uuid(value: str, field: str) -> str:
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise TenantConversationError(f"{field} must be a UUID") from exc

    @staticmethod
    def _scope(cur, tenant: str, principal: str) -> None:
        cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant,))
        cur.execute("SELECT set_config('omnis.principal_id', %s, true)", (principal,))

    @staticmethod
    def _conversation(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "conversation_id": str(row["conversation_id"]),
            "title": row["title"],
            "message_count": row["message_count"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def create(self, tenant_id: str, actor_id: str, title: str, audit_log) -> dict[str, Any]:
        tenant = self._uuid(tenant_id, "tenant_id")
        actor = self._uuid(actor_id, "actor_id")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
            raise TenantConversationError("title must contain 1-160 characters")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant, actor)
                cur.execute(
                    """INSERT INTO omnis.tenant_assistant_conversation
                       (tenant_id, created_by, title)
                       VALUES (%s, %s, %s)
                       RETURNING conversation_id, title, message_count, created_at, updated_at""",
                    (tenant, actor, title.strip()),
                )
                result = self._conversation(cur.fetchone())
                audit_log.record_in_transaction(
                    db, "tenant.assistant.conversation.created",
                    {"tenant_id": tenant, "conversation_id": result["conversation_id"]},
                    actor=actor,
                )
        return result

    def list(self, tenant_id: str, actor_id: str, limit: int = 50) -> list[dict[str, Any]]:
        tenant = self._uuid(tenant_id, "tenant_id")
        actor = self._uuid(actor_id, "actor_id")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise TenantConversationError("limit must be between 1 and 100")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant, actor)
                cur.execute(
                    """SELECT conversation_id, title, message_count, created_at, updated_at
                       FROM omnis.tenant_assistant_conversation
                       WHERE tenant_id = %s
                       ORDER BY updated_at DESC, conversation_id
                       LIMIT %s""",
                    (tenant, limit),
                )
                return [self._conversation(row) for row in cur.fetchall()]

    def history(self, tenant_id: str, actor_id: str, conversation_id: str,
                limit: int = 20) -> tuple[dict[str, Any], list[dict[str, str]]]:
        tenant = self._uuid(tenant_id, "tenant_id")
        actor = self._uuid(actor_id, "actor_id")
        conversation = self._uuid(conversation_id, "conversation_id")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant, actor)
                cur.execute(
                    """SELECT conversation_id, title, message_count, created_at, updated_at
                       FROM omnis.tenant_assistant_conversation
                       WHERE tenant_id = %s AND conversation_id = %s""",
                    (tenant, conversation),
                )
                row = cur.fetchone()
                if row is None:
                    raise TenantConversationError("conversation not found in this tenant")
                metadata = self._conversation(row)
                cur.execute(
                    """SELECT role, content FROM omnis.tenant_assistant_message
                       WHERE tenant_id = %s AND conversation_id = %s
                       ORDER BY message_index DESC LIMIT %s""",
                    (tenant, conversation, limit),
                )
                messages = list(reversed(cur.fetchall()))
                return metadata, [{"role": item["role"], "content": item["content"]} for item in messages]

    def persist_exchange(self, tenant_id: str, actor_id: str, conversation_id: str,
                         user_content: str, assistant_content: str, expected_count: int,
                         audit_log) -> dict[str, Any]:
        tenant = self._uuid(tenant_id, "tenant_id")
        actor = self._uuid(actor_id, "actor_id")
        conversation = self._uuid(conversation_id, "conversation_id")
        if not isinstance(user_content, str) or not 1 <= len(user_content.strip()) <= 12000:
            raise TenantConversationError("message must contain 1-12000 characters")
        if not isinstance(assistant_content, str) or not 1 <= len(assistant_content.strip()) <= 12000:
            raise TenantConversationError("assistant response is empty or too long")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant, actor)
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                            (f"omnis.tenant_assistant:{tenant}:{conversation}",))
                cur.execute(
                    """SELECT message_count FROM omnis.tenant_assistant_conversation
                       WHERE tenant_id = %s AND conversation_id = %s FOR UPDATE""",
                    (tenant, conversation),
                )
                row = cur.fetchone()
                if row is None:
                    raise TenantConversationError("conversation not found in this tenant")
                if row["message_count"] != expected_count:
                    raise TenantConversationError("conversation changed during generation; retry with the latest history")
                next_index = expected_count + 1
                cur.execute(
                    """INSERT INTO omnis.tenant_assistant_message
                       (tenant_id, conversation_id, message_index, role, content, actor_id)
                       VALUES (%s, %s, %s, 'user', %s, %s),
                              (%s, %s, %s, 'assistant', %s, NULL)""",
                    (tenant, conversation, next_index, user_content.strip(), actor,
                     tenant, conversation, next_index + 1, assistant_content.strip()),
                )
                cur.execute(
                    """UPDATE omnis.tenant_assistant_conversation
                       SET message_count = %s, updated_at = now()
                       WHERE tenant_id = %s AND conversation_id = %s
                       RETURNING conversation_id, title, message_count, created_at, updated_at""",
                    (expected_count + 2, tenant, conversation),
                )
                result = self._conversation(cur.fetchone())
                audit_log.record_in_transaction(
                    db, "tenant.assistant.exchange.completed",
                    {"tenant_id": tenant, "conversation_id": conversation,
                     "message_count": result["message_count"]},
                    actor=actor,
                )
        return result
