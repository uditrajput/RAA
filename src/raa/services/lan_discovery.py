"""Multi-protocol LAN device discovery (mDNS, SSDP/UPnP, Reverse DNS, NetBIOS, HTTP)."""

from __future__ import annotations

import logging
import os
import re
import socket
import subprocess
import time
import urllib.request
from contextlib import suppress

logger = logging.getLogger(__name__)


def _encode_dns_name(name: str) -> bytes:
    return (
        b"".join(bytes([len(p)]) + p.encode("ascii", errors="ignore") for p in name.split(".") if p)
        + b"\x00"
    )


def _decode_dns_labels(data: bytes, offset: int) -> tuple[list[str], int]:
    parts: list[str] = []
    pos = offset
    jumped = False
    end_offset = offset
    seen = 0
    while pos < len(data) and seen < 20:
        length = data[pos]
        if length == 0:
            if not jumped:
                end_offset = pos + 1
            break
        if (length & 0xC0) == 0xC0:
            if pos + 1 >= len(data):
                break
            if not jumped:
                end_offset = pos + 2
            pos = ((length & 0x3F) << 8) | data[pos + 1]
            jumped = True
            seen += 1
            continue
        pos += 1
        if pos + length > len(data):
            break
        parts.append(data[pos : pos + length].decode("utf-8", errors="ignore"))
        pos += length
    return parts, end_offset


def mdns_ptr_lookup(ip_addr: str, timeout: float = 0.35) -> str:
    """Query unicast mDNS (UDP 5353) for the device's .local hostname."""
    try:
        parts = ip_addr.split(".")
        if len(parts) != 4:
            return ""
        qname = _encode_dns_name(".".join([*reversed(parts), "in-addr", "arpa"]))
        packet = b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00" + qname + b"\x00\x0c\x00\x01"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (ip_addr, 5353))
            data, _ = sock.recvfrom(1024)
        if len(data) <= len(packet):
            return ""
        idx = 12
        _, idx = _decode_dns_labels(data, idx)
        idx += 4  # QTYPE + QCLASS
        if idx >= len(data):
            return ""
        _, idx = _decode_dns_labels(data, idx)
        if idx + 10 > len(data):
            return ""
        rdlength = int.from_bytes(data[idx + 8 : idx + 10], "big")
        rdata_idx = idx + 10
        if rdata_idx + rdlength > len(data):
            return ""
        name_parts, _ = _decode_dns_labels(data, rdata_idx)
        if name_parts:
            host = name_parts[0].strip()
            if host and host.lower() != "local":
                return host.replace("-", " ") if ".local" in ".".join(name_parts).lower() else host
    except Exception as exc:
        logger.debug("mDNS PTR lookup failed for %s: %s", ip_addr, exc)
    return ""


def discover_mdns_hosts(timeout: float = 0.7) -> dict[str, dict[str, str]]:
    """Broadcast mDNS service queries (Fing/Bonjour pattern) and map responder IP -> name/model."""
    services = (
        "_services._dns-sd._udp.local",
        "_airplay._tcp.local",
        "_companion-link._tcp.local",
        "_googlecast._tcp.local",
        "_adb-tls-connect._tcp.local",
        "_workstation._tcp.local",
    )
    results: dict[str, dict[str, str]] = {}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.25)
            for svc in services:
                pkt = (
                    b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                    + _encode_dns_name(svc)
                    + b"\x00\x0c\x00\x01"
                )
                with suppress(Exception):
                    sock.sendto(pkt, ("224.0.0.251", 5353))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    data, addr = sock.recvfrom(4096)
                except Exception:
                    break
                ip = addr[0]
                ascii_str = "".join(chr(b) if 32 <= b < 127 else "\n" for b in data)
                model_m = re.search(r"(?:model|md|fn)=([^\r\n\x00]{2,48})", ascii_str)
                local_m = re.search(r"([A-Za-z0-9][A-Za-z0-9 _-]{1,40})\.local", ascii_str)
                entry = results.setdefault(ip, {})
                if model_m and not entry.get("model"):
                    entry["model"] = model_m.group(1).strip()
                if local_m and not entry.get("name"):
                    entry["name"] = local_m.group(1).strip().replace("-", " ")
    except Exception as exc:
        logger.debug("mDNS discovery failed: %s", exc)
    return results


