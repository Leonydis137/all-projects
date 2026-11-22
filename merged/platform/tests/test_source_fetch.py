import base64
import hashlib
import json
import socket

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from omnis import source_fetch
from omnis.evidence import EvidenceLedger, EvidenceValidationError, _validate


def _private_key_env(monkeypatch):
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    monkeypatch.setenv(
        "OMNIS_PROVENANCE_PRIVATE_KEY_B64",
        base64.urlsafe_b64encode(raw).decode("ascii").rstrip("="),
    )
    return key


def test_source_url_requires_exact_allowlisted_https_host(monkeypatch):
    monkeypatch.setenv("OMNIS_SOURCE_ALLOWLIST", "docs.example.org,api.example.org")
    assert source_fetch._parse_source_uri("https://docs.example.org/paper.pdf") == (
        "docs.example.org", "/paper.pdf"
    )
    for uri in (
        "http://docs.example.org/paper.pdf",
        "https://user:pass@docs.example.org/paper.pdf",
        "https://docs.example.org:8443/paper.pdf",
        "https://docs.example.org/paper.pdf?token=secret",
        "https://docs.example.org/paper.pdf#fragment",
        "https://other.example.org/paper.pdf",
        "https://127.0.0.1/private",
    ):
        with pytest.raises(source_fetch.SourcePolicyError):
            source_fetch._parse_source_uri(uri)


def test_source_fetch_requires_explicit_allowlist(monkeypatch):
    monkeypatch.delenv("OMNIS_SOURCE_ALLOWLIST", raising=False)
    with pytest.raises(source_fetch.SourceUnavailable, match="allowlist"):
        source_fetch._parse_source_uri("https://docs.example.org/paper.pdf")


def test_dns_resolution_rejects_private_or_mixed_answers(monkeypatch):
    def answers(host, port, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ]

    monkeypatch.setattr(source_fetch.socket, "getaddrinfo", answers)
    with pytest.raises(source_fetch.SourcePolicyError, match="non-public"):
        source_fetch._resolve_public_ips("docs.example.org")


def test_fetch_pins_validated_ip_and_requests_identity_encoding(monkeypatch):
    calls = {}

    class Response:
        status = 200

        def getheader(self, name, default=None):
            return {"Content-Encoding": "identity", "Content-Length": "4",
                    "Content-Type": "text/plain; charset=utf-8"}.get(name, default)

        def read(self, amount):
            calls["read_amount"] = amount
            return b"data"

    class Connection:
        def __init__(self, host, address, timeout):
            calls["connection"] = (host, address, timeout)

        def request(self, method, path, headers):
            calls["request"] = (method, path, headers)

        def getresponse(self):
            return Response()

        def close(self):
            calls["closed"] = True

    monkeypatch.setattr(source_fetch, "_PinnedHTTPSConnection", Connection)
    body, media_type = source_fetch._fetch_pinned("docs.example.org", "/a", "8.8.8.8", 10)
    assert body == b"data"
    assert media_type == "text/plain"
    assert calls["connection"][1] == "8.8.8.8"
    assert calls["request"][0:2] == ("GET", "/a")
    assert calls["request"][2]["Accept-Encoding"] == "identity"
    assert calls["closed"]


def test_fetch_rejects_redirects_and_compressed_responses(monkeypatch):
    class Response:
        status = 302

        def getheader(self, name, default=None):
            return {"Location": "https://evil.example/"}.get(name, default)

        def read(self, amount):
            return b""

    class Connection:
        def __init__(self, *args):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(source_fetch, "_PinnedHTTPSConnection", Connection)
    with pytest.raises(source_fetch.SourceUnavailable, match="HTTP 302"):
        source_fetch._fetch_pinned("docs.example.org", "/a", "8.8.8.8", 10)


