"""Tenant-authenticated access to stateless OMNIS platform capabilities."""
from fastapi.testclient import TestClient

from omnis import api
from omnis.audit import AuditLog
from omnis.identity import Principal


TENANT_ID = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
PRINCIPAL_ID = "1a2b3c4d-5e6f-4789-8abc-123456789abc"
TOKEN = "omnis_live_" + "A" * 48


def _client(monkeypatch, role="operator"):
    principal = Principal(
        tenant_id=TENANT_ID,
        principal_id=PRINCIPAL_ID,
        email="operator@example.test",
        display_name="Tenant Operator",
        role=role,
        credential_prefix=TOKEN[:32],
    )
    tenant_log = AuditLog()
    global_log = AuditLog()
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant: principal)
    monkeypatch.setattr(api, "tenant_audit", tenant_log)
    monkeypatch.setattr(api, "audit", global_log)
    evaluated = {}
    def evaluate(action, context=None):
        evaluated["action"] = action
        evaluated["context"] = context
        return {"allowed": True, "violations": []}

    monkeypatch.setattr(api.governance, "evaluate", evaluate)
    monkeypatch.setattr(api.mathops, "gcd_lcm", lambda numbers: {
        "gcd": 6, "lcm": 36,
    })
    return TestClient(api.app), tenant_log, global_log, evaluated


def _headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-OMNIS-Tenant": TENANT_ID,
    }


def test_tenant_decision_is_governed_and_written_to_tenant_audit(monkeypatch):
    client, tenant_log, global_log, evaluated = _client(monkeypatch)
    response = client.post(
        "/v1/tenant/decide",
        headers=_headers(),
        json={"context": {"risk_level": 9}, "attributes": {"type": "caller-override"}},
    )

    assert response.status_code == 200
    assert response.json() == {"action": "alert", "rule": "high-risk-alert"}
    kinds = [entry["kind"] for entry in tenant_log.list()]
    assert kinds == ["http.request.started", "govern", "http.request.completed"]
    assert tenant_log.list()[1]["payload"]["action"] == "tenant.decision"
    assert tenant_log.list()[1]["actor"] == PRINCIPAL_ID
    assert evaluated["action"]["type"] == "tenant.decision"
    assert evaluated["context"] == {"risk_level": 9}
    assert global_log.list() == []


def test_tenant_routes_do_not_use_shared_mutable_engines(monkeypatch):
    client, _, _, _ = _client(monkeypatch)
    monkeypatch.setattr(api.engine, "decide", lambda context: {
        "action": "cross-tenant-poison", "rule": "legacy-mutation",
    })
    monkeypatch.setattr(api.aeon, "respond", lambda context: {
        "protocol": "cross-tenant-poison", "response": "legacy-mutation",
    })

    decision = client.post(
        "/v1/tenant/decide",
        headers=_headers(),
        json={"context": {"risk_level": 9}},
    )
    protocol = client.post(
        "/v1/tenant/protocols/respond",
        headers=_headers(),
        json={"emotional_tone": "frustrated"},
    )

    assert decision.status_code == 200
    assert decision.json()["action"] == "alert"
    assert protocol.status_code == 200
    assert protocol.json()["protocol"] == "collaborate"


def test_tenant_operation_cannot_be_used_by_reader_role(monkeypatch):
    client, tenant_log, global_log, _ = _client(monkeypatch, role="reader")
    response = client.post(
        "/v1/tenant/math/gcd-lcm",
        headers=_headers(),
        json={"numbers": [12, 18]},
    )

    assert response.status_code == 403
    assert "governance:execute" in response.json()["detail"]
    assert [entry["kind"] for entry in tenant_log.list()] == [
        "http.request.started", "http.request.completed",
    ]
    assert global_log.list() == []


def test_tenant_math_operation_returns_result_and_tenant_audit(monkeypatch):
    client, tenant_log, _, _ = _client(monkeypatch)
    response = client.post(
        "/v1/tenant/math/gcd-lcm",
        headers=_headers(),
        json={"numbers": [12, 18]},
    )

    assert response.status_code == 200
    assert response.json()["gcd"] == 6
    assert response.json()["lcm"] == 36
    assert tenant_log.list()[1]["payload"]["action"] == "tenant.math.gcd_lcm"


def test_tenant_stats_validation_is_preserved(monkeypatch):
    client, tenant_log, _, _ = _client(monkeypatch)
    response = client.post(
        "/v1/tenant/stats/ab",
        headers=_headers(),
        json={"conv_a": 8, "n_a": 5, "conv_b": 1, "n_b": 5},
    )

    assert response.status_code == 422
    assert tenant_log.list()[1]["payload"]["action"] == "tenant.stats.ab"
