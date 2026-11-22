import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from omnis import api, config


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "API_TOKEN", "source-test-token")
    monkeypatch.setattr(config, "DATABASE_URL", "")
    api._health_cache["checked_at"] = 0.0
    api._health_cache["response"] = None
    return TestClient(api.app, headers={"Authorization": "Bearer source-test-token"})


def test_source_fetch_is_governed_and_persists_signed_record(monkeypatch, client):
    calls = []

    record = {
        "source_uri": "https://docs.example.org/paper",
        "content_sha256": "a" * 64,
        "acquired_at": "2026-11-23T10:00:00Z",
        "acquisition_method": "omnis-fetch-attestation-v1",
        "license": "CC-BY-4.0",
        "submitted_by": "omnis-source-fetcher",
        "provenance_attestation": {"statement": {"claim": "platform_observed_fetch"}},
    }

    class Evidence:
        def append(self, value):
            calls.append(("append", value))
            return {"sequence": 1, "record_hash": "b" * 64, **value}

    class Audit:
        def record(self, kind, payload):
            calls.append((kind, payload))

    monkeypatch.setattr(api, "evidence", Evidence())
    monkeypatch.setattr(api, "audit", Audit())
    monkeypatch.setattr(api, "gated", lambda kind, attrs=None: calls.append(("govern", kind)))
    monkeypatch.setattr(api, "acquire_and_attest", lambda *args: (record, {
        "content_sha256": "a" * 64, "content_length": 12,
        "media_type": "application/pdf", "attestation": record["provenance_attestation"],
        "source_authenticity": "not_established",
    }))

    response = client.post("/v1/source/fetch", json={
        "source_uri": "https://docs.example.org/paper", "license": "CC-BY-4.0"
    })
    assert response.status_code == 200
    assert response.json()["evidence"]["sequence"] == 1
    assert response.json()["source_authenticity"] == "not_established"
    assert calls[0] == ("govern", "source.fetch")
    assert calls[1][0] == "append"
    assert calls[2][0] == "evidence.append"


def test_source_fetch_does_not_access_network_when_covenant_blocks(monkeypatch, client):
    def blocked(*args, **kwargs):
        raise HTTPException(403, "blocked by COVENANT")

    def network_must_not_run(*args, **kwargs):
        raise AssertionError("network acquisition must not run after policy denial")

    monkeypatch.setattr(api, "gated", blocked)
    monkeypatch.setattr(api, "acquire_and_attest", network_must_not_run)
    response = client.post("/v1/source/fetch", json={"source_uri": "https://docs.example.org/paper"})
    assert response.status_code == 403


def test_attestation_public_key_endpoint_fails_closed_without_key(monkeypatch, client):
    monkeypatch.delenv("OMNIS_PROVENANCE_PRIVATE_KEY_B64", raising=False)
    response = client.get("/v1/source/attestation-key")
    assert response.status_code == 503


def test_attestation_public_key_endpoint_returns_pinnable_fingerprint(monkeypatch, client):
    import base64
    import hashlib
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    monkeypatch.setenv("OMNIS_PROVENANCE_PRIVATE_KEY_B64", base64.urlsafe_b64encode(raw).decode().rstrip("="))
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    response = client.get("/v1/source/attestation-key")
    assert response.status_code == 200
    assert response.json()["key_id"] == hashlib.sha256(public).hexdigest()
