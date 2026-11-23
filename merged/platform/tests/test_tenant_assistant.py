"""Tenant assistant conversations: authorization, context isolation, and audit."""
from fastapi.testclient import TestClient

from omnis import api
from omnis.audit import AuditLog
from omnis.identity import Principal

TENANT_ID = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
PRINCIPAL_ID = "1a2b3c4d-5e6f-4789-8abc-123456789abc"
TOKEN = "omnis_live_" + "A" * 48
CONVERSATION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class FakeUsageStore:
    def __init__(self):
        self.calls = []
        self.outcome = "accepted"
    def consume(self, tenant_id, principal_id, operation, requests_per_minute, audit_log):
        self.calls.append((tenant_id, principal_id, operation, requests_per_minute))
        if self.outcome != "accepted":
            from omnis.tenant_usage import TenantUsageError
            raise TenantUsageError(self.outcome)
        return {"operation": operation, "units": 1, "outcome": "accepted"}
    def summary(self, tenant_id, principal_id, audit_log):
        return {"period": "calendar_month", "accepted_requests": len(self.calls),
                "monthly_request_limit": None, "unlimited_if_no_limit": True, "usage": []}


class FakeAssistantStore:
    def __init__(self):
        self.conversations = {}
        self.history_messages = {}
    def create(self, tenant_id, actor_id, title, audit_log):
        assert tenant_id == TENANT_ID and actor_id == PRINCIPAL_ID
        result = {"conversation_id": CONVERSATION_ID, "title": title,
                  "message_count": 0, "created_at": "2026-11-23T00:00:00+00:00",
                  "updated_at": "2026-11-23T00:00:00+00:00"}
        self.conversations[CONVERSATION_ID] = result
        self.history_messages[CONVERSATION_ID] = []
        audit_log.record("tenant.assistant.conversation.created",
                         {"tenant_id": tenant_id, "conversation_id": CONVERSATION_ID},
                         actor=actor_id)
        return result
    def list(self, tenant_id, actor_id, limit=50):
        assert tenant_id == TENANT_ID and actor_id == PRINCIPAL_ID
        return list(self.conversations.values())[:limit]
    def history(self, tenant_id, actor_id, conversation_id, limit=20):
        if tenant_id != TENANT_ID or conversation_id not in self.conversations:
            from omnis.tenant_assistant import TenantConversationError
            raise TenantConversationError("conversation not found in this tenant")
        return self.conversations[conversation_id], self.history_messages[conversation_id][-limit:]
    def persist_exchange(self, tenant_id, actor_id, conversation_id, user_content,
                         assistant_content, expected_count, audit_log):
        result = self.conversations[conversation_id]
        if result["message_count"] != expected_count:
            from omnis.tenant_assistant import TenantConversationError
            raise TenantConversationError("conversation changed during generation")
        self.history_messages[conversation_id].extend([
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ])
        result = {**result, "message_count": expected_count + 2}
        self.conversations[conversation_id] = result
        audit_log.record("tenant.assistant.exchange.completed",
                         {"tenant_id": tenant_id, "conversation_id": conversation_id,
                          "message_count": expected_count + 2}, actor=actor_id)
        return result


def _client(monkeypatch, role="operator"):
    principal = Principal(TENANT_ID, PRINCIPAL_ID, "member@example.test",
                          "Tenant Member", role, TOKEN[:32])
    tenant_log, global_log, store = AuditLog(), AuditLog(), FakeAssistantStore()
    usage = FakeUsageStore()
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant: principal)
    monkeypatch.setattr(api, "tenant_audit", tenant_log)
    monkeypatch.setattr(api, "audit", global_log)
    monkeypatch.setattr(api, "tenant_assistant", store)
    monkeypatch.setattr(api, "tenant_usage", usage)
    monkeypatch.setattr(api.governance, "evaluate", lambda action, context=None: {
        "allowed": True, "violations": [], "checked": [],
    })
    return TestClient(api.app), tenant_log, global_log, store


def _headers():
    return {"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": TENANT_ID}


def test_tenant_member_can_create_and_list_own_tenant_conversations(monkeypatch):
    client, tenant_log, global_log, store = _client()
    created = client.post("/v1/tenant/assistant/conversations", headers=_headers(),
                          json={"title": "Operations review"})
    listed = client.get("/v1/tenant/assistant/conversations", headers=_headers())
    assert created.status_code == 200
    assert created.json()["conversation"]["title"] == "Operations review"
    assert listed.status_code == 200
    assert len(listed.json()["conversations"]) == 1
    assert tenant_log.verify()
    assert global_log.list() == []


