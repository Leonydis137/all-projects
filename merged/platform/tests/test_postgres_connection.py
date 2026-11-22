"""Unit tests for PostgreSQL connection security policy."""
import pytest

from omnis.postgres_connection import _sslmode_for_params


def test_loopback_connections_may_use_plaintext(monkeypatch):
    for name in ("PGSERVICE", "PGHOST", "PGHOSTADDR"):
        monkeypatch.delenv(name, raising=False)
    assert _sslmode_for_params({"host": "localhost"}) == "disable"
    assert _sslmode_for_params({"host": "127.0.0.1", "hostaddr": "127.0.0.1"}) == "disable"
    assert _sslmode_for_params({"hostaddr": "127.0.0.1"}) == "disable"
    assert _sslmode_for_params({}) == "disable"


def test_remote_connections_require_verified_tls():
    assert _sslmode_for_params({"host": "db.example.net"}) == "verify-full"
    assert _sslmode_for_params({"host": "db.example.net", "hostaddr": "203.0.113.10"}) == "verify-full"


def test_remote_hostaddr_cannot_hide_behind_loopback_hostname():
    with pytest.raises(ValueError, match="loopback"):
        _sslmode_for_params({"host": "localhost", "hostaddr": "203.0.113.10"})


def test_environment_hostaddr_cannot_hide_behind_loopback_hostname(monkeypatch):
    monkeypatch.setenv("PGHOSTADDR", "203.0.113.10")
    with pytest.raises(ValueError, match="loopback"):
        _sslmode_for_params({"host": "localhost"})


def test_remote_hostaddr_requires_a_verifiable_hostname():
    with pytest.raises(ValueError, match="hostname"):
        _sslmode_for_params({"hostaddr": "203.0.113.10"})


def test_hostless_libpq_environment_overrides_are_rejected(monkeypatch):
    monkeypatch.setenv("PGHOST", "db.remote.example")
    with pytest.raises(ValueError, match="hostless"):
        _sslmode_for_params({})


def test_service_based_dsns_are_rejected_without_resolved_host():
    with pytest.raises(ValueError, match="service"):
        _sslmode_for_params({"service": "remote-db"})


def test_service_environment_is_rejected_even_with_local_host(monkeypatch):
    monkeypatch.setenv("PGSERVICE", "remote-db")
    with pytest.raises(ValueError, match="service"):
        _sslmode_for_params({"host": "localhost"})