def test_fetch_attestation_is_ed25519_signed_and_explicitly_limited(monkeypatch):
    private_key = _private_key_env(monkeypatch)
    monkeypatch.setenv("OMNIS_SOURCE_ALLOWLIST", "docs.example.org")
    monkeypatch.setattr(source_fetch, "_resolve_public_ips", lambda host: ["8.8.8.8"])
    monkeypatch.setattr(source_fetch, "_fetch_pinned", lambda *args: (b"independent source bytes", "application/pdf"))

    record, result = source_fetch.acquire_and_attest(
        "https://docs.example.org/paper.pdf", "CC-BY-4.0", "omnis-fetcher-test"
    )
    attestation = record["provenance_attestation"]
    statement = attestation["statement"]
    canonical = json.dumps(statement, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = base64.urlsafe_b64decode(attestation["signature_b64"] + "==")
    private_key.public_key().verify(signature, canonical)

    assert record["content_sha256"] == hashlib.sha256(b"independent source bytes").hexdigest()
    assert statement["claim"] == "platform_observed_fetch"
    assert statement["tls_hostname_verified"] is True
    assert statement["redirects_followed"] == 0
    assert result["source_authenticity"] == "not_established"
    assert attestation["key_id"] == source_fetch.public_key_document()["key_id"]
    assert _validate(record)["provenance_attestation"] == attestation


def test_attestation_must_match_record_source_and_digest():
    record = {
        "source_uri": "https://docs.example.org/a",
        "content_sha256": "a" * 64,
        "acquired_at": "2026-11-22T10:00:00Z",
        "acquisition_method": "test",
        "license": "unknown",
        "submitted_by": "test",
        "provenance_attestation": {
            "statement": {"source_uri": "https://docs.example.org/a", "content_sha256": "b" * 64},
            "algorithm": "Ed25519",
            "key_id": "c" * 64,
            "public_key_b64": "public",
            "signature_b64": "signature",
        },
    }
    with pytest.raises(EvidenceValidationError, match="does not match"):
        _validate(record)


def test_signed_attestation_is_part_of_evidence_hash_chain(tmp_path, monkeypatch):
    _private_key_env(monkeypatch)
    monkeypatch.setenv("OMNIS_SOURCE_ALLOWLIST", "docs.example.org")
    monkeypatch.setattr(source_fetch, "_resolve_public_ips", lambda host: ["8.8.8.8"])
    monkeypatch.setattr(source_fetch, "_fetch_pinned", lambda *args: (b"source", "text/plain"))
    record, _ = source_fetch.acquire_and_attest(
        "https://docs.example.org/source", "unknown", "test-fetcher"
    )
    ledger = EvidenceLedger(tmp_path / "evidence.sqlite3")
    stored = ledger.append(record)
    assert stored["provenance_attestation"] == record["provenance_attestation"]
    assert ledger.verify()["valid"] is True


@pytest.mark.parametrize(
    "headers, expected",
    [
        ({"Content-Encoding": "gzip", "Content-Length": "4"}, source_fetch.SourcePolicyError),
        ({"Content-Encoding": "identity", "Content-Length": "11"}, source_fetch.SourcePolicyError),
    ],
)
def test_fetch_rejects_compression_and_declared_oversize(monkeypatch, headers, expected):
    class Response:
        status = 200

        def getheader(self, name, default=None):
            return headers.get(name, default)

        def read(self, amount):
            raise AssertionError("body must not be read after rejected headers")

    class Connection:
        def __init__(self, *args):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(source_fetch, "_PinnedHTTPSConnection", Connection)
    with pytest.raises(expected):
        source_fetch._fetch_pinned("docs.example.org", "/a", "8.8.8.8", 10)


def test_attestation_rejects_tampered_signature(tmp_path, monkeypatch):
    _private_key_env(monkeypatch)
    monkeypatch.setenv("OMNIS_SOURCE_ALLOWLIST", "docs.example.org")
    monkeypatch.setattr(source_fetch, "_resolve_public_ips", lambda host: ["8.8.8.8"])
    monkeypatch.setattr(source_fetch, "_fetch_pinned", lambda *args: (b"source", "text/plain"))
    record, _ = source_fetch.acquire_and_attest(
        "https://docs.example.org/source", "unknown", "test-fetcher"
    )
    record["provenance_attestation"]["signature_b64"] = base64.urlsafe_b64encode(b"x" * 64).decode().rstrip("=")
    with pytest.raises(EvidenceValidationError, match="signature is invalid"):
        _validate(record)
