"""Shared SSRF protection utilities for all HTTP executors.

Mitigations implemented here:
1. Every hostname is resolved with `getaddrinfo` and ALL returned addresses
   are validated against the blocked-network list before use.
2. IPv4-mapped IPv6 addresses (e.g. ``::ffff:127.0.0.1``) are normalized to
   their IPv4 form before the check, closing the classic bypass that hides a
   private IPv4 behind an IPv6 wrapper.
3. Executors re-validate the URL on EVERY hop of a redirect chain, so a DNS
   rebinding that swaps an internal IP after the first resolution is caught.
"""

import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse


BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),        # loopback
    ipaddress.ip_network("10.0.0.0/8"),          # private
    ipaddress.ip_network("172.16.0.0/12"),       # private
    ipaddress.ip_network("192.168.0.0/16"),      # private
    ipaddress.ip_network("169.254.0.0/16"),      # link-local / cloud metadata
    ipaddress.ip_network("100.64.0.0/10"),       # carrier-grade NAT (RFC 6598)
    ipaddress.ip_network("0.0.0.0/32"),          # unspecified
    ipaddress.ip_network("::1/128"),             # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),            # IPv6 private
    ipaddress.ip_network("fe80::/10"),           # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),       # IPv4-mapped IPv6 (normalized first)
]

BLOCKED_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::1]",
    "metadata.google.internal",
    "169.254.169.254",  # AWS/GCP/Azure metadata
})

# Max redirect hops an executor may follow while re-validating each hop.
MAX_REDIRECTS = 5


def _normalize_address(addr: str) -> "ipaddress._BaseAddress":
    """Return an ipaddress object, unwrapping IPv4-mapped IPv6 to plain IPv4."""
    ip = ipaddress.ip_address(addr)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def validate_url(url: str) -> Tuple[str, str, int]:
    """
    Validate URL for SSRF safety. Returns (hostname, resolved_ip_str, port).

    Resolves the hostname via `getaddrinfo` and rejects it if ANY resolved
    address falls inside a blocked network (protects against multi-A-record
    setups where a previous single-IP lookup could miss the dangerous one).

    Raises ValueError if the URL is unsafe.
    """
    if not url:
        raise ValueError("URL is required")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme '{parsed.scheme}' not allowed. Use http or https")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")

    # Block known dangerous hosts
    if hostname.lower().lstrip("[").rstrip("]") in BLOCKED_HOSTS:
        raise ValueError(f"URL hostname '{hostname}' is blocked")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Resolve ALL addresses and validate each one (DNS-rebinding resistance:
    # an attacker-controlled DNS answer that mixes a public and an internal
    # address gets caught here).
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    safe_ip: str | None = None
    seen: set[str] = set()
    for info in infos:
        raw = info[4][0]
        if raw in seen:
            continue
        seen.add(raw)
        ip = _normalize_address(raw)
        for network in BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(f"URL resolves to blocked network: {raw}")
        if safe_ip is None:
            safe_ip = str(ip)

    if safe_ip is None:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    return hostname, safe_ip, port