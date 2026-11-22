# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
import pytest
from fastapi.testclient import TestClient

from omnis import config, governance, stats
from omnis.api import app
from omnis.protocols import AEON, Context
from omnis.recommend import Recommender

@pytest.fixture(autouse=True)
def _configured_test_token(monkeypatch):
    from omnis import api
    monkeypatch.setattr(config, "API_TOKEN", "test-token")
    api._health_cache["checked_at"] = 0.0
    api._health_cache["response"] = None


c = TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_health_and_sources():
    response = c.get("/health")
    h = response.json()
    assert response.status_code == 200
    assert h["status"] == "ok" and h["sources_present"]
    assert h["evidence_ledger"]["valid"]


@pytest.mark.parametrize("component", ["audit", "evidence"])
def test_health_returns_503_when_integrity_verifier_raises(monkeypatch, component):
    from omnis import api

    verifier = getattr(api, component)
    api._health_cache["checked_at"] = 0.0
    api._health_cache["response"] = None
    method = "health" if hasattr(verifier, "health") else "verify"
    monkeypatch.setattr(verifier, method, lambda: (_ for _ in ()).throw(RuntimeError("private storage detail")))
    response = c.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert "private storage detail" not in response.text


def test_protected_api_fails_closed_when_token_is_unset(monkeypatch):
    monkeypatch.setattr(config, "API_TOKEN", "")
    response = c.get("/v1/catalog")
    assert response.status_code == 503


def test_catalog_covers_all_projects():
    d = c.get("/v1/catalog").json()
    assert len(d["projects"]) >= 20 and d["totals"]["files"] > 1000
    assert any("POST /v1/govern" in p["platform_features"] for p in d["projects"])


def test_governance_rules():
    assert not governance.evaluate({})["allowed"]  # fails closed without evidence
    assert governance.evaluate(governance.stamp({}))["allowed"]
    v = governance.evaluate(governance.stamp({"harm": 1, "intent": "malicious"}))
    assert {x["rule"] for x in v["violations"]} >= {"PreserveLifeRule"}


def test_decide_and_block():
    assert c.post("/v1/decide", json={"context": {"risk_level": 9}}).json()["action"] == "alert"
    r = c.post("/v1/decide", json={"context": {"risk_level": 9}, "attributes": {"harm": 5}})
    assert r.status_code == 403 and r.json()["detail"]["blocked_by"] == "covenant"


def test_client_cannot_override_platform_evidence():
    r = c.post("/v1/decide", json={"context": {}, "attributes": {"auditable": False, "mission": "X"}})
    assert r.status_code == 200


def test_rules_crud_and_validation():
    assert c.post("/v1/decision/rules", json={"name": "t", "field": "x", "op": "~", "value": 1, "action": "a"}).status_code == 422
    assert c.post("/v1/decision/rules", json={"name": "t", "field": "x", "op": ">", "value": 1, "action": "a", "priority": 99}).status_code == 200
    assert c.post("/v1/decide", json={"context": {"x": 5}}).json()["rule"] == "t"


def test_protocols():
    a = AEON()
    assert a.respond(Context("anxious"))["protocol"] == "relax"
    assert a.respond(Context("???"))["protocol"] is None


def test_recommend_and_math_and_stats():
    r = Recommender(); r.fit([[0, 0], [5, 5], [1, 1]])
    assert r.recommend([1, 1], 1)[0]["index"] == 2
    assert c.post("/v1/math/gcd-lcm", json={"numbers": [12, 18]}).json() == {"gcd": 6, "lcm": 36}
    assert c.post("/v1/math/gcd-lcm", json={"numbers": []}).status_code == 422
    assert stats.ab_test(50, 1000, 90, 1000)["p_b_beats_a"] > 0.99
    assert c.post("/v1/stats/ab", json={"conv_a": 5, "n_a": 1, "conv_b": 0, "n_b": 1}).status_code == 422
    assert stats.posterior(1.0) == pytest.approx(0.5)


def test_audit_chain():
    c.post("/v1/decide", json={"context": {}})
    a = c.get("/v1/audit").json()
    assert a["valid"] and a["entries"]


def test_sites_served():
    assert c.get("/sites/portfolio/").status_code == 200
    console = c.get("/")
    assert console.status_code == 200
    assert "evidence ledger" in console.text.lower()


def test_assistant_requires_key(monkeypatch):
    from omnis import config
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert c.post("/v1/assistant", json={"message": "hi"}).status_code == 503