def _fetch_upnp_xml_info(location_url: str) -> dict[str, str]:
    if not location_url.startswith(("http://", "https://")):
        return {}
    try:
        req = urllib.request.Request(location_url, headers={"User-Agent": "RAA-LAN-Scanner/4.0"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=0.8) as resp:  # noqa: S310
            xml_bytes = resp.read(32768)
        xml_text = xml_bytes.decode("utf-8", errors="ignore")
        info: dict[str, str] = {}
        for tag, key in (
            ("friendlyName", "name"),
            ("modelName", "model"),
            ("manufacturer", "manufacturer"),
        ):
            m = re.search(rf"<(?:\w+:)?{tag}[^>]*>([^<]+)</(?:\w+:)?{tag}>", xml_text)
            if m and m.group(1).strip():
                info[key] = m.group(1).strip()
        return info
    except Exception:
        return {}


def discover_ssdp_hosts(timeout: float = 0.7) -> dict[str, dict[str, str]]:
    """Send SSDP M-SEARCH (UPnP) and parse device XML friendlyName/modelName/manufacturer."""
    results: dict[str, dict[str, str]] = {}
    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 1\r\n"
        "ST: ssdp:all\r\n\r\n"
    ).encode("ascii")
    locations: dict[str, str] = {}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.25)
            sock.sendto(msg, ("239.255.255.250", 1900))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    data, addr = sock.recvfrom(4096)
                except Exception:
                    break
                ip = addr[0]
                text = data.decode("utf-8", errors="ignore")
                loc_m = re.search(r"(?im)^LOCATION:\s*(\S+)", text)
                srv_m = re.search(r"(?im)^SERVER:\s*(.+)$", text)
                if loc_m and ip not in locations:
                    locations[ip] = loc_m.group(1).strip()
                if srv_m:
                    results.setdefault(ip, {})["server"] = srv_m.group(1).strip()
    except Exception as exc:
        logger.debug("SSDP discovery failed: %s", exc)
    for ip, loc in locations.items():
        xml_info = _fetch_upnp_xml_info(loc)
        if xml_info:
            results.setdefault(ip, {}).update(xml_info)
    return results


def probe_http_device_name(ip_addr: str, timeout: float = 0.25) -> str:
    """Probe HTTP management title/Server header (Advanced IP Scanner pattern) on common ports."""
    bad_titles = (
        "index",
        "login",
        "welcome",
        "home",
        "redirect",
        "moved",
        "301 ",
        "302 ",
        "307 ",
        "308 ",
        "400 ",
        "401 ",
        "403 ",
        "404 ",
        "500 ",
        "502 ",
        "503 ",
        "bad request",
        "not found",
        "forbidden",
        "unauthorized",
    )
    for port in (80, 8080, 8008):
        try:
            url = f"http://{ip_addr}:{port}/" if port != 80 else f"http://{ip_addr}/"
            req = urllib.request.Request(url, headers={"User-Agent": "RAA-LAN-Scanner/4.0"})  # noqa: S310
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  # noqa: S310
                raw = resp.read(8192).decode("utf-8", errors="ignore")
                srv = str(resp.headers.get("Server") or "").strip()
            title_m = re.search(r"(?is)<title[^>]*>\s*([^<]{2,60}?)\s*</title>", raw)
            if title_m:
                title = title_m.group(1).strip()
                t_low = title.lower()
                if title and not any(b in t_low for b in bad_titles):
                    return title
            if srv and srv.lower() not in {"nginx", "apache", "lighttpd", "httpd"}:
                return srv
        except Exception as exc:
            logger.debug("HTTP probe failed for %s:%s: %s", ip_addr, port, exc)
            continue
    return ""


_OUI_CACHE: dict[str, str] = {}


