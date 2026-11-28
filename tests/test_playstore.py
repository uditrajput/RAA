"""Tests for Google Play Store metadata lookup and AVD/Play Store app download."""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from raa.cli.main import app as cli_app
from raa.errors import EngineUnavailableError, InvalidArgumentsError, PolicyDeniedError
from raa.runtime import Runtime
from raa.services.playstore import _find_install_button_center, parse_play_package_id


def _write_minimal_apk(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"manifest-placeholder")
        archive.writestr("classes.dex", b"dex\n035\x00")


def test_parse_play_package_id_accepts_id_and_url() -> None:
    assert parse_play_package_id("com.example.demo_app") == "com.example.demo_app"
    assert (
        parse_play_package_id(
            "https://play.google.com/store/apps/details?id=com.example.demo&hl=en"
        )
        == "com.example.demo"
    )


@pytest.mark.parametrize(
    "bad_input",
    [
        "",
        "not_a_package",
        "com.example;rm -rf /",
        "https://evil.example.com/store/apps/details?id=com.example.demo",
        "https://play.google.com/store/apps/details?hl=en",
    ],
)
def test_parse_play_package_id_rejects_invalid(bad_input: str) -> None:
    with pytest.raises(InvalidArgumentsError):
        parse_play_package_id(bad_input)


def test_find_install_button_center() -> None:
    xml_doc = (
        "<hierarchy>"
        '<node text="Uninstall" bounds="[0,0][100,50]" enabled="true"/>'
        '<node text="Install" bounds="[100,200][300,260]" enabled="true"/>'
        "</hierarchy>"
    )
    assert _find_install_button_center(xml_doc) == (200, 230)


