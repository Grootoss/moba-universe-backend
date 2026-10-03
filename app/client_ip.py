"""Client IP as nginx sees it. Forwarding headers from the public internet are ignored."""

from __future__ import annotations

import ipaddress

from fastapi import Request


def _parse_ip(value: str) -> str | None:
    raw = value.strip()
    if raw.startswith("[") and "]" in raw:
        raw = raw[1 : raw.index("]")]
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def _trusted_proxy(peer: str) -> bool:
    ip = _parse_ip(peer)
    if ip is None:
        return False
    addr = ipaddress.ip_address(ip)
    return addr.is_private or addr.is_loopback


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else ""
    if _trusted_proxy(peer):
        forwarded = _parse_ip(request.headers.get("x-real-ip", ""))
        if forwarded:
            return forwarded
    return _parse_ip(peer) or "unknown"
