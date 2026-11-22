"""Controlled HTTPS source acquisition and platform-signed fetch attestations.

The attestation proves what this configured OMNIS fetcher observed. It is not a
publisher signature and does not establish that the source's claims are true.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import os
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit


MAX_SOURCE_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 8
MAX_URI_LENGTH = 2048
_ATTESTATION_VERSION = "omnis-fetch-attestation-v1"


class SourcePolicyError(ValueError):
    """The requested source violates the configured outbound policy."""


class SourceUnavailable(RuntimeError):
    """A source could not be retrieved within the configured safety limits."""


def _allowed_hosts() -> set[str]:
    raw = os.environ.get("OMNIS_SOURCE_ALLOWLIST", "")
    return {item.strip().encode("idna").decode("ascii").lower().rstrip(".")
            for item in raw.split(",") if item.strip()}


def _parse_source_uri(source_uri: str) -> tuple[str, str]:
    if not isinstance(source_uri, str) or not source_uri or len(source_uri) > MAX_URI_LENGTH:
        raise SourcePolicyError("source_uri is missing or exceeds the maximum length")
    try:
        parsed = urlsplit(source_uri)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise SourcePolicyError("source_uri is malformed") from exc
    if (parsed.scheme.lower() != "https" or not host or parsed.username or parsed.password
            or parsed.query or parsed.fragment or port not in (None, 443)):
        raise SourcePolicyError("only credential-free HTTPS URLs on port 443 without query or fragment are allowed")
    try:
        normalized_host = host.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise SourcePolicyError("source hostname is invalid") from exc
    try:
        ipaddress.ip_address(normalized_host)
    except ValueError:
        pass
    else:
        raise SourcePolicyError("IP-literal source URLs are not allowed")
    if not normalized_host or normalized_host not in _allowed_hosts():
        raise SourcePolicyError("source hostname is not in OMNIS_SOURCE_ALLOWLIST")
    path = parsed.path or "/"
    if any(ord(char) < 0x20 or ord(char) == 0x7f or char == " " for char in path):
        raise SourcePolicyError("source path contains invalid characters")
    return normalized_host, path


def _resolve_public_ips(host: str) -> list[str]:
    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise SourceUnavailable("source hostname could not be resolved") from exc
    addresses = sorted({item[4][0] for item in answers})
    if not addresses:
        raise SourceUnavailable("source hostname returned no addresses")
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as exc:
            raise SourceUnavailable("DNS returned an invalid address") from exc
        if not parsed.is_global:
            raise SourcePolicyError("source hostname resolves to a non-public IP address")
    return addresses


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to an IP already checked against SSRF policy."""

    def __init__(self, host: str, address: str, timeout: float):
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = address

    def connect(self) -> None:
        raw = socket.create_connection((self._pinned_address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def _fetch_pinned(host: str, path: str, address: str, max_bytes: int) -> tuple[bytes, str]:
    connection = _PinnedHTTPSConnection(host, address, FETCH_TIMEOUT_SECONDS)
    try:
        connection.request("GET", path, headers={
            "Host": host,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "close",
            "User-Agent": "OMNIS-Source-Acquisition/1",
        })
        response = connection.getresponse()
        if response.status != 200:
            raise SourceUnavailable(f"source returned HTTP {response.status}")
        encoding = response.getheader("Content-Encoding", "identity").lower()
        if encoding not in ("", "identity"):
            raise SourcePolicyError("compressed source responses are not accepted")
        declared_length = response.getheader("Content-Length")
        if declared_length:
            try:
                if int(declared_length) > max_bytes:
                    raise SourcePolicyError("source response exceeds the configured size limit")
            except ValueError as exc:
                raise SourceUnavailable("source returned an invalid Content-Length") from exc
        content = response.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise SourcePolicyError("source response exceeds the configured size limit")
        media_type = response.getheader("Content-Type", "application/octet-stream").split(";", 1)[0].strip().lower()
        return content, media_type or "application/octet-stream"
    except (SourcePolicyError, SourceUnavailable):
        raise
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        raise SourceUnavailable("source retrieval failed") from exc
    finally:
        connection.close()


def _signing_key():
    encoded = os.environ.get("OMNIS_PROVENANCE_PRIVATE_KEY_B64", "")
    if not encoded:
        raise SourceUnavailable("source acquisition signing key is not configured")
    try:
        raw = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
        )
        if len(raw) != 32:
            raise ValueError("expected a 32-byte Ed25519 private key")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        return Ed25519PrivateKey.from_private_bytes(raw)
    except Exception as exc:
        raise SourceUnavailable("source acquisition signing key is invalid") from exc


def public_key_document() -> dict[str, str]:
    from cryptography.hazmat.primitives import serialization
    key = _signing_key()
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fingerprint = hashlib.sha256(public_bytes).hexdigest()
    return {
        "algorithm": "Ed25519",
        "key_id": fingerprint,
        "public_key_b64": base64.urlsafe_b64encode(public_bytes).decode("ascii").rstrip("="),
        "trust_note": "Pin this key fingerprint out-of-band; a key returned by the same server is not independently trusted.",
    }


def acquire_and_attest(source_uri: str, license_name: str, fetcher_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch one allowlisted source, hash bytes, and sign the canonical fetch statement."""
    host, path = _parse_source_uri(source_uri)
    addresses = _resolve_public_ips(host)
    content, media_type = _fetch_pinned(host, path, addresses[0], MAX_SOURCE_BYTES)
    acquired_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    digest = hashlib.sha256(content).hexdigest()
    statement = {
        "version": _ATTESTATION_VERSION,
        "claim": "platform_observed_fetch",
        "source_uri": source_uri,
        "acquired_at": acquired_at,
        "content_sha256": digest,
        "content_length": len(content),
        "media_type": media_type,
        "fetcher_id": fetcher_id,
        "tls_hostname_verified": True,
        "redirects_followed": 0,
        "dns_addresses_checked": len(addresses),
    }
    key = _signing_key()
    from cryptography.hazmat.primitives import serialization
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fingerprint = hashlib.sha256(public_bytes).hexdigest()
    canonical = json.dumps(statement, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = key.sign(canonical)
    attestation = {
        "statement": statement,
        "algorithm": "Ed25519",
        "key_id": fingerprint,
        "public_key_b64": base64.urlsafe_b64encode(public_bytes).decode("ascii").rstrip("="),
        "signature_b64": base64.urlsafe_b64encode(signature).decode("ascii").rstrip("="),
    }
    record = {
        "source_uri": source_uri,
        "content_sha256": digest,
        "acquired_at": acquired_at,
        "acquisition_method": _ATTESTATION_VERSION,
        "license": license_name,
        "submitted_by": fetcher_id,
        "provenance_attestation": attestation,
    }
    return record, {
        "content_sha256": digest,
        "content_length": len(content),
        "media_type": media_type,
        "attestation": attestation,
        "source_authenticity": "not_established",
    }
