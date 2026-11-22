"""Shared PostgreSQL connection policy for OMNIS ledger adapters."""
from __future__ import annotations

import ipaddress
from typing import Any


def connect_postgres(dsn: str, row_factory: Any, *, statement_timeout_ms: int = 10_000):
    """Connect with verified TLS for remote hosts and bounded database operations."""
    try:
        import psycopg
        from psycopg.conninfo import conninfo_to_dict
    except ImportError as exc:
        raise RuntimeError("PostgreSQL storage requires psycopg; install platform requirements") from exc

    params = conninfo_to_dict(dsn)
    hosts = [item.strip().lower() for item in (params.get("host") or "").split(",") if item.strip()]
    hostaddrs = [item.strip() for item in (params.get("hostaddr") or "").split(",") if item.strip()]
    local_names = {"localhost"}

    def is_loopback(address: str) -> bool:
        try:
            return ipaddress.ip_address(address).is_loopback
        except ValueError:
            return False

    # No host/hostaddr means libpq's local Unix-socket default.
    if not hosts and not hostaddrs:
        local = True
    else:
        host_is_local = bool(hosts) and all(
            host in local_names or host.startswith("/") or is_loopback(host)
            for host in hosts
        )
        addresses_are_local = all(is_loopback(address) for address in hostaddrs)
        local = host_is_local and addresses_are_local

    # A remote hostaddr without a DNS host cannot be authenticated by hostname.
    if not local and not hosts:
        raise ValueError("remote PostgreSQL DSNs must include a hostname for TLS verification")

    sslmode = "disable" if local else "verify-full"
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
