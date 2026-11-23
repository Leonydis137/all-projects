import hashlib
import hmac
import pytest

from omnis.identity import (
    IdentityUnavailable,
    InvalidCredential,
    Principal,
    digest_api_key,
    normalize_tenant_id,
)

TOKEN = "omnis_live_" + "A" * 48
PEPPER = "test-pepper-that-is-at-least-32-characters-long"


def test_api_key_digest_is_keyed_hmac_sha256():
    actual = digest_api_key(TOKEN, PEPPER)
    expected = hmac.new(PEPPER.encode(), TOKEN.encode(), hashlib.sha256).hexdigest()
    assert actual == expected
    assert len(actual) == 64


def test_api_key_digest_rejects_malformed_tokens():
    with pytest.raises(InvalidCredential):
        digest_api_key("not-a-token", PEPPER)


def test_api_key_digest_requires_strong_pepper():
    with pytest.raises(IdentityUnavailable):
        digest_api_key(TOKEN, "short")


def test_tenant_id_is_canonicalized():
    value = "A3D7A1B4-1B2C-4D5E-8F90-123456789ABC"
    assert normalize_tenant_id(value) == value.lower()


@pytest.mark.parametrize("value", [None, "", "not-a-uuid", "tenant-1"])
def test_tenant_id_must_be_uuid(value):
    with pytest.raises(InvalidCredential):
        normalize_tenant_id(value)


def test_role_permissions_are_least_privilege():
    reader = Principal("tenant", "principal", "a@example.test", "A", "reader", "omnis_live_")
    operator = Principal("tenant", "principal", "a@example.test", "A", "operator", "omnis_live_")
    assert reader.allows("evidence:read")
    assert not reader.allows("evidence:write")
    assert not reader.allows("members:manage")
    assert operator.allows("evidence:write")
    assert not operator.allows("members:manage")


def test_database_authentication_requires_matching_active_membership():
    from omnis.identity import authenticate_api_key

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    principal = "1a2b3c4d-5e6f-4789-8abc-123456789abc"

    class Cursor:
        def __init__(self):
            self.row = {
                "tenant_id": tenant,
                "principal_id": principal,
                "email": "user@example.test",
                "display_name": "Test User",
                "role": "operator",
                "token_prefix": TOKEN[:32],
            }
            self.params = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params):
            self.params = params

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.cur = Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return self.cur

    connection = Connection()
    result = authenticate_api_key(
        TOKEN, tenant, dsn="postgresql://unused", pepper=PEPPER,
        connect_factory=lambda: connection,
    )
    assert result.principal_id == principal
    assert result.tenant_id == tenant
    assert result.role == "operator"
    assert connection.cur.params == (digest_api_key(TOKEN, PEPPER), tenant, tenant, TOKEN[:32])


def test_database_authentication_rejects_missing_membership():
    from omnis.identity import authenticate_api_key

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params):
            self.params = params

        def fetchone(self):
            return None

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return Cursor()

    with pytest.raises(InvalidCredential):
        authenticate_api_key(
            TOKEN, "a3d7a1b4-1b2c-4d5e-8f90-123456789abc",
            dsn="postgresql://unused", pepper=PEPPER,
            connect_factory=Connection,
        )


def test_identity_endpoint_uses_database_principal_and_attributes_audit(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    principal = Principal(
        tenant_id="a3d7a1b4-1b2c-4d5e-8f90-123456789abc",
        principal_id="1a2b3c4d-5e6f-4789-8abc-123456789abc",
        email="user@example.test",
        display_name="Test User",
        role="operator",
        credential_prefix=TOKEN[:32],
    )
    test_audit = AuditLog()
    monkeypatch.setattr(api, "audit", test_audit)
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant: principal)
    response = TestClient(api.app).get(
        "/v1/identity/me",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": principal.tenant_id},
    )
    assert response.status_code == 200
    assert response.json()["principal_id"] == principal.principal_id
    assert "evidence:write" in response.json()["permissions"]
    assert all(entry.get("actor") == principal.principal_id for entry in test_audit.list())
    assert all(entry["payload"].get("tenant_id") == principal.tenant_id for entry in test_audit.list())
    assert test_audit.verify()


