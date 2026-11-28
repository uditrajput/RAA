"""Scope constants and the fail-closed policy engine.

A tool declares the scopes it needs. A project grants a set of scopes. The
policy engine allows the call only when every required scope is granted.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from raa.errors import InvalidArgumentsError

PROJECT_READ = "project.read"
PROJECT_WRITE = "project.write"
STATIC_READ = "static.read"
EXPORT_WRITE = "export.write"
EXPORT_RAW = "export.raw"
DYNAMIC_DEVICE = "dynamic.device"
DYNAMIC_INSTRUMENT = "dynamic.instrument"
NETWORK_CAPTURE = "network.capture"
NETWORK_OSINT = "network.osint"
NETWORK_CRAWL = "network.crawl"
NETWORK_FETCH = "network.fetch"
ANDROID_INSTALL = "android.install"
ANDROID_PATCH = "android.patch"
ANDROID_SIGN = "android.sign"
LLM_EXTERNAL = "llm.external"
ADMIN = "admin"

ALL_SCOPES: frozenset[str] = frozenset(
    {
        PROJECT_READ,
        PROJECT_WRITE,
        STATIC_READ,
        EXPORT_WRITE,
        EXPORT_RAW,
        DYNAMIC_DEVICE,
        DYNAMIC_INSTRUMENT,
        NETWORK_CAPTURE,
        NETWORK_OSINT,
        NETWORK_CRAWL,
        NETWORK_FETCH,
        ANDROID_INSTALL,
        ANDROID_PATCH,
        ANDROID_SIGN,
        LLM_EXTERNAL,
        ADMIN,
    }
)

DANGEROUS_SCOPES: frozenset[str] = frozenset(
    {
        EXPORT_RAW,
        DYNAMIC_DEVICE,
        DYNAMIC_INSTRUMENT,
        NETWORK_CAPTURE,
        NETWORK_OSINT,
        NETWORK_CRAWL,
        NETWORK_FETCH,
        ANDROID_INSTALL,
        ANDROID_PATCH,
        ANDROID_SIGN,
        LLM_EXTERNAL,
    }
)

DEFAULT_PROJECT_SCOPES: tuple[str, ...] = (
    PROJECT_READ,
    PROJECT_WRITE,
    STATIC_READ,
    EXPORT_WRITE,
)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    missing: frozenset[str] = frozenset()
    reason: str | None = None


class PolicyEngine:
    """Pure scope evaluation. No I/O and no hidden grants."""

    def evaluate(
        self,
        required: Iterable[str],
        granted: Iterable[str],
    ) -> PolicyDecision:
        required_set = frozenset(required)
        granted_set = frozenset(granted)
        missing = required_set - granted_set
        if missing:
            return PolicyDecision(
                allowed=False,
                missing=missing,
                reason=(
                    "Missing project scope(s): "
                    + ", ".join(sorted(missing))
                    + ". Update the project scopes explicitly before retrying."
                ),
            )
        return PolicyDecision(allowed=True)


def normalize_scopes(values: Iterable[str]) -> list[str]:
    """Validate and de-duplicate scope names while preserving order."""

    normalized: list[str] = []
    unknown: list[str] = []
    for value in values:
        scope = str(value).strip()
        if not scope:
            continue
        if scope not in ALL_SCOPES:
            unknown.append(scope)
            continue
        if scope not in normalized:
            normalized.append(scope)
    if unknown:
        raise InvalidArgumentsError(
            "Unknown scope(s): " + ", ".join(sorted(unknown)),
            hint="Use admin_policy_get to list valid scopes.",
            details={"unknown": sorted(unknown), "valid": sorted(ALL_SCOPES)},
        )
    return normalized
