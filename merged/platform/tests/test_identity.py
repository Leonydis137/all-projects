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