def test_identity_endpoint_rejects_missing_tenant_header():
    from fastapi.testclient import TestClient
    from omnis import api

    response = TestClient(api.app).get(
        "/v1/identity/me",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 401


def test_tenant_evidence_routes_enforce_role_and_tenant_context(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    operator = Principal(
        tenant_id=tenant, principal_id="1a2b3c4d-5e6f-4789-8abc-123456789abc",
        email="operator@example.test", display_name="Operator", role="operator",
        credential_prefix=TOKEN[:32],
    )
    reader = Principal(
        tenant_id=tenant, principal_id="2a2b3c4d-5e6f-4789-8abc-123456789abc",
        email="reader@example.test", display_name="Reader", role="reader",
        credential_prefix=TOKEN[:32],
    )

    class TenantStore:
        def __init__(self):
            self.append_args = None

        def append_with_audit(self, record, tenant_id, actor_id, audit):
            self.append_args = (record, tenant_id, actor_id)
            return {"sequence": 1, "tenant_id": tenant_id, **record, "submitted_by": actor_id}

        def list(self, tenant_id, limit=100, before=None):
            return [{"tenant_id": tenant_id, "sequence": 1}]

        def verify(self, tenant_id):
            return {"valid": True, "checked": 1, "tenant_id": tenant_id}

    store = TenantStore()
    test_audit = AuditLog()
    monkeypatch.setattr(api, "tenant_evidence", store)
    monkeypatch.setattr(api, "audit", test_audit)
    current = {"principal": operator}
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: current["principal"])
    client = TestClient(api.app)
    headers = {"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant}

    denied = client.post("/v1/tenant/evidence", headers=headers, json={
        "source_uri": "https://example.test/item",
        "content_sha256": "a" * 64,
        "acquired_at": "2026-11-22T10:00:00Z",
        "acquisition_method": "test",
        "license": "unknown",
    })
    assert denied.status_code == 200
    assert store.append_args[1:] == (tenant, operator.principal_id)

    current["principal"] = reader
    forbidden = client.post("/v1/tenant/evidence", headers=headers, json={
        "source_uri": "https://example.test/reader",
        "content_sha256": "b" * 64,
        "acquired_at": "2026-11-22T10:00:00Z",
        "acquisition_method": "test",
        "license": "unknown",
    })
    assert forbidden.status_code == 403
    listed = client.get("/v1/tenant/evidence", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["records"][0]["tenant_id"] == tenant
    assert test_audit.verify()


def test_tenant_credential_cannot_access_legacy_global_routes(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api, config

    monkeypatch.setattr(config, "API_TOKEN", "legacy-only-token")
    response = TestClient(api.app).get(
        "/v1/catalog",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"},
    )
    assert response.status_code == 401


def test_tenant_admin_routes_require_membership_management(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    owner = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "owner@example.test", "Owner", "owner", TOKEN[:32])
    reader = Principal(tenant, "2a2b3c4d-5e6f-4789-8abc-123456789abc",
                       "reader@example.test", "Reader", "reader", TOKEN[:32])

    class AdminStore:
        def __init__(self):
            self.added = None
        def list_members(self, tenant_id):
            return [{"tenant_id": tenant_id, "principal_id": owner.principal_id}]
        def add_member(self, tenant_id, email, display_name, role, actor_id, actor_role, audit):
            self.added = (tenant_id, email, role, actor_id, actor_role)
            return {"tenant_id": tenant_id, "email": email, "role": role}

    store = AdminStore()
    current = {"principal": owner}
    monkeypatch.setattr(api, "tenant_admin", store)
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: current["principal"])
    client = TestClient(api.app)
    headers = {"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant}

    created = client.post("/v1/tenant/members", headers=headers, json={
        "email": "new@example.test", "display_name": "New Member", "role": "reader",
    })
    assert created.status_code == 200
    assert store.added == (tenant, "new@example.test", "reader", owner.principal_id, "owner")

    current["principal"] = reader
    denied = client.get("/v1/tenant/members", headers=headers)
    assert denied.status_code == 403


def test_only_owner_can_assign_owner_role(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    admin = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "admin@example.test", "Admin", "admin", TOKEN[:32])
    class AdminStore:
        def add_member(self, *args):
            raise AssertionError("owner assignment must be rejected before storage")
    monkeypatch.setattr(api, "tenant_admin", AdminStore())
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: admin)
    response = TestClient(api.app).post(
        "/v1/tenant/members",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant},
        json={"email": "new@example.test", "display_name": "New Owner", "role": "owner"},
    )
    assert response.status_code == 403


def test_tenant_source_fetch_is_governed_before_network(monkeypatch):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    operator = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                         "operator@example.test", "Operator", "operator", TOKEN[:32])
    monkeypatch.setattr(api, "tenant_evidence", object())
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: operator)
    def deny(*args, **kwargs):
        raise HTTPException(403, "blocked by test governance")
    def network_must_not_run(*args, **kwargs):
        raise AssertionError("network must not run before COVENANT authorization")
    monkeypatch.setattr(api, "gated", deny)
    monkeypatch.setattr(api, "acquire_and_attest", network_must_not_run)
    response = TestClient(api.app).post(
        "/v1/tenant/source/fetch",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant},
        json={"source_uri": "https://allowed.example.test/document", "license": "unknown"},
    )
    assert response.status_code == 403


