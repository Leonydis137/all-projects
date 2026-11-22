"""Shared PostgreSQL connection policy for OMNIS ledger adapters."""
from __future__ import annotations

import ipaddress
from typing import Any


def _sslmode_for_params(params: dict[str, str]) -> str:
    hosts = [item.strip().lower() for item in (params.get("host") or "").split(",") if item.strip()]
    hostaddrs = [item.strip() for item in (params.get("hostaddr") or "").split(",") if item.strip()]
    local_names = {"localhost"}

    def is_loopback(address: str) -> bool:
        try:
            return ipaddress.ip_address(address).is_loopback
        except ValueError:
            return False

    if not hosts and not hostaddrs:
        return "disable"  # libpq's default local Unix socket
    host_is_local = bool(hosts) and all(
        host in local_names or host.startswith("/") or is_loopback(host)
        for host in hosts
    )
    addresses_are_local = all(is_loopback(address) for address in hostaddrs)
    local = host_is_local and addresses_are_local
    if local:
        return "disable"

    if not hosts:
        raise ValueError("remote PostgreSQL DSNs must include a hostname for TLS verification")
    if hostaddrs and host_is_local:
        raise ValueError("a remote hostaddr cannot be paired with a loopback PostgreSQL hostname")
    return "verify-full"


def connect_postgres(dsn: str, row_factory: Any, *, statement_timeout_ms: int = 10_000):
    """Connect with verified TLS for remote hosts and bounded database operations."""
    try:
        import psycopg
        from psycopg.conninfo import conninfo_to_dict
    except ImportError as exc:
        raise RuntimeError("PostgreSQL storage requires psycopg; install platform requirements") from exc

    sslmode = _sslmode_for_params(conninfo_to_dict(dsn))
    timeout = int(statement_timeout_ms)
    if timeout < 0:
        raise ValueError("statement timeout must be non-negative")
    return psycopg.connect(
        dsn,
        row_factory=row_factory,
        sslmode=sslmode,
        connect_timeout=5,
        options=f"-c statement_timeout={timeout}",
    )
