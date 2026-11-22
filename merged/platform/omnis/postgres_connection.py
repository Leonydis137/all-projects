"""Shared PostgreSQL connection policy for OMNIS ledger adapters."""
from __future__ import annotations

import ipaddress
import os
from typing import Any


def _sslmode_for_params(params: dict[str, str]) -> str:
    raw_host = params.get("host") or ""
    raw_hostaddr = params.get("hostaddr")
    if not raw_host and os.environ.get("PGHOST"):
        raise ValueError("PostgreSQL host resolved from PGHOST is unsupported; specify host in OMNIS_DATABASE_URL")
    if raw_hostaddr is None and os.environ.get("PGHOSTADDR"):
        raw_hostaddr = os.environ["PGHOSTADDR"]
    hosts = [item.strip().lower() for item in raw_host.split(",") if item.strip()]
    hostaddrs = [item.strip() for item in (raw_hostaddr or "").split(",") if item.strip()]
    local_names = {"localhost"}

    def is_loopback(address: str) -> bool:
        try:
            return ipaddress.ip_address(address).is_loopback
        except ValueError:
            return False

    if not hosts and not hostaddrs:
        # libpq may silently resolve hostless DSNs through service files.
        if params.get("service") or os.environ.get("PGSERVICE"):
            raise ValueError("hostless PostgreSQL DSNs with libpq service overrides are unsupported")
        return "disable"  # unambiguous libpq default local Unix socket

    addresses_are_local = all(is_loopback(address) for address in hostaddrs)
    if not hosts:
        if hostaddrs and addresses_are_local:
            return "disable"
        raise ValueError("remote PostgreSQL DSNs must include a hostname for TLS verification")

    host_is_local = all(
        host in local_names or host.startswith("/") or is_loopback(host)
        for host in hosts
    )
    if host_is_local and addresses_are_local:
        return "disable"
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