@pytest.mark.asyncio
async def test_playstore_app_info_parses_listing(
    runtime: Runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html_body = (
        "<html><head>"
        "<title>Demo App - Apps on Google Play</title>"
        '<meta property="og:title" content="Demo App">'
        '<meta property="og:description" content="A sample Android app.">'
        '<meta property="og:image" content="https://play-lh.googleusercontent.com/icon.png">'
        "</head></html>"
    )

    def fake_get(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(200, text=html_body, request=httpx.Request("GET", url))

    monkeypatch.setattr("raa.services.playstore.httpx.get", fake_get)

    envelope = await runtime.invoke(
        "playstore_app_info",
        {"package_or_url": "https://play.google.com/store/apps/details?id=com.example.demo"},
    )
    assert envelope.data["package_id"] == "com.example.demo"
    assert envelope.data["title"] == "Demo App"
    assert envelope.data["description"] == "A sample Android app."
    assert envelope.data["icon_url"] == "https://play-lh.googleusercontent.com/icon.png"


@pytest.mark.asyncio
async def test_playstore_download_via_avd_boots_taps_install_and_ingests(
    runtime: Runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await runtime.invoke("project_create", {"name": "AVD Play Store Demo"})
    project_id = created.data["id"]

    monkeypatch.setattr(
        "raa.services.playstore.shutil.which",
        lambda name: f"/sdk/{name}" if name in {"adb", "emulator"} else None,
    )
    monkeypatch.setattr("raa.services.playstore.time.sleep", lambda _: None)

    state = {"booted": False, "tapped": False}
    launched_cmds: list[list[str]] = []

    def fake_popen(cmd: list[str], **kwargs: Any) -> Any:
        launched_cmds.append(cmd)
        state["booted"] = True
        return object()

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd[1:] == ["-list-avds"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="Pixel_7_API_34\nPixel_8_Play_Store\n",
                stderr="",
            )
        if cmd[1:] == ["devices"]:
            out = "List of devices attached\n"
            if state["booted"]:
                out += "emulator-5554\tdevice\n"
            return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
        if "getprop" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="1\n", stderr="")
        if "pm" in cmd and "path" in cmd:
            if state["tapped"]:
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout=(
                        "package:/data/app/com.example.play/base.apk\n"
                        "package:/data/app/com.example.play/split_config.arm64_v8a.apk\n"
                    ),
                    stderr="",
                )
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
        if "am" in cmd and "start" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="Starting: Intent", stderr="")
        if "uiautomator" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="UI hierchary dumped", stderr="")
        if "cat" in cmd:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout='<hierarchy><node text="Install" bounds="[100,200][300,260]" enabled="true"/></hierarchy>',
                stderr="",
            )
        if "input" in cmd and "tap" in cmd:
            state["tapped"] = True
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pull" in cmd:
            _write_minimal_apk(Path(cmd[-1]))
            return subprocess.CompletedProcess(cmd, 0, stdout="1 file pulled", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr("raa.services.playstore.subprocess.Popen", fake_popen)
    monkeypatch.setattr("raa.services.playstore.subprocess.run", fake_run)

    envelope = await runtime.invoke(
        "playstore_download_app",
        {
            "package_or_url": "https://play.google.com/store/apps/details?id=com.example.play",
            "project_id": project_id,
            "provider": "auto",
            "headless": True,
        },
    )
    assert launched_cmds and "Pixel_8_Play_Store" in launched_cmds[0]
    assert "-no-window" in launched_cmds[0]
    assert envelope.data["provider"] == "avd"
    assert envelope.data["avd_name"] == "Pixel_8_Play_Store"
    assert envelope.data["avd_launched"] is True
    assert envelope.data["device_serial"] == "emulator-5554"
    assert envelope.data["split_count"] == 2
    assert envelope.data["filename"] == "com.example.play.apks"
    assert envelope.data["ingested"] is True
    assert envelope.data["artifact"]["artifact_type"] == "apks"


@pytest.mark.asyncio
async def test_playstore_download_via_apkeep_and_auto_ingest(
    runtime: Runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await runtime.invoke("project_create", {"name": "Play Store Demo"})
    project_id = created.data["id"]

    monkeypatch.setattr(
        "raa.services.playstore.shutil.which",
        lambda name: f"/usr/bin/{name}" if name == "apkeep" else None,
    )

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        staging_dir = Path(cmd[5])
        _write_minimal_apk(staging_dir / "com.example.demo.apk")
        return subprocess.CompletedProcess(cmd, 0, stdout="Downloaded", stderr="")

    monkeypatch.setattr("raa.services.playstore.subprocess.run", fake_run)

    envelope = await runtime.invoke(
        "playstore_download_app",
        {
            "package_or_url": "com.example.demo",
            "project_id": project_id,
            "provider": "apkeep",
            "email": "user@example.com",
            "aas_token": "aas_et/test_token",
        },
    )
    assert envelope.data["provider"] == "apkeep"
    assert envelope.data["ingested"] is True
    assert envelope.data["artifact"]["project_id"] == project_id
    assert envelope.data["artifact"]["artifact_type"] == "apk"
    assert len(envelope.evidence_ids) >= 3


@pytest.mark.asyncio
async def test_playstore_download_via_adb_split_apks(
    runtime: Runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await runtime.invoke("project_create", {"name": "ADB Split Demo"})
    project_id = created.data["id"]

    monkeypatch.setattr(
        "raa.services.playstore.shutil.which",
        lambda name: f"/usr/bin/{name}" if name == "adb" else None,
    )

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd[1:] == ["devices"]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="List of devices attached\n", stderr=""
            )
        if "pm" in cmd:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=(
                    "package:/data/app/com.example.split/base.apk\n"
                    "package:/data/app/com.example.split/split_config.arm64_v8a.apk\n"
                ),
                stderr="",
            )
        if "pull" in cmd:
            dest = Path(cmd[-1])
            _write_minimal_apk(dest)
            return subprocess.CompletedProcess(cmd, 0, stdout="1 file pulled", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr("raa.services.playstore.subprocess.run", fake_run)

    envelope = await runtime.invoke(
        "playstore_download_app",
        {
            "package_or_url": "com.example.split",
            "project_id": project_id,
            "provider": "auto",
        },
    )
    assert envelope.data["provider"] == "adb"
    assert envelope.data["split_count"] == 2
    assert envelope.data["filename"] == "com.example.split.apks"
    assert envelope.data["ingested"] is True
    assert envelope.data["artifact"]["artifact_type"] == "apks"


@pytest.mark.asyncio
async def test_playstore_download_requires_provider_and_scope(
    runtime: Runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await runtime.invoke("project_create", {"name": "No Provider"})
    monkeypatch.setattr("raa.services.playstore.shutil.which", lambda name: None)
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
    with pytest.raises(EngineUnavailableError):
        await runtime.invoke(
            "playstore_download_app",
            {
                "package_or_url": "com.example.demo",
                "project_id": created.data["id"],
                "auto_ingest": False,
            },
        )

    restricted = await runtime.invoke(
        "project_create", {"name": "Readonly", "scopes": ["project.read"]}
    )
    with pytest.raises(PolicyDeniedError):
        await runtime.invoke(
            "playstore_download_app",
            {"package_or_url": "com.example.demo", "project_id": restricted.data["id"]},
        )


def test_cli_playstore_info_and_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAA_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setattr(
        "raa.services.playstore.httpx.get",
        lambda url, **kwargs: httpx.Response(
            200,
            text='<meta property="og:title" content="CLI Demo">',
            request=httpx.Request("GET", url),
        ),
    )

    runner = CliRunner()
    res = runner.invoke(cli_app, ["--json", "artifact", "playstore-info", "com.example.cli"])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["data"]["title"] == "CLI Demo"


@pytest.mark.asyncio
async def test_apkeep_download_app_google_play_and_fdroid(
    runtime: Runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await runtime.invoke("project_create", {"name": "Apkeep Demo"})
    project_id = created.data["id"]

    monkeypatch.setattr(
        "raa.services.playstore.shutil.which",
        lambda name: f"/usr/bin/{name}" if name == "apkeep" else None,
    )

    seen_cmds: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen_cmds.append(cmd)
        staging_dir = Path(cmd[5])
        _write_minimal_apk(staging_dir / "com.example.apkeep.apk")
        return subprocess.CompletedProcess(cmd, 0, stdout="Downloaded", stderr="")

    monkeypatch.setattr("raa.services.playstore.subprocess.run", fake_run)

    # Default source is google-play (first priority)
    play_res = await runtime.invoke(
        "apkeep_download_app",
        {
            "package_or_url": "com.example.apkeep",
            "project_id": project_id,
            "email": "user@example.com",
            "oauth_token": "oauth2_4/test_token",
        },
    )
    assert seen_cmds[0][:4] == ["apkeep", "-d", "google-play", "-a"]
    assert "-o" in seen_cmds[0]
    assert play_res.data["source"] == "google-play"
    assert play_res.data["ingested"] is True

    # Alternative source (f-droid)
    fdroid_res = await runtime.invoke(
        "apkeep_download_app",
        {
            "package_or_url": "org.fdroid.fdroid",
            "project_id": project_id,
            "source": "f-droid",
        },
    )
    assert seen_cmds[1][:4] == ["apkeep", "-d", "f-droid", "-a"]
    assert fdroid_res.data["source"] == "f-droid"
    assert fdroid_res.data["ingested"] is True

    # Verify apkeep is registered in ToolManagerService
    tool_ids = {t["tool_id"] for t in runtime.tool_manager.list_tools()}
    assert "apkeep" in tool_ids
