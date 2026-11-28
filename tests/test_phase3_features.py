"""Tests for Phase 3 features: upstream APK fetch, UI tree-screenshot fusion, and Hoppscotch export."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from raa.errors import PolicyDeniedError
from raa.runtime import Runtime
from raa.services.android.source_fetcher import download_upstream_apk, resolve_upstream_release


@pytest.mark.asyncio
async def test_apk_fetch_upstream_scope_and_resolvers(
    runtime: Runtime,
    tmp_path: Path,
) -> None:
    project = await runtime.invoke("project_create", {"name": "upstream-test"})
    pid = project.data["id"]

    with pytest.raises(PolicyDeniedError):
        await runtime.invoke(
            "apk_fetch_upstream",
            {"project_id": pid, "provider": "github", "identifier": "owner/app"},
        )

    def _handler(request: httpx.Request) -> httpx.Response:
        if "api.github.com" in request.url.host:
            return httpx.Response(
                200,
                json={
                    "tag_name": "v1.2.3",
                    "html_url": "https://github.com/owner/app/releases/tag/v1.2.3",
                    "assets": [
                        {
                            "name": "app-release.apk",
                            "browser_download_url": "https://cdn.example.com/app-release.apk",
                        }
                    ],
                },
            )
        if "f-droid.org" in request.url.host:
            return httpx.Response(
                200,
                json={"packages": [{"versionName": "2.0.0", "versionCode": 200}]},
            )
        if request.url.host == "cdn.example.com":
            return httpx.Response(200, content=b"PK\x03\x04fakeapk")
        return httpx.Response(404)

    transport = httpx.MockTransport(_handler)
    gh = await resolve_upstream_release("github", "owner/app", transport=transport)
    assert gh["version"] == "v1.2.3"
    assert gh["download_url"] == "https://cdn.example.com/app-release.apk"

    fd = await resolve_upstream_release("fdroid", "org.example.app", transport=transport)
    assert fd["version"] == "2.0.0"
    assert fd["download_url"] == "https://f-droid.org/repo/org.example.app_200.apk"

    dest = tmp_path / "app-release.apk"
    await download_upstream_apk(gh["download_url"], dest, transport=transport)
    assert dest.read_bytes() == b"PK\x03\x04fakeapk"


@pytest.mark.asyncio
async def test_api_export_hoppscotch(runtime: Runtime) -> None:
    project = await runtime.invoke("project_create", {"name": "hopp-test"})
    pid = project.data["id"]

    res = await runtime.invoke(
        "api_export_hoppscotch",
        {"project_id": pid, "collection_name": "MobileAPI"},
        profile="api",
    )
    parsed = json.loads(res.data["collection_json"])
    assert parsed["v"] == 2
    assert parsed["name"] == "MobileAPI"
    assert len(parsed["requests"]) == 3
    assert Path(res.data["export_path"]).exists()


@pytest.mark.asyncio
async def test_ui_tree_screenshot_fuse(runtime: Runtime) -> None:
    xml = (
        '<hierarchy rotation="0">'
        '<node class="android.widget.Button" text="Sign In" '
        'resource-id="com.app:id/btn_login" clickable="true" bounds="[0,100][1080,300]" />'
        "</hierarchy>"
    )
    res = await runtime.invoke(
        "ui_tree_screenshot_fuse",
        {
            "hierarchy_xml": xml,
            "screen_width": 1080,
            "screen_height": 2400,
            "screenshot_path": "screen.png",
        },
        profile="ui",
    )
    assert res.data["fused_element_count"] == 1
    el = res.data["fused_elements"][0]
    assert el["center_px"] == {"x": 540, "y": 200}
    assert el["normalized_box_1000"] == [0, 42, 1000, 125]