def test_owner_can_assign_second_owner(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    owner = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "owner@example.test", "Owner", "owner", TOKEN[:32])
    class AdminStore:
        def add_member(self, tenant_id, email, display_name, role, actor_id, actor_role, audit):
            assert role == "owner"
            assert actor_role == "owner"
            return {"tenant_id": tenant_id, "email": email, "role": role}
    monkeypatch.setattr(api, "tenant_admin", AdminStore())
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: owner)
    response = TestClient(api.app).post(
        "/v1/tenant/members",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant},
        json={"email": "second-owner@example.test", "display_name": "Second Owner", "role": "owner"},
    )
    assert response.status_code == 200
    assert response.json()["member"]["role"] == "owner"


def test_tenant_source_fetch_persists_to_authenticated_tenant(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    operator = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                         "operator@example.test", "Operator", "operator", TOKEN[:32])
    attestation = {"statement": {"claim": "platform_observed_fetch"}, "algorithm": "Ed25519"}
    record = {
        "source_uri": "https://allowed.example.test/document",
        "content_sha256": "c" * 64,
        "acquired_at": "2026-11-23T00:00:00Z",
        "acquisition_method": "omnis-fetch-attestation-v1",
        "license": "unknown",
        "submitted_by": "omnis-source-fetcher",
        "provenance_attestation": attestation,
    }
    class TenantStore:
        def append_with_audit(self, value, tenant_id, actor_id, audit):
            assert tenant_id == operator.tenant_id
            assert actor_id == operator.principal_id
            assert value["provenance_attestation"] == attestation
            return {"tenant_id": tenant_id, **value, "submitted_by": actor_id}
    monkeypatch.setattr(api, "tenant_evidence", TenantStore())
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: operator)
    monkeypatch.setattr(api, "gated", lambda *args, **kwargs: {"allowed": True})
    monkeypatch.setattr(api, "acquire_and_attest", lambda *args: (record, {"content_sha256": "c" * 64}))
    response = TestClient(api.app).post(
        "/v1/tenant/source/fetch",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant},
        json={"source_uri": "https://allowed.example.test/document", "license": "unknown"},
    )
    assert response.status_code == 200
    assert response.json()["record"]["submitted_by"] == operator.principal_id


