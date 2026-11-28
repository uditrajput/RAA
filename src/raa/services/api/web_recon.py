"""Clean-room async backend web & JS endpoint reconnaissance crawler using httpx."""

from __future__ import annotations

import re
from collections import deque
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

_LINK_RE = re.compile(r"""(?:href|src|action)=["']([^"'#]+)["']""", re.IGNORECASE)
_JS_ENDPOINT_RE = re.compile(
    r"""["']((?:https?://[^"'\s]+|/(?:api|v[0-9]+|graphql|auth|oauth)[^"'\s]*))["']""",
    re.IGNORECASE,
)
_S3_BUCKET_RE = re.compile(
    r"""https?://(?:[a-z0-9.-]+\.)?s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com(?:/[^\s"'<>]+)?""",
    re.IGNORECASE,
)
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,48}\b")),
)


async def crawl_backend_surface(
    base_urls: list[str],
    *,
    max_depth: int = 2,
    max_pages: int = 25,
    timeout_seconds: float = 15.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """Crawl extracted app backend URLs to harvest API endpoints, subdomains, S3 buckets, and keys."""
    allowed_hosts: set[str] = set()
    queue: deque[tuple[str, int]] = deque()
    for raw_url in base_urls:
        parsed = urlparse(raw_url.strip())
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            allowed_hosts.add(parsed.netloc.lower())
            queue.append((raw_url.strip(), 0))

    visited: set[str] = set()
    discovered_endpoints: set[str] = set()
    discovered_params: set[str] = set()
    discovered_subdomains: set[str] = set()
    discovered_s3_buckets: set[str] = set()
    secret_hits: list[dict[str, str]] = []

    client_kwargs: dict[str, Any] = {
        "timeout": timeout_seconds,
        "follow_redirects": True,
        "headers": {"User-Agent": "RAA-WebRecon/4.0"},
    }
    if transport is not None:
        client_kwargs["transport"] = transport

    async with httpx.AsyncClient(**client_kwargs) as client:
        while queue and len(visited) < max_pages:
            url, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            try:
                resp = await client.get(url)
            except httpx.HTTPError:
                continue

            body = resp.text
            for s3_match in _S3_BUCKET_RE.findall(body):
                discovered_s3_buckets.add(s3_match)

            for secret_kind, pattern in _SECRET_PATTERNS:
                for match in pattern.findall(body):
                    secret_hits.append(
                        {"kind": secret_kind, "source_url": url, "redacted": f"{match[:6]}..."}
                    )

            for endpoint in _JS_ENDPOINT_RE.findall(body):
                resolved_ep = urljoin(url, endpoint)
                discovered_endpoints.add(resolved_ep)
                ep_parsed = urlparse(resolved_ep)
                if ep_parsed.query:
                    for part in ep_parsed.query.split("&"):
                        key = part.split("=", 1)[0].strip()
                        if key:
                            discovered_params.add(key)

            if depth < max_depth:
                for link in _LINK_RE.findall(body):
                    next_url = urljoin(url, link)
                    next_parsed = urlparse(next_url)
                    host = next_parsed.netloc.lower()
                    if next_parsed.scheme not in {"http", "https"} or not host:
                        continue
                    if host in allowed_hosts:
                        if next_url not in visited:
                            queue.append((next_url, depth + 1))
                    elif any(host.endswith(f".{root}") for root in allowed_hosts):
                        discovered_subdomains.add(host)

    return {
        "status": "BACKEND_RECON_COMPLETE",
        "pages_crawled": len(visited),
        "endpoints": sorted(discovered_endpoints),
        "query_parameters": sorted(discovered_params),
        "subdomains": sorted(discovered_subdomains),
        "s3_buckets": sorted(discovered_s3_buckets),
        "secret_hits": secret_hits,
    }