def test_token_auth(monkeypatch):
    from omnis import config
    monkeypatch.setattr(config, "API_TOKEN", "s3cret")
    assert c.get("/v1/catalog").status_code == 401
    assert c.get("/v1/catalog", headers={"Authorization": "Bearer s3cret"}).status_code == 200


def test_audit_endpoint_returns_snapshot_storage_failure_without_listing(monkeypatch):
    from omnis import api

    class UnavailableAudit:
        def snapshot(self, limit=50):
            return {"verification": {"valid": False, "reason": "storage_error"}, "entries": []}

        def list(self, limit=50):
            raise AssertionError("snapshot response must not issue a second list query")

    monkeypatch.setattr(api, "audit", UnavailableAudit())
    response = c.get("/v1/audit")
    assert response.status_code == 503
    assert response.json()["verification"]["reason"] == "storage_error"
    assert response.json()["entries"] == []


def test_health_probe_reuses_recent_database_result(monkeypatch):
    from omnis import api

    calls = {"audit": 0, "evidence": 0}

    class Probe:
        def __init__(self, key):
            self.key = key

        def health(self):
            calls[self.key] += 1
            return True if self.key == "audit" else {"valid": True, "checked": 0}

    monkeypatch.setattr(api, "audit", Probe("audit"))
    monkeypatch.setattr(api, "evidence", Probe("evidence"))
    api._health_cache["checked_at"] = 0.0
    api._health_cache["response"] = None
    assert c.get("/health").status_code == 200
    assert c.get("/health").status_code == 200
    assert calls == {"audit": 1, "evidence": 1}


def test_audit_endpoint_preserves_specific_integrity_failure(monkeypatch):
    from omnis import api

    class CorruptAudit:
        def snapshot(self, limit=50):
            return {"verification": {"valid": False, "reason": "malformed_event", "failed_index": 7},
                    "entries": []}

    monkeypatch.setattr(api, "audit", CorruptAudit())
    response = c.get("/v1/audit")
    assert response.status_code == 503
    assert response.json()["verification"] == {
        "valid": False, "reason": "malformed_event", "failed_index": 7
    }


def test_sqlite_idempotent_evidence_retry_does_not_duplicate_audit(monkeypatch):
    from omnis import api

    calls = []

    class ExistingEvidence:
        def append(self, record):
            return {"sequence": 3, "record_hash": "a" * 64, "idempotent_replay": True}

    class AuditSpy:
        def record(self, kind, payload):
            calls.append((kind, payload))

    monkeypatch.setattr(api, "evidence", ExistingEvidence())
    monkeypatch.setattr(api, "audit", AuditSpy())
    response = c.post("/v1/evidence", json={
        "source_uri": "https://example.org/retry",
        "content_sha256": "a" * 64,
        "acquired_at": "2026-11-22T10:00:00Z",
        "acquisition_method": "test",
        "license": "unknown",
        "submitted_by": "test",
        "idempotency_key": "retry-key",
    })
    assert response.status_code == 200
    assert not any(kind == "evidence.append" for kind, _ in calls)


def test_every_api_route_is_audited_even_without_covenant_gate():
    from omnis import api

    response = c.post("/v1/stats/posterior", json={"bayes_factor": 2.0})
    assert response.status_code == 200
    entries = api.audit.list(limit=500)
    recent = entries[-2:]
    assert [entry["kind"] for entry in recent] == [
        "http.request.started", "http.request.completed"
    ]
    assert recent[0]["payload"] == {"method": "POST", "path": "/v1/stats/posterior"}
    assert recent[1]["payload"]["status_code"] == 200


def test_audit_unavailable_blocks_api_dispatch(monkeypatch):
    from omnis import api

    class UnavailableAudit:
        def record(self, kind, payload):
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(api, "audit", UnavailableAudit())
    response = c.post("/v1/math/gcd-lcm", json={"numbers": [12, 18]})
    assert response.status_code == 503
    assert response.json()["detail"] == "audit_unavailable"


def test_completion_audit_failure_is_explicit_without_replaying_action(monkeypatch):
    from omnis import api

    class CompletionFailureAudit:
        def record(self, kind, payload):
            if kind == "http.request.completed":
                raise RuntimeError("database unavailable")

    monkeypatch.setattr(api, "audit", CompletionFailureAudit())
    response = c.post("/v1/math/gcd-lcm", json={"numbers": [12, 18]})
    assert response.status_code == 200
    assert response.json() == {"gcd": 6, "lcm": 36}
    assert response.headers["X-OMNIS-Audit-Status"] == "incomplete"