def test_tenant_audit_api_and_governance_use_tenant_chain(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    owner = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "owner@example.test", "Owner", "owner", TOKEN[:32])

    class TenantAudit:
        def __init__(self):
            self.events = []
        def record(self, kind, payload, actor=None):
            self.events.append({"kind": kind, "payload": payload, "actor": actor})
            return self.events[-1]
        def list(self, tenant_id, limit=100, before=None):
            assert all(event["payload"].get("tenant_id") == tenant_id for event in self.events)
            return self.events[-limit:]
        def verify(self, tenant_id):
            assert all(event["payload"].get("tenant_id") == tenant_id for event in self.events)
            return {"valid": True, "checked": len(self.events), "head": "a" * 64}

    tenant_log = TenantAudit()
    monkeypatch.setattr(api, "tenant_audit", tenant_log)
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: owner)
    monkeypatch.setattr(api.governance, "evaluate", lambda action, context=None: {
        "allowed": True, "violations": [], "checked": [],
    })
    client = TestClient(api.app)
    headers = {"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant}

    governed = client.post("/v1/tenant/govern", headers=headers,
                           json={"action": {"type": "test.action"}, "context": {}})
    assert governed.status_code == 200
    assert any(event["kind"] == "governance.evaluate" for event in tenant_log.events)

    listed = client.get("/v1/tenant/audit", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["events"]
    verified = client.get("/v1/tenant/audit/verify", headers=headers)
    assert verified.status_code == 200
    assert verified.json()["valid"] is True
    assert all(event["payload"].get("tenant_id") == tenant for event in tenant_log.events)

def test_tenant_credential_inventory_is_permission_gated_and_never_returns_tokens(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    owner = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "owner@example.test", "Owner", "owner", TOKEN[:32])
    reader = Principal(tenant, "2a2b3c4d-5e6f-4789-8abc-123456789abc",
                       "reader@example.test", "Reader", "reader", TOKEN[:32])

    class AdminStore:
        def list_credentials(self, tenant_id):
            assert tenant_id == tenant
            return [{"credential_id": "3a2b3c4d-5e6f-4789-8abc-123456789abc",
                     "principal_id": owner.principal_id, "email": owner.email,
                     "label": "console", "expires_at": "2027-01-01T00:00:00Z",
                     "revoked_at": None, "created_at": "2026-11-23T00:00:00Z"}]

    current = {"principal": owner}
    monkeypatch.setattr(api, "tenant_admin", AdminStore())
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: current["principal"])
    client = TestClient(api.app)
    headers = {"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant}

    listed = client.get("/v1/tenant/credentials", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["credentials"][0]["label"] == "console"
    assert "api_token_once" not in listed.text
    assert "token_digest" not in listed.text

    current["principal"] = reader
    denied = client.get("/v1/tenant/credentials", headers=headers)
    assert denied.status_code == 403


def test_credential_revocation_uses_tenant_audit_log(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    owner = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "owner@example.test", "Owner", "owner", TOKEN[:32])

    class AdminStore:
        def revoke_credential(self, tenant_id, credential_id, actor_id, actor_role, audit_log):
            assert audit_log is tenant_log
            return {"tenant_id": tenant_id, "credential_id": credential_id, "revoked": True}

    class TenantAudit:
        def record(self, *args, **kwargs):
            return None
    tenant_log = TenantAudit()
    monkeypatch.setattr(api, "tenant_admin", AdminStore())
    monkeypatch.setattr(api, "tenant_audit", tenant_log)
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: owner)
    response = TestClient(api.app).delete(
        "/v1/tenant/credentials/3a2b3c4d-5e6f-4789-8abc-123456789abc",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant},
    )
    assert response.status_code == 200

def test_tenant_admin_overview_is_owner_only_and_tenant_scoped(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    owner = Principal(tenant, "1a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "owner@example.test", "Owner", "owner", TOKEN[:32])
    admin = Principal(tenant, "2a2b3c4d-5e6f-4789-8abc-123456789abc",
                      "admin@example.test", "Admin", "admin", TOKEN[:32])

    class AdminStore:
        def overview(self, tenant_id):
            assert tenant_id == tenant
            return {"tenant_id": tenant_id, "slug": "example-tenant",
                    "display_name": "Example Tenant", "status": "active",
                    "member_count": 2, "active_member_count": 2,
                    "active_owner_count": 1, "credential_count": 2,
                    "active_credential_count": 1}

    current = {"principal": owner}
    monkeypatch.setattr(api, "tenant_admin", AdminStore())
    test_audit = AuditLog()
    monkeypatch.setattr(api, "audit", test_audit)
    monkeypatch.setattr(api, "tenant_audit", None)
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: current["principal"])
    client = TestClient(api.app)
    headers = {"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant}

    response = client.get("/v1/tenant/admin/overview", headers=headers)
    assert response.status_code == 200
    assert response.json()["overview"]["active_owner_count"] == 1
    assert response.json()["overview"]["tenant_id"] == tenant
    assert any(entry.get("actor") == owner.principal_id for entry in test_audit.list())

    current["principal"] = admin
    denied = client.get("/v1/tenant/admin/overview", headers=headers)
    assert denied.status_code == 403


def test_tenant_admin_overview_rejects_reader(monkeypatch):
    from fastapi.testclient import TestClient
    from omnis import api
    from omnis.audit import AuditLog

    tenant = "a3d7a1b4-1b2c-4d5e-8f90-123456789abc"
    reader = Principal(tenant, "3a2b3c4d-5e6f-4789-8abc-123456789abc",
                       "reader@example.test", "Reader", "reader", TOKEN[:32])
    monkeypatch.setattr(api, "tenant_admin", object())
    monkeypatch.setattr(api, "audit", AuditLog())
    monkeypatch.setattr(api, "authenticate_api_key", lambda token, tenant_id: reader)
    response = TestClient(api.app).get(
        "/v1/tenant/admin/overview",
        headers={"Authorization": f"Bearer {TOKEN}", "X-OMNIS-Tenant": tenant},
    )
    assert response.status_code == 403
