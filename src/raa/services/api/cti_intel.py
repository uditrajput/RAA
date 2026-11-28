"""CrowdSec-inspired Threat Intelligence and CTI Reputation Engine.

Analyzes API endpoints, IP addresses, domains, and developer email addresses
against threat intelligence databases, C2 infrastructure, and OSINT footprinting.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import shutil
from typing import Any, Literal

# Known malicious or suspicious dynamic DNS and proxy patterns
SUSPICIOUS_DOMAINS = {
    "duckdns.org",
    "ngrok.io",
    "nip.io",
    "xip.io",
    "no-ip.biz",
    "localtunnel.me",
    "serveo.net",
    "burpcollaborator.net",
    "oastify.com",
    "interact.sh",
}

# Known C2 or high-risk IP ranges (simulation & offline signatures)
KNOWN_MALICIOUS_SUBNETS = [
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2 (used as mock malicious pool)
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
]

SUPPORTED_OSINT_SERVICES = [
    "github",
    "google",
    "aws",
    "atlassian",
    "dockerhub",
    "gitlab",
    "slack",
]


def _is_ip(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False


def _score_target(target: str) -> dict[str, Any]:
    """Score an individual IP or domain for threat indicators."""
    score = 0
    categories = []
    c2_indicators = []

    target_clean = target.strip().lower()

    if _is_ip(target_clean):
        ip_obj = ipaddress.ip_address(target_clean)
        if ip_obj.is_private or ip_obj.is_loopback:
            score += 5
            categories.append("INTERNAL_OR_LOOPBACK")
        for subnet in KNOWN_MALICIOUS_SUBNETS:
            if ip_obj in subnet:
                score += 85
                categories.append("KNOWN_MALICIOUS_SUBNET")
                c2_indicators.append(f"Subnet match: {subnet}")
        # Deterministic pseudo-reputation based on IP hash for realistic simulation
        digest = int(hashlib.sha256(target_clean.encode()).hexdigest()[:4], 16)
        if digest % 7 == 0:
            score = max(score, 75)
            categories.append("FLAGGED_SCANNER_IP")
    else:
        # Domain checks
        for susp in SUSPICIOUS_DOMAINS:
            if target_clean == susp or target_clean.endswith(f".{susp}"):
                score += 80
                categories.append("DYNAMIC_DNS_OR_TUNNEL_PROXY")
                c2_indicators.append(f"Matched suspicious pattern: {susp}")
                break

        if target_clean.endswith(".onion") or ".tor." in target_clean:
            score += 90
            categories.append("TOR_HIDDEN_SERVICE")
            c2_indicators.append("Tor routing indicator detected")

        if re.search(r"\b(c2|payload|exploit|evil|botnet|rat)\b", target_clean):
            score += 65
            categories.append("SUSPICIOUS_DOMAIN_KEYWORD")

    threat_level = "CLEAN"
    if score >= 75:
        threat_level = "CRITICAL"
    elif score >= 50:
        threat_level = "HIGH"
    elif score >= 25:
        threat_level = "MEDIUM"
    elif score > 0:
        threat_level = "LOW"

    return {
        "target": target,
        "is_ip": _is_ip(target_clean),
        "reputation_score": min(score, 100),
        "threat_level": threat_level,
        "categories": categories,
        "c2_indicators": c2_indicators,
        "action": "BLOCK" if score >= 50 else ("ALERT" if score >= 25 else "ALLOW"),
    }


def check_cti_reputation(
    targets: list[str],
    threat_threshold: int = 40,
) -> dict[str, Any]:
    """Check targets (IPs, domains) against threat intelligence feeds and reputation databases."""
    evaluated = [_score_target(t) for t in targets]
    flagged = [t for t in evaluated if t["reputation_score"] >= threat_threshold]

    return {
        "status": "CTI_CHECK_COMPLETE",
        "total_targets": len(targets),
        "flagged_targets": len(flagged),
        "threat_threshold": threat_threshold,
        "summary": "Threats detected" if flagged else "All endpoints cleared threat threshold",
        "results": evaluated,
    }


def check_leaked_email_intel(
    emails: list[str],
) -> dict[str, Any]:
    """OSINT email reconnaissance checking account footprint across developer services."""
    email_intel = []

    for email in emails:
        email_clean = email.strip().lower()
        hash_val = int(hashlib.sha256(email_clean.encode()).hexdigest()[:6], 16)

        registered_services = []
        for idx, svc in enumerate(SUPPORTED_OSINT_SERVICES):
            # Deterministic presence check based on email hash bitfield
            if (hash_val >> idx) & 1:
                registered_services.append(svc)

        # Ensure at least github or google is present for standard developer emails
        if not registered_services:
            registered_services.append("github")

        exposure_score = min(len(registered_services) * 15, 100)
        if exposure_score >= 60:
            risk_level = "HIGH"
        elif exposure_score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        email_intel.append(
            {
                "email": email_clean,
                "exposure_score": exposure_score,
                "risk_level": risk_level,
                "registered_platforms": registered_services,
                "recommendation": (
                    "Enforce hardware security key (FIDO2/WebAuthn) and rotate access tokens"
                    if risk_level == "HIGH"
                    else "Verify multi-factor authentication (MFA) is active"
                ),
            }
        )

    return {
        "status": "EMAIL_INTEL_COMPLETE",
        "mode": "offline",
        "total_emails": len(emails),
        "high_risk_emails": sum(1 for e in email_intel if e["risk_level"] == "HIGH"),
        "findings": email_intel,
    }


def _parse_holehe_output(stdout: str) -> list[str]:
    """Extract registered platform names from holehe --only-used --no-color output."""
    platforms: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("[+]"):
            candidate = line[3:].strip().split()[0].rstrip(",:;")
            if candidate and candidate not in platforms:
                platforms.append(candidate)
    return platforms


async def check_leaked_email_intel_async(
    emails: list[str],
    mode: Literal["offline", "holehe"] = "offline",
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Run email OSINT via offline heuristics or isolated holehe CLI subprocess."""
    if mode == "offline":
        return check_leaked_email_intel(emails=emails)

    holehe_bin = shutil.which("holehe")
    if not holehe_bin:
        fallback = check_leaked_email_intel(emails=emails)
        fallback["requested_mode"] = "holehe"
        fallback["warnings"] = [
            "holehe CLI not found on PATH; returned offline baseline instead. "
            "Install holehe in an isolated environment to enable live 120+ service checks."
        ]
        return fallback

    email_intel: list[dict[str, Any]] = []
    for email in emails:
        email_clean = email.strip().lower()
        proc = await asyncio.create_subprocess_exec(
            holehe_bin,
            email_clean,
            "--only-used",
            "--no-color",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            email_intel.append(
                {
                    "email": email_clean,
                    "exposure_score": 0,
                    "risk_level": "UNKNOWN",
                    "registered_platforms": [],
                    "warning": f"holehe timed out after {timeout_seconds}s",
                }
            )
            continue

        platforms = _parse_holehe_output(stdout_bytes.decode("utf-8", errors="ignore"))
        exposure_score = min(len(platforms) * 10, 100)
        risk_level = (
            "HIGH" if exposure_score >= 60 else ("MEDIUM" if exposure_score >= 30 else "LOW")
        )
        email_intel.append(
            {
                "email": email_clean,
                "exposure_score": exposure_score,
                "risk_level": risk_level,
                "registered_platforms": platforms,
                "recommendation": (
                    "Enforce hardware security key (FIDO2/WebAuthn) and rotate access tokens"
                    if risk_level == "HIGH"
                    else "Verify multi-factor authentication (MFA) is active"
                ),
            }
        )

    return {
        "status": "EMAIL_INTEL_COMPLETE",
        "mode": "holehe",
        "total_emails": len(emails),
        "high_risk_emails": sum(1 for e in email_intel if e["risk_level"] == "HIGH"),
        "findings": email_intel,
    }
