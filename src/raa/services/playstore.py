"""Google Play Store app metadata lookup and AVD/Play Store downloader."""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

import httpx

from raa.config import Settings
from raa.domain.models import Authority, Confidence, Representation
from raa.errors import EngineUnavailableError, InvalidArgumentsError, InvalidArtifactError
from raa.services.artifacts import ArtifactService
from raa.services.evidence import EvidenceService
from raa.services.workspace import Workspace

PlayStoreProvider = Literal["auto", "avd", "adb", "apkeep", "gplaycli"]
ApkeepSource = Literal["google-play", "apk-pure", "f-droid", "huawei-app-gallery"]

_PACKAGE_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")
_LOCALE_CODE_RE = re.compile(r"^[a-zA-Z]{2,3}([_-][a-zA-Z0-9]{2,4})?$")
_META_TAG_RE = re.compile(
    r'<meta\s+[^>]*?(?:name|property)=["\']([^"\']+)["\'][^>]*?content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
_NODE_TAG_RE = re.compile(r"<node\b([^>]+?)/?>", re.IGNORECASE | re.DOTALL)
_ATTR_RE = re.compile(r'([a-zA-Z0-9_:-]+)\s*=\s*"([^"]*)"')
_ARTIFACT_EXTS = (".apk", ".apks", ".xapk", ".aab")


def parse_play_package_id(package_or_url: str) -> str:
    """Extract and validate an Android package ID from a raw ID or Play Store URL."""
    raw = package_or_url.strip()
    if not raw:
        raise InvalidArgumentsError("Package ID or Play Store URL must not be empty.")

    candidate = raw
    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        if host != "play.google.com":
            raise InvalidArgumentsError(
                f"Unsupported Play Store host: {parsed.netloc}",
                hint="Provide an Android package ID (e.g. com.example.app) or a play.google.com URL.",
            )
        query_ids = parse_qs(parsed.query).get("id")
        if not query_ids or not query_ids[0].strip():
            raise InvalidArgumentsError(
                "Play Store URL is missing the 'id' query parameter.",
                hint="Expected a URL like https://play.google.com/store/apps/details?id=com.example.app.",
            )
        candidate = query_ids[0].strip()

    if not _PACKAGE_ID_RE.fullmatch(candidate):
        raise InvalidArgumentsError(
            f"Invalid Android package ID: {candidate}",
            hint="Use reverse-domain notation such as 'com.example.app'.",
        )
    return candidate


def _validate_locale(value: str, field: str) -> str:
    cleaned = value.strip()
    if not _LOCALE_CODE_RE.fullmatch(cleaned):
        raise InvalidArgumentsError(f"Invalid {field} code: {value}")
    return cleaned


def _find_install_button_center(xml_text: str) -> tuple[int, int] | None:
    """Locate the center coordinates of a Play Store 'Install'/'Update' button in UIAutomator XML."""
    for node_attrs in _NODE_TAG_RE.findall(xml_text):
        attrs = {key: html.unescape(val) for key, val in _ATTR_RE.findall(node_attrs)}
        label = (attrs.get("text") or attrs.get("content-desc") or "").strip().lower()
        if label not in {"install", "update"}:
            continue
        if attrs.get("enabled", "true").lower() == "false":
            continue
        match = _BOUNDS_RE.fullmatch(attrs.get("bounds", "").strip())
        if not match:
            continue
        x1, y1, x2, y2 = (int(group) for group in match.groups())
        return (x1 + x2) // 2, (y1 + y2) // 2
    return None


class PlayStoreService:
    """Fetches public Play Store metadata and downloads apps via AVD Manager / Play Store."""

    def __init__(
        self,
        *,
        settings: Settings,
        workspace: Workspace,
        artifacts: ArtifactService,
        evidence: EvidenceService,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.artifacts = artifacts
        self.evidence = evidence

    def fetch_app_info(
        self,
        package_or_url: str,
        *,
        lang: str = "en",
        country: str = "us",
    ) -> dict[str, Any]:
        """Fetch public metadata for an app from its Google Play Store web listing."""
        package_id = parse_play_package_id(package_or_url)
        hl = _validate_locale(lang, "language")
        gl = _validate_locale(country, "country")
        store_url = f"https://play.google.com/store/apps/details?id={package_id}&hl={hl}&gl={gl}"

        try:
            response = httpx.get(
                store_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; RAA/4.0)"},
                follow_redirects=True,
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            raise EngineUnavailableError(
                f"Failed to reach Google Play Store listing for {package_id}: {exc}",
                hint="Check network connectivity or proxy settings.",
            ) from exc

        if response.status_code == 404:
            raise InvalidArgumentsError(
                f"App not found on Google Play Store: {package_id}",
                hint="Verify the package ID and country/region availability.",
                details={"package_id": package_id, "status_code": 404},
            )
        if response.status_code >= 400:
            raise EngineUnavailableError(
                f"Google Play Store returned HTTP {response.status_code} for {package_id}.",
                details={"package_id": package_id, "status_code": response.status_code},
            )

        body = response.text
        meta: dict[str, str] = {}
        for key, value in _META_TAG_RE.findall(body):
            meta.setdefault(key.lower(), html.unescape(value).strip())

        title_match = _TITLE_RE.search(body)
        page_title = html.unescape(title_match.group(1)).strip() if title_match else ""
        app_title = (
            meta.get("og:title") or page_title.removesuffix(" - Apps on Google Play").strip()
        )

        return {
            "package_id": package_id,
            "store_url": store_url,
            "title": app_title or package_id,
            "description": meta.get("og:description") or meta.get("description") or "",
            "icon_url": meta.get("og:image"),
            "language": hl,
            "country": gl,
        }

    def download_app(
        self,
        package_or_url: str,
        *,
        project_id: str | None = None,
        provider: PlayStoreProvider = "auto",
        avd_name: str | None = None,
        headless: bool = False,
        boot_timeout_seconds: float = 120.0,
        install_timeout_seconds: float = 180.0,
        auto_tap_install: bool = True,
        version_code: int | None = None,
        split_apk: bool = False,
        device_serial: str | None = None,
        email: str | None = None,
        aas_token: str | None = None,
        oauth_token: str | None = None,
        apkeep_source: ApkeepSource = "google-play",
        auto_ingest: bool = True,
    ) -> dict[str, Any]:
        """Download an app from Google Play (via AVD Manager Play Store or fallback) and optionally ingest it."""
        package_id = parse_play_package_id(package_or_url)
        if auto_ingest and not project_id:
            raise InvalidArgumentsError(
                "project_id is required when auto_ingest is enabled.",
                hint="Pass project_id or set auto_ingest=False to stage the download only.",
            )

        staging_dir = self.workspace.tmp_dir / "playstore" / package_id
        staging_dir.mkdir(parents=True, exist_ok=True)

        selected = self._resolve_provider(
            provider=provider,
            package_id=package_id,
            device_serial=device_serial,
            avd_name=avd_name,
        )

        if selected == "avd":
            downloaded_path, extra = self._download_via_avd_playstore(
                package_id=package_id,
                staging_dir=staging_dir,
                avd_name=avd_name,
                device_serial=device_serial,
                headless=headless,
                boot_timeout_seconds=boot_timeout_seconds,
                install_timeout_seconds=install_timeout_seconds,
                auto_tap_install=auto_tap_install,
            )
        elif selected == "adb":
            downloaded_path, extra = self._download_via_adb(
                package_id=package_id,
                staging_dir=staging_dir,
                device_serial=device_serial,
            )
        elif selected == "apkeep":
            downloaded_path, extra = self._download_via_apkeep(
                package_id=package_id,
                staging_dir=staging_dir,
                source=apkeep_source,
                version_code=version_code,
                split_apk=split_apk,
                email=email,
                aas_token=aas_token,
                oauth_token=oauth_token,
            )
        else:
            downloaded_path, extra = self._download_via_gplaycli(
                package_id=package_id,
                staging_dir=staging_dir,
            )

        result: dict[str, Any] = {
            "package_id": package_id,
            "provider": selected,
            "downloaded_path": str(downloaded_path),
            "filename": downloaded_path.name,
            "size_bytes": downloaded_path.stat().st_size,
            **extra,
        }

        if project_id and auto_ingest:
            ingested = self.artifacts.ingest_path(project_id, str(downloaded_path))
            dl_evidence = self.evidence.add(
                project_id=project_id,
                artifact_id=ingested.artifact.id,
                kind="playstore.download",
                summary=f"Downloaded {package_id} via {selected}",
                payload={
                    "package_id": package_id,
                    "provider": selected,
                    "filename": downloaded_path.name,
                    "sha256": ingested.artifact.sha256,
                    **extra,
                },
                source_tool="playstore_download_app",
                authority=Authority.SHIPPED_ARTIFACT,
                representation=Representation.ORIGINAL,
                confidence=Confidence.OBSERVED,
            )
            result["ingested"] = True
            result["artifact"] = ingested.artifact.model_dump(mode="json")
            result["evidence_ids"] = [rec.id for rec in ingested.evidence] + [dl_evidence.id]
        else:
            result["ingested"] = False
            result["evidence_ids"] = []

        return result

    def _resolve_sdk_binary(self, name: str) -> str | None:
        direct = shutil.which(name)
        if direct:
            return direct

        ext = ".exe" if os.name == "nt" and name in {"adb", "emulator"} else ""
        bat_ext = ".bat" if os.name == "nt" and name == "avdmanager" else ""
        sdk_roots = [
            os.environ.get("ANDROID_HOME"),
            os.environ.get("ANDROID_SDK_ROOT"),
        ]
        subpaths = {
            "adb": [Path("platform-tools") / f"adb{ext}"],
            "emulator": [Path("emulator") / f"emulator{ext}"],
            "avdmanager": [
                Path("cmdline-tools") / "latest" / "bin" / f"avdmanager{bat_ext}",
                Path("tools") / "bin" / f"avdmanager{bat_ext}",
            ],
        }
        for root in sdk_roots:
            if not root:
                continue
            base = Path(root).expanduser()
            for rel in subpaths.get(name, []):
                candidate = base / rel
                if candidate.is_file():
                    return str(candidate)
        return None

    def _resolve_provider(
        self,
        *,
        provider: PlayStoreProvider,
        package_id: str,
        device_serial: str | None,
        avd_name: str | None,
    ) -> Literal["avd", "adb", "apkeep", "gplaycli"]:
        if provider == "avd":
            if not self._resolve_sdk_binary("adb"):
                raise EngineUnavailableError(
                    "Android SDK 'adb' is required for AVD Play Store downloads.",
                    hint=self._provider_install_hint("avd"),
                )
            return "avd"
        if provider != "auto":
            binary = (
                self._resolve_sdk_binary(provider) if provider == "adb" else shutil.which(provider)
            )
            if binary is None:
                raise EngineUnavailableError(
                    f"Requested Play Store provider '{provider}' is not installed on PATH.",
                    hint=self._provider_install_hint(provider),
                )
            return provider

        adb_bin = self._resolve_sdk_binary("adb")
        if adb_bin:
            running_emulators = self._list_running_emulators(adb_bin)
            if avd_name or running_emulators or self._resolve_sdk_binary("emulator"):
                return "avd"
            if self._adb_has_package(adb_bin, package_id, device_serial):
                return "adb"
        if shutil.which("apkeep"):
            return "apkeep"
        if shutil.which("gplaycli"):
            return "gplaycli"

        raise EngineUnavailableError(
            "No Android AVD Manager / Play Store download provider is available.",
            hint=self._provider_install_hint("avd"),
            details={"package_id": package_id},
        )

    @staticmethod
    def _provider_install_hint(provider: str) -> str:
        hints = {
            "avd": (
                "Install Android SDK platform-tools + emulator (ANDROID_HOME), create a Google Play "
                "AVD via 'avdmanager' or Android Studio, and sign into Google Play Store on the AVD."
            ),
            "adb": "Install Android platform-tools (adb) or run 'raa tool-manager download platform-tools'.",
            "apkeep": "Install apkeep (cargo install apkeep) and set RAA_PLAY_EMAIL / RAA_PLAY_AAS_TOKEN.",
            "gplaycli": "Install gplaycli and configure your Google Play credentials.",
        }
        return hints.get(provider, "Ensure the provider binary is installed and on PATH.")

    def _list_running_emulators(self, adb_bin: str) -> list[str]:
        try:
            proc = subprocess.run(
                [adb_bin, "devices"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        if proc.returncode != 0:
            return []
        serials: list[str] = []
        for line in proc.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device" and parts[0].startswith("emulator-"):
                serials.append(parts[0])
        return serials

    def _list_avds(self) -> list[str]:
        emulator_bin = self._resolve_sdk_binary("emulator")
        if emulator_bin:
            proc = self._run_command([emulator_bin, "-list-avds"], provider="avd")
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

        avdmanager_bin = self._resolve_sdk_binary("avdmanager")
        if avdmanager_bin:
            proc = self._run_command([avdmanager_bin, "list", "avd", "-c"], provider="avd")
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

        raise EngineUnavailableError(
            "Neither Android 'emulator' nor 'avdmanager' was found in PATH or ANDROID_HOME.",
            hint=self._provider_install_hint("avd"),
        )

    def _ensure_avd_running(
        self,
        *,
        adb_bin: str,
        avd_name: str | None,
        device_serial: str | None,
        headless: bool,
        boot_timeout_seconds: float,
    ) -> tuple[str, str | None, bool]:
        running = self._list_running_emulators(adb_bin)
        if device_serial and (device_serial in running or not avd_name):
            return device_serial, avd_name, False
        if running and not avd_name:
            return running[0], None, False

        available_avds = self._list_avds()
        if not available_avds:
            raise EngineUnavailableError(
                "No Android Virtual Devices (AVDs) are configured in AVD Manager.",
                hint="Create a Google Play AVD in Android Studio or with 'avdmanager create avd'.",
            )

        target_avd = avd_name
        if target_avd is None:
            play_avds = [name for name in available_avds if "play" in name.lower()]
            target_avd = play_avds[0] if play_avds else available_avds[0]
        elif target_avd not in available_avds:
            raise InvalidArgumentsError(
                f"AVD '{target_avd}' not found in AVD Manager.",
                hint=f"Available AVDs: {', '.join(available_avds)}",
            )

        emulator_bin = self._resolve_sdk_binary("emulator")
        if not emulator_bin:
            raise EngineUnavailableError(
                "Android 'emulator' binary is required to launch the AVD.",
                hint=self._provider_install_hint("avd"),
            )

        cmd = [emulator_bin, "-avd", target_avd, "-no-audio"]
        if headless:
            cmd.extend(["-no-window", "-gpu", "swiftshader_indirect"])
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.monotonic() + boot_timeout_seconds
        serial: str | None = device_serial
        while time.monotonic() < deadline:
            candidates = self._list_running_emulators(adb_bin)
            if serial and serial in candidates:
                pass
            elif candidates:
                serial = candidates[0]
            if serial and self._is_device_booted(adb_bin, serial):
                return serial, target_avd, True
            time.sleep(2.0)

        raise EngineUnavailableError(
            f"AVD '{target_avd}' did not finish booting within {boot_timeout_seconds}s.",
            hint="Increase boot_timeout_seconds or start the AVD manually in Android Studio.",
        )

    def _is_device_booted(self, adb_bin: str, serial: str) -> bool:
        try:
            proc = subprocess.run(
                [adb_bin, "-s", serial, "shell", "getprop", "sys.boot_completed"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return proc.returncode == 0 and proc.stdout.strip() == "1"

    def _download_via_avd_playstore(
        self,
        *,
        package_id: str,
        staging_dir: Path,
        avd_name: str | None,
        device_serial: str | None,
        headless: bool,
        boot_timeout_seconds: float,
        install_timeout_seconds: float,
        auto_tap_install: bool,
    ) -> tuple[Path, dict[str, Any]]:
        adb_bin = self._resolve_sdk_binary("adb")
        if not adb_bin:
            raise EngineUnavailableError(
                "Android SDK 'adb' is required for AVD Play Store downloads.",
                hint=self._provider_install_hint("avd"),
            )

        serial, resolved_avd, launched = self._ensure_avd_running(
            adb_bin=adb_bin,
            avd_name=avd_name,
            device_serial=device_serial,
            headless=headless,
            boot_timeout_seconds=boot_timeout_seconds,
        )

        remote_paths = self._adb_pm_paths(adb_bin, package_id, serial)
        if not remote_paths:
            self._open_playstore_listing(adb_bin, serial, package_id)
            remote_paths = self._wait_for_playstore_install(
                adb_bin=adb_bin,
                serial=serial,
                package_id=package_id,
                install_timeout_seconds=install_timeout_seconds,
                auto_tap_install=auto_tap_install,
            )

        bundle_or_apk, split_count = self._pull_apks_from_device(
            adb_bin=adb_bin,
            serial=serial,
            package_id=package_id,
            remote_paths=remote_paths,
            staging_dir=staging_dir,
        )
        return bundle_or_apk, {
            "split_count": split_count,
            "device_serial": serial,
            "avd_name": resolved_avd,
            "avd_launched": launched,
        }

    def _open_playstore_listing(self, adb_bin: str, serial: str, package_id: str) -> None:
        market_uri = f"market://details?id={package_id}"
        proc = self._run_command(
            [
                adb_bin,
                "-s",
                serial,
                "shell",
                "am",
                "start",
                "-a",
                "android.intent.action.VIEW",
                "-d",
                market_uri,
            ],
            provider="avd",
        )
        if "Error:" in proc.stdout or "Error:" in proc.stderr:
            web_uri = f"https://play.google.com/store/apps/details?id={package_id}"
            self._run_command(
                [
                    adb_bin,
                    "-s",
                    serial,
                    "shell",
                    "am",
                    "start",
                    "-a",
                    "android.intent.action.VIEW",
                    "-d",
                    web_uri,
                ],
                provider="avd",
            )

    def _wait_for_playstore_install(
        self,
        *,
        adb_bin: str,
        serial: str,
        package_id: str,
        install_timeout_seconds: float,
        auto_tap_install: bool,
    ) -> list[str]:
        deadline = time.monotonic() + install_timeout_seconds
        tapped_install = False

        while time.monotonic() < deadline:
            paths = self._adb_pm_paths(adb_bin, package_id, serial)
            if paths:
                return paths

            if auto_tap_install and not tapped_install:
                coords = self._probe_playstore_install_button(adb_bin, serial)
                if coords is not None:
                    self._run_command(
                        [
                            adb_bin,
                            "-s",
                            serial,
                            "shell",
                            "input",
                            "tap",
                            str(coords[0]),
                            str(coords[1]),
                        ],
                        provider="avd",
                    )
                    tapped_install = True

            time.sleep(2.0)

        raise EngineUnavailableError(
            f"Timed out waiting for Google Play Store on AVD '{serial}' to install '{package_id}'.",
            hint=(
                "Ensure the AVD has a Google Play Store image, internet access, and is signed into "
                "a Google account, then tap Install if prompted."
            ),
        )

    def _probe_playstore_install_button(self, adb_bin: str, serial: str) -> tuple[int, int] | None:
        dump_path = "/sdcard/raa_playstore_ui.xml"
        try:
            subprocess.run(
                [adb_bin, "-s", serial, "shell", "uiautomator", "dump", dump_path],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            cat_proc = subprocess.run(
                [adb_bin, "-s", serial, "shell", "cat", dump_path],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if cat_proc.returncode != 0 or not cat_proc.stdout.strip():
            return None
        return _find_install_button_center(cat_proc.stdout)

    def _adb_has_package(self, adb_bin: str, package_id: str, device_serial: str | None) -> bool:
        return bool(self._adb_pm_paths(adb_bin, package_id, device_serial))

    def _adb_pm_paths(
        self,
        adb_bin: str,
        package_id: str,
        device_serial: str | None,
    ) -> list[str]:
        cmd = [adb_bin]
        if device_serial:
            cmd.extend(["-s", device_serial])
        cmd.extend(["shell", "pm", "path", package_id])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        if proc.returncode != 0:
            return []
        return [
            line.removeprefix("package:").strip()
            for line in proc.stdout.splitlines()
            if line.strip().startswith("package:")
        ]

    def _pull_apks_from_device(
        self,
        *,
        adb_bin: str,
        serial: str | None,
        package_id: str,
        remote_paths: list[str],
        staging_dir: Path,
    ) -> tuple[Path, int]:
        base_cmd = [adb_bin]
        if serial:
            base_cmd.extend(["-s", serial])

        pulled: list[Path] = []
        for idx, remote_path in enumerate(remote_paths):
            remote_name = Path(remote_path).name or f"split_{idx}.apk"
            local_dest = staging_dir / remote_name
            self._run_command([*base_cmd, "pull", remote_path, str(local_dest)], provider="adb")
            if local_dest.is_file():
                pulled.append(local_dest)

        if not pulled:
            raise InvalidArtifactError(
                f"ADB pull produced no APK files for {package_id}.",
                hint="Check device permissions and USB/Wi-Fi ADB connectivity.",
            )

        if len(pulled) == 1:
            return pulled[0], 1

        bundle_path = staging_dir / f"{package_id}.apks"
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for apk_file in pulled:
                archive.write(apk_file, arcname=apk_file.name)
        return bundle_path, len(pulled)

    def download_with_apkeep(
        self,
        package_or_url: str,
        *,
        project_id: str | None = None,
        source: ApkeepSource = "google-play",
        version_code: int | None = None,
        split_apk: bool = False,
        email: str | None = None,
        aas_token: str | None = None,
        oauth_token: str | None = None,
        auto_ingest: bool = True,
    ) -> dict[str, Any]:
        """Download an app using efforg/apkeep (defaulting to Google Play Store)."""
        package_id = parse_play_package_id(package_or_url)
        if auto_ingest and not project_id:
            raise InvalidArgumentsError(
                "project_id is required when auto_ingest is enabled.",
                hint="Pass project_id or set auto_ingest=False to stage the download only.",
            )
        if shutil.which("apkeep") is None:
            raise EngineUnavailableError(
                "EFF 'apkeep' binary is not installed on PATH.",
                hint=self._provider_install_hint("apkeep"),
            )

        staging_dir = self.workspace.tmp_dir / "apkeep" / source / package_id
        staging_dir.mkdir(parents=True, exist_ok=True)
        downloaded_path, extra = self._download_via_apkeep(
            package_id=package_id,
            staging_dir=staging_dir,
            source=source,
            version_code=version_code,
            split_apk=split_apk,
            email=email,
            aas_token=aas_token,
            oauth_token=oauth_token,
        )

        result: dict[str, Any] = {
            "package_id": package_id,
            "provider": "apkeep",
            "downloaded_path": str(downloaded_path),
            "filename": downloaded_path.name,
            "size_bytes": downloaded_path.stat().st_size,
            **extra,
        }

        if project_id and auto_ingest:
            ingested = self.artifacts.ingest_path(project_id, str(downloaded_path))
            dl_evidence = self.evidence.add(
                project_id=project_id,
                artifact_id=ingested.artifact.id,
                kind="apkeep.download",
                summary=f"Downloaded {package_id} via apkeep ({source})",
                payload={
                    "package_id": package_id,
                    "provider": "apkeep",
                    "filename": downloaded_path.name,
                    "sha256": ingested.artifact.sha256,
                    **extra,
                },
                source_tool="apkeep_download_app",
                authority=Authority.SHIPPED_ARTIFACT,
                representation=Representation.ORIGINAL,
                confidence=Confidence.OBSERVED,
            )
            result["ingested"] = True
            result["artifact"] = ingested.artifact.model_dump(mode="json")
            result["evidence_ids"] = [rec.id for rec in ingested.evidence] + [dl_evidence.id]
        else:
            result["ingested"] = False
            result["evidence_ids"] = []

        return result

    def _download_via_apkeep(
        self,
        *,
        package_id: str,
        staging_dir: Path,
        source: ApkeepSource = "google-play",
        version_code: int | None,
        split_apk: bool,
        email: str | None,
        aas_token: str | None,
        oauth_token: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        app_spec = f"{package_id}@{version_code}" if version_code is not None else package_id
        cmd = ["apkeep", "-d", source, "-a", app_spec, str(staging_dir)]
        if source == "google-play":
            resolved_email = email or os.environ.get("RAA_PLAY_EMAIL")
            resolved_token = aas_token or os.environ.get("RAA_PLAY_AAS_TOKEN")
            resolved_oauth = oauth_token or os.environ.get("RAA_PLAY_OAUTH_TOKEN")
            if resolved_email:
                cmd.extend(["-e", resolved_email])
            if resolved_token:
                cmd.extend(["-t", resolved_token])
            if resolved_oauth:
                cmd.extend(["-o", resolved_oauth])
        if split_apk:
            cmd.append("--accept-tos")

        self._run_command(cmd, provider="apkeep")
        artifact_path, splits = self._collect_downloaded_artifact(staging_dir, package_id)
        return artifact_path, {
            "source": source,
            "split_count": len(splits),
            "version_code": version_code,
        }

    def _download_via_gplaycli(
        self,
        *,
        package_id: str,
        staging_dir: Path,
    ) -> tuple[Path, dict[str, Any]]:
        cmd = ["gplaycli", "-d", package_id, "-f", str(staging_dir)]
        self._run_command(cmd, provider="gplaycli")
        artifact_path, splits = self._collect_downloaded_artifact(staging_dir, package_id)
        return artifact_path, {"split_count": len(splits)}

    def _download_via_adb(
        self,
        *,
        package_id: str,
        staging_dir: Path,
        device_serial: str | None,
    ) -> tuple[Path, dict[str, Any]]:
        adb_bin = self._resolve_sdk_binary("adb")
        if not adb_bin:
            raise EngineUnavailableError(
                "Android SDK 'adb' is not installed on PATH.",
                hint=self._provider_install_hint("adb"),
            )
        remote_paths = self._adb_pm_paths(adb_bin, package_id, device_serial)
        if not remote_paths:
            raise InvalidArtifactError(
                f"Package '{package_id}' is not installed on the connected ADB device.",
                hint="Install the app from Google Play Store on the device/emulator first.",
            )
        bundle_or_apk, split_count = self._pull_apks_from_device(
            adb_bin=adb_bin,
            serial=device_serial,
            package_id=package_id,
            remote_paths=remote_paths,
            staging_dir=staging_dir,
        )
        return bundle_or_apk, {"split_count": split_count, "device_serial": device_serial}

    def _run_command(self, cmd: list[str], *, provider: str) -> subprocess.CompletedProcess[str]:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.engine_timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise EngineUnavailableError(
                f"Provider binary '{provider}' was not found.",
                hint=self._provider_install_hint(provider),
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise EngineUnavailableError(
                f"Provider '{provider}' timed out after {self.settings.engine_timeout_seconds}s.",
            ) from exc

        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "").strip()
            raise EngineUnavailableError(
                f"Provider '{provider}' exited with status {proc.returncode}: {stderr[:400]}",
                hint=self._provider_install_hint(provider),
            )
        return proc

    def _collect_downloaded_artifact(
        self,
        staging_dir: Path,
        package_id: str,
    ) -> tuple[Path, list[Path]]:
        candidates = sorted(
            (
                p
                for p in staging_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in _ARTIFACT_EXTS
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise InvalidArtifactError(
                f"Provider did not produce an APK/APKS/XAPK/AAB file for {package_id}.",
                hint="Verify credentials, region availability, and package ID.",
            )

        for preferred_ext in (".xapk", ".apks", ".aab"):
            for item in candidates:
                if item.suffix.lower() == preferred_ext:
                    return item, [item]

        apks = [p for p in candidates if p.suffix.lower() == ".apk"]
        if len(apks) == 1:
            return apks[0], apks

        bundle_path = staging_dir / f"{package_id}.apks"
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for apk_file in apks:
                archive.write(apk_file, arcname=apk_file.name)
        return bundle_path, apks
