"""Clean-room Obtainium-inspired upstream APK release resolver & fetcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import httpx

ProviderType = Literal["github", "gitlab", "fdroid"]


async def resolve_upstream_release(
    provider: ProviderType,
    identifier: str,
    *,
    timeout_seconds: float = 15.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """Resolve latest APK release metadata from GitHub, GitLab, or F-Droid."""
    client_kwargs: dict[str, Any] = {
        "timeout": timeout_seconds,
        "follow_redirects": True,
        "headers": {"User-Agent": "RAA-SourceFetcher/4.0", "Accept": "application/json"},
    }
    if transport is not None:
        client_kwargs["transport"] = transport

    async with httpx.AsyncClient(**client_kwargs) as client:
        if provider == "github":
            url = f"https://api.github.com/repos/{identifier.strip('/')}/releases/latest"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            apk_assets = [
                a for a in data.get("assets", []) if str(a.get("name", "")).lower().endswith(".apk")
            ]
            download_url = apk_assets[0]["browser_download_url"] if apk_assets else None
            return {
                "provider": "github",
                "identifier": identifier,
                "version": data.get("tag_name") or data.get("name") or "unknown",
                "download_url": download_url,
                "asset_name": apk_assets[0]["name"] if apk_assets else None,
                "release_url": data.get("html_url"),
            }

        if provider == "gitlab":
            encoded = quote(identifier.strip("/"), safe="")
            url = f"https://gitlab.com/api/v4/projects/{encoded}/releases"
            resp = await client.get(url)
            resp.raise_for_status()
            releases = resp.json()
            latest = releases[0] if isinstance(releases, list) and releases else {}
            links = latest.get("assets", {}).get("links", [])
            apk_links = [lnk for lnk in links if str(lnk.get("name", "")).lower().endswith(".apk")]
            download_url = (
                apk_links[0].get("direct_asset_url") or apk_links[0].get("url")
                if apk_links
                else None
            )
            return {
                "provider": "gitlab",
                "identifier": identifier,
                "version": latest.get("tag_name") or latest.get("name") or "unknown",
                "download_url": download_url,
                "asset_name": apk_links[0].get("name") if apk_links else None,
                "release_url": latest.get("_links", {}).get("self"),
            }

        # fdroid
        pkg = identifier.strip()
        url = f"https://f-droid.org/api/v1/packages/{pkg}"
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        packages = data.get("packages", [])
        latest_pkg = packages[0] if isinstance(packages, list) and packages else {}
        version_code = latest_pkg.get("versionCode")
        version_name = latest_pkg.get("versionName") or "unknown"
        download_url = (
            f"https://f-droid.org/repo/{pkg}_{version_code}.apk"
            if version_code is not None
            else None
        )
        return {
            "provider": "fdroid",
            "identifier": pkg,
            "version": version_name,
            "version_code": version_code,
            "download_url": download_url,
            "asset_name": f"{pkg}_{version_code}.apk" if version_code is not None else None,
            "release_url": f"https://f-droid.org/packages/{pkg}/",
        }


def _write_apk_file(dest_path: Path, content: bytes) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(content)
    return dest_path


async def download_upstream_apk(
    download_url: str,
    dest_path: Path,
    *,
    timeout_seconds: float = 60.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Path:
    """Stream-download an APK from a resolved upstream release URL."""
    client_kwargs: dict[str, Any] = {
        "timeout": timeout_seconds,
        "follow_redirects": True,
        "headers": {"User-Agent": "RAA-SourceFetcher/4.0"},
    }
    if transport is not None:
        client_kwargs["transport"] = transport

    async with httpx.AsyncClient(**client_kwargs) as client:
        resp = await client.get(download_url)
        resp.raise_for_status()
        return _write_apk_file(dest_path, resp.content)
