"""Tenant decision-rule authorization, isolation, and evaluation tests."""
from fastapi.testclient import TestClient

from omnis import api
from omnis.audit import AuditLog
from omnis.identity import Principal

TENANT_ID = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
PRINCIPAL_ID = "1a2b3c4d-5e6f-4789-8abc-123456789abc"
TOKEN = "omnis_live_" + "A" * 48


class FakeRuleStore:
    def __init__(self):
        self.rules = []
    def list_rules(self, tenant_id, include_disabled=False):
        assert tenant_id == TENANT_ID
        return list(self.rules)
    def create_rule(self, tenant_id, actor_id, rule, audit_log):
        assert tenant_id == TENANT_ID and actor_id == PRINCIPAL_ID
        result = {"rule_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", **rule, "enabled": True}
        self.rules.append(result)
        return result
    def update_rule(self, tenant_id, actor_id, rule_id, rule, audit_log):
        assert tenant_id == TENANT_ID and actor_id == PRINCIPAL_ID
        result = {"rule_id": rule_id, **rule, "enabled": True}
        self.rules = [result]
        return result
    def delete_rule(self, tenant_id, actor_id, rule_id, audit_log):
        assert tenant_id == TENANT_ID and actor_id == PRINCIPAL_ID
        self.rules = []
        return {"tenant_id": tenant_id, "rule_id": rule_id, "deleted": True}


def _client(monkeypatch, role="operator"):
    principal = Principal(TENANT_ID, PRINCIPAL_ID, "member@example.test", "Tenant Member", role, TOKEN[:32])
    tenant_log, global_log, store = AuditLog(), AuditLog(), FakeRuleStore()
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant: principal)
    monkeypatch.setattr(api, "tenant_audit", tenant_log)
    monkeypatch.setattr(api, "audit", global_log)
    monkeypatch.setattr(api, "tenant_decision_rules", store)
    monkeypatch.setattr(api.governance, "evaluate", lambda action, context=None: {
        "allowed": True, "violations": [], "checked": [],
    })
    return TestClient(api.app), tenant_log, global_log, store


def _headers():
    return {"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": TENANT_ID}


def _rule():
    return {"name": "urgent-review", "field": "risk_level", "op": ">=",
            "value": 6, "action": "manual-review", "priority": 50}


def test_operator_can_read_but_cannot_mutate_tenant_rules(monkeypatch):
    client, _, _, _ = _client(monkeypatch, "operator")
    assert client.get("/v1/tenant/decision-rules", headers=_headers()).status_code == 200
    response = client.post("/v1/tenant/decision-rules", headers=_headers(), json=_rule())
    assert response.status_code == 403


def test_admin_can_create_rule_and_event_is_tenant_audited(monkeypatch):
    client, tenant_log, global_log, store = _client(monkeypatch, "admin")
    response = client.post("/v1/tenant/decision-rules", headers=_headers(), json=_rule())
    assert response.status_code == 200
    assert response.json()["rule"]["name"] == "urgent-review"
    assert len(store.rules) == 1
    assert tenant_log.verify()
    assert global_log.list() == []


def test_tenant_decision_uses_custom_rule_without_mutating_global_engine(monkeypatch):
    client, _, _, store = _client(monkeypatch)
    store.rules.append({**_rule(), "rule_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                        "enabled": True})
    monkeypatch.setattr(api.engine, "decide", lambda context: {"action": "global-poison", "rule": "global"})
    response = client.post("/v1/tenant/decide", headers=_headers(),
                           json={"context": {"risk_level": 7}})
    assert response.status_code == 200
    assert response.json() == {"action": "manual-review", "rule": "urgent-review"}


def test_reader_can_read_tenant_rules_but_cannot_write(monkeypatch):
    client, _, _, _ = _client(monkeypatch, "reader")
    assert client.get("/v1/tenant/decision-rules", headers=_headers()).status_code == 200
    assert client.delete("/v1/tenant/decision-rules/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                         headers=_headers()).status_code == 403
