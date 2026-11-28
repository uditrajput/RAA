"""Tests for Phase 2 OSINT email recon (holehe) and clean-room httpx backend crawler."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from raa.errors import PolicyDeniedError
from raa.runtime import Runtime
from raa.services.api.cti_intel import check_leaked_email_intel_async
from raa.services.api.web_recon import crawl_backend_surface


@pytest.mark.asyncio
async def test_email_intel_offline_and_scope_gate(runtime: Runtime) -> None:
    offline = await runtime.invoke(
        "sec_leaked_email_intel",
        {"emails": ["dev@example.com"]},
    )
    assert offline.data["status"] == "EMAIL_INTEL_COMPLETE"
    assert offline.data["mode"] == "offline"

    with pytest.raises(PolicyDeniedError):
        await runtime.invoke(
            "sec_leaked_email_intel",
            {"emails": ["dev@example.com"], "mode": "holehe"},
        )


@pytest.mark.asyncio
async def test_email_intel_holehe_subprocess_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProc:
        async def communicate(self) -> tuple[bytes, bytes]:
            return (b"[+] github.com\n[+] spotify.com\n[-] twitter.com\n", b"")

        def kill(self) -> None:
            return None

        async def wait(self) -> int:
            return 0

    async def _fake_exec(*args: Any, **kwargs: Any) -> _FakeProc:
        del args, kwargs
        return _FakeProc()

    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/holehe" if name == "holehe" else None
    )
    monkeypatch.setattr("asyncio.create_subprocess_exec", _fake_exec)

    res = await check_leaked_email_intel_async(["dev@example.com"], mode="holehe")
    assert res["mode"] == "holehe"
    assert res["findings"][0]["registered_platforms"] == ["github.com", "spotify.com"]


@pytest.mark.asyncio
async def test_backend_recon_scope_and_crawler(runtime: Runtime) -> None:
    project = await runtime.invoke("project_create", {"name": "recon-test"})
    pid = project.data["id"]

    with pytest.raises(PolicyDeniedError):
        await runtime.invoke(
            "api_backend_recon",
            {"project_id": pid, "base_urls": ["https://api.example.com"]},
            profile="api",
        )

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            html = (
                '<script src="/app.js"></script>'
                '<a href="https://cdn.api.example.com/assets">CDN</a>'
            )
            return httpx.Response(200, text=html)
        if request.url.path == "/app.js":
            js = (
                'fetch("/api/v2/users?role=admin");'
                'const bucket = "https://my-app-assets.s3.amazonaws.com/config.json";'
                'const key = "' + "AKIA" + '1234567890ABCDEF";'
            )
            return httpx.Response(200, text=js)
        return httpx.Response(404, text="not found")

    res = await crawl_backend_surface(
        ["https://api.example.com/"],
        max_depth=1,
        max_pages=10,
        transport=httpx.MockTransport(_handler),
    )
    assert res["pages_crawled"] == 2
    assert "https://api.example.com/api/v2/users?role=admin" in res["endpoints"]
    assert "role" in res["query_parameters"]
    assert "cdn.api.example.com" in res["subdomains"]
    assert "https://my-app-assets.s3.amazonaws.com/config.json" in res["s3_buckets"]
    assert res["secret_hits"][0]["kind"] == "aws_access_key"
