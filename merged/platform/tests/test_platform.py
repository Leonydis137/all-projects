# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
import pytest
from fastapi.testclient import TestClient

from omnis import governance, stats
from omnis.api import app
from omnis.protocols import AEON, Context
from omnis.recommend import Recommender

c = TestClient(app)


def test_health_and_sources():
    h = c.get("/health").json()
    assert h["status"] == "ok" and h["sources_present"]


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
    assert c.get("/").status_code == 200


def test_assistant_requires_key(monkeypatch):
    from omnis import config
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert c.post("/v1/assistant", json={"message": "hi"}).status_code == 503


def test_token_auth(monkeypatch):
    from omnis import config
    monkeypatch.setattr(config, "API_TOKEN", "s3cret")
    assert c.get("/v1/catalog").status_code == 401
    assert c.get("/v1/catalog", headers={"Authorization": "Bearer s3cret"}).status_code == 200