def test_assistant_uses_database_history_not_client_supplied_history(monkeypatch):
    client, tenant_log, global_log, store = _client()
    store.conversations[CONVERSATION_ID] = {
        "conversation_id": CONVERSATION_ID, "title": "Private tenant context",
        "message_count": 2, "created_at": "2026-11-23T00:00:00+00:00",
        "updated_at": "2026-11-23T00:00:00+00:00",
    }
    store.history_messages[CONVERSATION_ID] = [
        {"role": "user", "content": "Stored tenant question"},
        {"role": "assistant", "content": "Stored tenant answer"},
    ]
    received = {}
    async def fake_chat(message, history):
        received["message"] = message
        received["history"] = history
        return "Response from isolated assistant"
    monkeypatch.setattr(api.assistant, "chat", fake_chat)
    response = client.post(
        f"/v1/tenant/assistant/conversations/{CONVERSATION_ID}/messages",
        headers=_headers(),
        json={"message": "Continue this", "history": [
            {"role": "user", "content": "INJECTED OTHER TENANT HISTORY"}
        ]},
    )
    assert response.status_code == 200
    assert received["message"] == "Continue this"
    assert received["history"] == store.history_messages[CONVERSATION_ID][:2]
    assert "INJECTED OTHER TENANT HISTORY" not in str(received["history"])
    assert response.json()["reply"] == "Response from isolated assistant"
    assert tenant_log.verify()
    assert global_log.list() == []


def test_reader_role_can_use_assistant_without_governance_execute(monkeypatch):
    client, _, _, _ = _client(role="reader")
    async def fake_chat(message, history):
        return "Read-only member response"
    monkeypatch.setattr(api.assistant, "chat", fake_chat)
    response = client.post("/v1/tenant/assistant/conversations", headers=_headers(),
                           json={"title": "Reader conversation"})
    assert response.status_code == 200
    sent = client.post(
        f"/v1/tenant/assistant/conversations/{CONVERSATION_ID}/messages",
        headers=_headers(), json={"message": "Hello"},
    )
    assert sent.status_code == 200


def test_conversation_id_from_another_tenant_is_not_found(monkeypatch):
    client, _, _, _ = _client()
    response = client.post(
        "/v1/tenant/assistant/conversations/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/messages",
        headers=_headers(), json={"message": "Hello"},
    )
    assert response.status_code == 404


def test_assistant_provider_failure_does_not_persist_exchange(monkeypatch):
    client, _, _, store = _client()
    store.conversations[CONVERSATION_ID] = {
        "conversation_id": CONVERSATION_ID, "title": "Failure test",
        "message_count": 0, "created_at": "2026-11-23T00:00:00+00:00",
        "updated_at": "2026-11-23T00:00:00+00:00",
    }
    store.history_messages[CONVERSATION_ID] = []
    async def fail_chat(message, history):
        raise api.assistant.AssistantUnavailable("provider unavailable")
    monkeypatch.setattr(api.assistant, "chat", fail_chat)
    response = client.post(
        f"/v1/tenant/assistant/conversations/{CONVERSATION_ID}/messages",
        headers=_headers(), json={"message": "Hello"},
    )
    assert response.status_code == 503
    assert store.conversations[CONVERSATION_ID]["message_count"] == 0
    assert store.history_messages[CONVERSATION_ID] == []



def test_assistant_requests_are_metered_per_tenant(monkeypatch):
    client, _, _, store = _client()
    store.conversations[CONVERSATION_ID] = {
        "conversation_id": CONVERSATION_ID, "title": "Metered conversation",
        "message_count": 0, "created_at": "2026-11-23T00:00:00+00:00",
        "updated_at": "2026-11-23T00:00:00+00:00",
    }
    store.history_messages[CONVERSATION_ID] = []
    async def fake_chat(message, history):
        return "Metered response"
    monkeypatch.setattr(api.assistant, "chat", fake_chat)
    response = client.post(
        f"/v1/tenant/assistant/conversations/{CONVERSATION_ID}/messages",
        headers=_headers(), json={"message": "Count this request"},
    )
    assert response.status_code == 200
    assert api.tenant_usage.calls == [(TENANT_ID, PRINCIPAL_ID, "assistant.message", 30)]


def test_assistant_rate_limit_returns_429_without_calling_provider(monkeypatch):
    client, _, _, store = _client()
    store.conversations[CONVERSATION_ID] = {
        "conversation_id": CONVERSATION_ID, "title": "Limited conversation",
        "message_count": 0, "created_at": "2026-11-23T00:00:00+00:00",
        "updated_at": "2026-11-23T00:00:00+00:00",
    }
    store.history_messages[CONVERSATION_ID] = []
    api.tenant_usage.outcome = "rate_limited"
    async def unexpected_chat(message, history):
        raise AssertionError("provider must not be called after a limit rejection")
    monkeypatch.setattr(api.assistant, "chat", unexpected_chat)
    response = client.post(
        f"/v1/tenant/assistant/conversations/{CONVERSATION_ID}/messages",
        headers=_headers(), json={"message": "This should be limited"},
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "tenant_rate_limit_exceeded"