def lookup_oui_vendor(mac_addr: str, timeout: float = 0.5) -> str:
    """Resolve non-randomized MAC OUI vendor via api.macvendors.com with in-memory cache."""
    clean = mac_addr.strip().lower().replace("-", ":")
    if len(clean) < 8:
        return ""
    if len(clean) >= 2 and clean[1] in {"2", "6", "a", "e"}:
        return ""
    oui = clean[:8]
    if oui in _OUI_CACHE:
        return _OUI_CACHE[oui]
    try:
        req = urllib.request.Request(
            f"https://api.macvendors.com/{oui}",
            headers={"User-Agent": "RAA-LAN-Scanner/4.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            vendor = resp.read(256).decode("utf-8", errors="ignore").strip()
        if vendor and "not found" not in vendor.lower() and "errors" not in vendor.lower():
            _OUI_CACHE[oui] = vendor[:40]
            return _OUI_CACHE[oui]
    except Exception as exc:
        logger.debug("SSDP discovery failed: %s", exc)
    _OUI_CACHE[oui] = ""
    return ""


def detect_ttl_os(ip_addr: str, timeout_ms: int = 300) -> str:
    """Use ICMP ping TTL fingerprinting (128=Windows PC, <=64=Mobile/Linux/iOS)."""
    try:
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
        )
        cmd = (
            ["ping", "-n", "1", "-w", str(timeout_ms), ip_addr]
            if os.name == "nt"
            else ["ping", "-c", "1", "-W", "1", ip_addr]
        )
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=1.0, creationflags=creationflags
        )
        m = re.search(r"ttl=(\d+)", proc.stdout, re.IGNORECASE)
        if m:
            ttl = int(m.group(1))
            if ttl > 64:
                return "windows"
            return "mobile_unix"
    except Exception as exc:
        logger.debug("mDNS PTR lookup failed for %s: %s", ip_addr, exc)
    return ""


def resolve_lan_device_name(
    ip_addr: str,
    fallback: str,
    *,
    mdns_map: dict[str, dict[str, str]] | None = None,
    ssdp_map: dict[str, dict[str, str]] | None = None,
    is_gateway: bool = False,
) -> tuple[str, str]:
    """Resolve friendly device name & vendor via Reverse DNS, mDNS, SSDP/UPnP, NetBIOS, and HTTP."""
    ssdp_info = (ssdp_map or {}).get(ip_addr, {})
    mdns_info = (mdns_map or {}).get(ip_addr, {})
    detected_vendor = ssdp_info.get("manufacturer") or ""

    # 1. mDNS multicast model/name
    if mdns_info.get("model"):
        return mdns_info["model"], detected_vendor
    if mdns_info.get("name"):
        return mdns_info["name"], detected_vendor

    # 2. SSDP / UPnP XML friendlyName / modelName
    if ssdp_info.get("name"):
        return ssdp_info["name"], detected_vendor
    if ssdp_info.get("model"):
        return ssdp_info["model"], detected_vendor

    # 3. Reverse DNS
    try:
        resolved, _, _ = socket.gethostbyaddr(ip_addr)
        if resolved and resolved != ip_addr:
            return resolved.split(".")[0], detected_vendor
    except Exception as exc:
        logger.debug("SSDP discovery failed: %s", exc)

    # 4. Unicast mDNS PTR
    ptr_name = mdns_ptr_lookup(ip_addr)
    if ptr_name:
        return ptr_name, detected_vendor

    # 5. Windows NetBIOS (nbtstat -A)
    if os.name == "nt" and not is_gateway:
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            nb = subprocess.run(
                ["nbtstat", "-A", ip_addr],
                capture_output=True,
                text=True,
                timeout=0.5,
                creationflags=creationflags,
            )
            for line in nb.stdout.splitlines():
                m_nb = re.match(r"^\s*([A-Za-z0-9_-]{2,20})\s+<00>\s+UNIQUE", line)
                if m_nb:
                    return m_nb.group(1), detected_vendor
        except Exception as exc:
            logger.debug("NetBIOS lookup failed for %s: %s", ip_addr, exc)

    # 6. HTTP title / Server banner (routers, smart devices)
    http_name = probe_http_device_name(ip_addr)
    if http_name:
        return http_name, detected_vendor

    return fallback, detected_vendor
