"""Domain Intent Guard for Mobile Inbound Channels.

Enforces that natural language prompts arriving from Telegram or WhatsApp strictly
fall within RAA reverse-engineering, UI reconstruction, offensive security,
toolchain, or status query domains.
"""

from __future__ import annotations

import re
from typing import Any

ALLOWED_DOMAINS: dict[str, list[str]] = {
    "reversing": [
        "decompile",
        "disassemble",
        "extract",
        "jadx",
        "ghidra",
        "symbols",
        "apk",
        "dex",
        "smali",
        "endpoints",
        "strings",
        "manifest",
        "permissions",
        "resources",
        "arsc",
        "axml",
        "inspect",
        "analyze",
        "aot",
        "native",
        "so",
        "elf",
        "unpack",
    ],
    "living_canvas": [
        "ui",
        "compose",
        "jetpack",
        "screen",
        "redesign",
        "living canvas",
        "layout",
        "d-pad",
        "android tv",
        "leanback",
        "view",
        "theme",
        "material3",
        "m3",
        "screendiff",
    ],
    "offensive": [
        "bypass",
        "ssl",
        "pinning",
        "root",
        "frida",
        "hook",
        "patch",
        "rebuild",
        "repackage",
        "cve",
        "vuln",
        "vulnerability",
        "exploit",
        "sign",
        "zipalign",
        "kernelpatch",
        "ring-0",
        "integrity",
        "attestation",
        "play protect",
    ],
    "toolchain": [
        "download",
        "tool",
        "tools",
        "apktool",
        "platform-tools",
        "adb",
        "path",
        "install",
        "delete",
        "storage",
        "reclaim",
        "setup",
        "wizard",
        "version",
        "apkeep",
    ],
    "status": [
        "status",
        "progress",
        "task",
        "job",
        "health",
        "ping",
        "uptime",
        "cadence",
        "help",
        "capabilities",
        "queue",
        "report",
        "how many",
        "count",
        "list",
    ],
}


class DomainIntentGuard:
    """Classifies and filters incoming prompts to guard against prompt injection and out-of-scope requests."""

    def __init__(self, allowed_domains: dict[str, list[str]] | None = None) -> None:
        self.domains = allowed_domains or ALLOWED_DOMAINS

    def classify_intent(self, prompt: str) -> dict[str, Any]:
        cleaned = prompt.strip().lower()
        if not cleaned:
            return {
                "is_allowed": False,
                "domain": "empty",
                "confidence": 0.0,
                "reason": "Prompt is empty.",
                "suggestions": [
                    "Decompile target.apk and extract endpoints",
                    "Convert checkout screen to Jetpack Compose M3",
                    "Bypass SSL pinning on com.wallet and rebuild APK",
                ],
            }

        domain_scores: dict[str, int] = {d: 0 for d in self.domains}
        matched_keywords: dict[str, list[str]] = {d: [] for d in self.domains}

        words = re.findall(r"\w+", cleaned)
        for domain, keywords in self.domains.items():
            for kw in keywords:
                if kw in cleaned or kw in words:
                    domain_scores[domain] += 1
                    matched_keywords[domain].append(kw)

        best_domain = max(domain_scores, key=lambda d: domain_scores[d])
        best_score = domain_scores[best_domain]

        if best_score > 0:
            confidence = min(1.0, 0.4 + (best_score * 0.2))
            return {
                "is_allowed": True,
                "domain": best_domain,
                "confidence": round(confidence, 2),
                "matched_keywords": matched_keywords[best_domain],
                "reason": f"Prompt matches RAA '{best_domain}' domain capability.",
            }

        return {
            "is_allowed": False,
            "domain": "unsupported",
            "confidence": 0.0,
            "reason": "Request does not relate to RAA reverse engineering, UI design, security, or tool management.",
            "suggestions": [
                "Decompile target.apk and extract API endpoints",
                "Convert the checkout screen into Jetpack Compose M3",
                "Bypass SSL pinning on com.wallet and send me the patched APK",
                "Download Apktool and configure its path",
                "What is the progress on current tasks?",
            ],
        }
