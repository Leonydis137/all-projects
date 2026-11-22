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
    assert connection.cur.params == (digest_api_key(TOKEN, PEPPER), tenant, TOKEN[:32])


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
        credential_prefix=TOKEN[:20],
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
    assert test_audit.verify()


def test_identity_endpoint_rejects_missing_tenant_header():
    from fastapi.testclient import TestClient
    from omnis import api

    response = TestClient(api.app).get(
        "/v1/identity/me",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 401
