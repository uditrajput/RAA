"""Tests for profile dropdown visibility and Tools/MCP Mesh profile filtering in setup UI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from raa.api.setup_ui import (
    SETUP_HTML,
    ProfileUpdateBody,
    get_active_profile,
    update_active_profile,
)
from raa.services.skills import SkillService
from raa.services.tool_manager import SUPPORTED_TOOLS


def test_setup_html_profile_dropdown_visibility_and_filters() -> None:
    assert 'id="profileSelectWrapper" style="display: none;"' in SETUP_HTML
    assert "function updateProfileDropdownVisibility(tabId)" in SETUP_HTML
    assert "if (tabId === 'tools' || tabId === 'mesh' || tabId === 'skills')" in SETUP_HTML
    assert "function isToolInProfile(tool, profile)" in SETUP_HTML
    assert "function isMeshInProfile(connector, profile)" in SETUP_HTML
    assert "function isSkillInProfile(skill, profile)" in SETUP_HTML
    assert "allToolsCache.filter(t => isToolInProfile(t, activeProfile))" in SETUP_HTML
    assert "allMeshCache.filter(m => isMeshInProfile(m, activeProfile))" in SETUP_HTML
    assert "allSkillsCache.filter(s => isSkillInProfile(s, activeProfile))" in SETUP_HTML
    assert "openWifiQrPairModal('', 'Android Device')" in SETUP_HTML
    assert "📷 Pair with QR Code" in SETUP_HTML
    assert "1. Enable Developer Options" in SETUP_HTML
    assert "2. Turn ON Wireless Debugging" in SETUP_HTML
    assert "📷 QR Pair" not in SETUP_HTML
    assert "function upsertWifiDeviceCard(dev)" in SETUP_HTML
    assert 'id="wifiQrPairModal"' in SETUP_HTML
    assert "const TOOLS_PAGE_SIZE = 9;" in SETUP_HTML
    assert "const MESH_PAGE_SIZE = 8;" in SETUP_HTML
    assert "const SKILLS_PAGE_SIZE = 9;" in SETUP_HTML
    assert 'id="toolsPagination"' in SETUP_HTML
    assert 'id="meshPagination"' in SETUP_HTML
    assert 'id="skillsPagination"' in SETUP_HTML
    assert 'id="skillCategoryFilters"' in SETUP_HTML
    assert 'id="meshCategoryFilters"' in SETUP_HTML
    assert 'id="customSkillForm"' in SETUP_HTML
    assert "function renderPaginationControls(" in SETUP_HTML


def test_setup_profile_endpoints_roundtrip(tmp_path: Path, monkeypatch) -> None:
    import raa.api.setup_ui as setup_ui_mod

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    prof_file = cfg_dir / "profile.json"
    prof_file.write_text(json.dumps({"active_profile": "core"}), encoding="utf-8")
    monkeypatch.setattr(setup_ui_mod, "CONFIG_DIR", cfg_dir)

    dummy_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=None)))

    res_get = asyncio.run(get_active_profile(dummy_request))
    assert res_get["active_profile"] == "core"

    res_post = asyncio.run(
        update_active_profile(ProfileUpdateBody(active_profile="ui"), dummy_request)
    )
    assert res_post["status"] == "success"
    assert res_post["active_profile"] == "ui"

    res_get2 = asyncio.run(get_active_profile(dummy_request))
    assert res_get2["active_profile"] == "ui"


def test_app_store_compliance_skill_and_tool_registered() -> None:
    assert "app-store-compliance" in SUPPORTED_TOOLS
    meta = SUPPORTED_TOOLS["app-store-compliance"]
    assert meta["category"] == "security"
    assert meta["github_url"] == "https://github.com/mjmirza/app-store-compliance"

    skills = {s.id: s for s in SkillService().discover()}
    assert "raa-app-store-compliance" in skills
    assert "app-store-compliance" in skills["raa-app-store-compliance"].content
    assert "smap" in SUPPORTED_TOOLS
    assert "nmap-vulners" in SUPPORTED_TOOLS
    assert "raa-smap-recon" in skills
    assert "raa-nmap-vulners" in skills


def test_lan_discovery_resolves_mdns_and_ssdp_names() -> None:
    from raa.services.lan_discovery import resolve_lan_device_name

    name, _vendor = resolve_lan_device_name(
        "192.168.1.2",
        "Mobile Device (2)",
        mdns_map={"192.168.1.2": {"model": "iPhone15,2", "name": "Udits iPhone"}},
        ssdp_map={},
    )
    assert name == "iPhone15,2"

    tv_name, tv_vendor = resolve_lan_device_name(
        "192.168.1.5",
        "Mobile Device (5)",
        mdns_map={},
        ssdp_map={"192.168.1.5": {"name": "Living Room TV", "manufacturer": "Google Inc."}},
    )
    assert tv_name == "Living Room TV"
    assert tv_vendor == "Google Inc."


def test_wifi_device_label_clear_removes_duplicate_name(tmp_path: Path, monkeypatch) -> None:
    import raa.api.setup_ui as setup_ui_mod

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(setup_ui_mod, "CONFIG_DIR", cfg_dir)

    res1 = asyncio.run(
        setup_ui_mod.save_wifi_device_label(
            {"key": "aa:bb:cc:dd:ee:01", "label": "OPPO A15s", "ip": "192.168.1.7"}
        )
    )
    assert res1["status"] == "success"

    res_clear = asyncio.run(
        setup_ui_mod.save_wifi_device_label(
            {"key": "aa:bb:cc:dd:ee:01", "ip": "192.168.1.7", "clear_label": True}
        )
    )
    assert res_clear["status"] == "success"
    assert res_clear["label"] == ""
    saved = json.loads((cfg_dir / "wifi_labels.json").read_text(encoding="utf-8"))
    assert saved == {}


def test_wifi_qr_pair_start_generates_adb_payload() -> None:
    import raa.api.setup_ui as setup_ui_mod

    dummy_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=None)))
    res = asyncio.run(setup_ui_mod.start_wifi_qr_pair(dummy_request, {"ip": "192.168.1.12"}))
    assert res["status"] == "success"
    assert res["qr_payload"].startswith("WIFI:T:ADB;S:studio-")
    assert res["session_id"] in setup_ui_mod._WIFI_QR_SESSIONS


def test_wifi_qr_pair_poll_captures_metadata_and_updates_card(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    import raa.api.setup_ui as setup_ui_mod

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "wifi_labels.json").write_text(
        json.dumps({"0e:ee:bc:b6:8b:ba": {"mac": "0e:ee:bc:b6:8b:ba", "last_ip": "192.168.1.12"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_ui_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(setup_ui_mod, "_resolve_adb_executable", lambda _req: "adb")
    monkeypatch.setattr(
        setup_ui_mod, "_send_arp_windows", lambda ip, _idx: (ip, "0e:ee:bc:b6:8b:ba")
    )

    def fake_run(cmd, **_kwargs):
        if cmd[1:3] == ["mdns", "services"]:
            return SimpleNamespace(
                stdout=(
                    "studio-abc\t_adb-tls-pairing._tcp\t192.168.1.12:37123\n"
                    "adb-xyz\t_adb-tls-connect._tcp\t192.168.1.12:41999\n"
                ),
                stderr="",
            )
        if cmd[1] == "pair":
            return SimpleNamespace(stdout="Successfully paired to 192.168.1.12:37123", stderr="")
        if cmd[1] == "connect":
            return SimpleNamespace(stdout="connected to 192.168.1.12:41999", stderr="")
        if cmd[1:5] == ["-s", "192.168.1.12:41999", "shell", "getprop"]:
            prop_map = {
                "ro.product.marketname": "OPPO A15s",
                "ro.product.model": "CPH2179",
                "ro.product.manufacturer": "OPPO",
                "ro.build.version.release": "12",
            }
            return SimpleNamespace(stdout=prop_map.get(cmd[5], ""), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    setup_ui_mod._WIFI_QR_SESSIONS["sess1"] = {
        "service_name": "studio-abc",
        "password": "secret",
        "ip": "",
    }

    dummy_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=None)))
    res = asyncio.run(setup_ui_mod.poll_wifi_qr_pair(dummy_request, "sess1"))
    assert res["status"] == "paired"
    assert res["device_info"]["device_name"] == "OPPO A15s"
    assert res["device_info"]["vendor"] == "OPPO"
    assert res["device_info"]["android_version"] == "12"
    assert res["device_info"]["port"] == "41999"
    assert res["device"]["ip"] == "192.168.1.12"
    assert res["device"]["adb_status"] == "connected"
    assert res["device"]["device_name"] == "OPPO A15s"
    assert res["device"]["adb_port"] == 41999

    saved = json.loads((cfg_dir / "wifi_labels.json").read_text(encoding="utf-8"))
    card = saved["0e:ee:bc:b6:8b:ba"]
    assert card["device_name"] == "OPPO A15s"
    assert card["vendor"] == "OPPO"
    assert card["android_version"] == "12"
    assert card["adb_port"] == 41999
    assert card["last_ip"] == "192.168.1.12"


def test_wifi_qr_pair_poll_waits_for_delayed_mdns_connect(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    import raa.api.setup_ui as setup_ui_mod

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(setup_ui_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(setup_ui_mod, "_resolve_adb_executable", lambda _req: "adb")
    monkeypatch.setattr(
        setup_ui_mod, "_send_arp_windows", lambda ip, _idx: (ip, "aa:11:22:33:44:55")
    )

    mdns_calls = {"count": 0}

    def fake_run(cmd, **_kwargs):
        if cmd[1:3] == ["mdns", "services"]:
            mdns_calls["count"] += 1
            if mdns_calls["count"] == 1:
                return SimpleNamespace(
                    stdout="studio-xyz\t_adb-tls-pairing._tcp\t192.168.1.15:38001\n", stderr=""
                )
            return SimpleNamespace(
                stdout="adb-dev\t_adb-tls-connect._tcp\t192.168.1.15:42111\n", stderr=""
            )
        if cmd[1] == "pair":
            return SimpleNamespace(stdout="Successfully paired to 192.168.1.15:38001", stderr="")
        if cmd[1] == "connect":
            return SimpleNamespace(stdout="connected to 192.168.1.15:42111", stderr="")
        if cmd[1:5] == ["-s", "192.168.1.15:42111", "shell", "getprop"]:
            return SimpleNamespace(
                stdout="Pixel 8" if cmd[5] == "ro.product.model" else "", stderr=""
            )
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    setup_ui_mod._WIFI_QR_SESSIONS["sess2"] = {
        "service_name": "studio-xyz",
        "password": "pw",
        "ip": "",
    }

    dummy_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=None)))
    res = asyncio.run(setup_ui_mod.poll_wifi_qr_pair(dummy_request, "sess2"))
    assert res["status"] == "paired"
    assert res["device_info"]["device_name"] == "Pixel 8"
    assert res["device_info"]["port"] == "42111"


def test_list_wifi_devices_marks_mdns_tls_adb_device_connected(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    import raa.api.setup_ui as setup_ui_mod

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "wifi_labels.json").write_text(
        json.dumps(
            {
                "0e:ee:bc:b6:8b:ba": {
                    "mac": "0e:ee:bc:b6:8b:ba",
                    "last_ip": "192.168.1.12",
                    "device_name": "OPPO A15s",
                    "vendor": "OPPO",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_ui_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(setup_ui_mod, "_get_local_wifi_ip", lambda: "192.168.1.7")
    monkeypatch.setattr(
        setup_ui_mod, "_active_subnet_sweep", lambda _p, _ip: {"192.168.1.12": "0e:ee:bc:b6:8b:ba"}
    )
    monkeypatch.setattr(setup_ui_mod, "_resolve_adb_executable", lambda _req: "adb")

    def fake_run(cmd, **_kwargs):
        if cmd[1:3] == ["mdns", "services"]:
            return SimpleNamespace(
                stdout="adb-R58M123-xyz\t_adb-tls-connect._tcp\t192.168.1.12:40369\n", stderr=""
            )
        if cmd[1:3] == ["devices", "-l"]:
            return SimpleNamespace(
                stdout="List of devices attached\nadb-R58M123-xyz._adb-tls-connect._tcp\tdevice product:cph2179 model:CPH2179\n",
                stderr="",
            )
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    dummy_request = SimpleNamespace(
        url=SimpleNamespace(port=8765), app=SimpleNamespace(state=SimpleNamespace(runtime=None))
    )
    res = asyncio.run(setup_ui_mod.list_wifi_devices(dummy_request))
    devs = [d for d in res["devices"] if d.get("ip") == "192.168.1.12"]
    assert len(devs) == 1
    assert devs[0]["adb_status"] == "connected"
    assert devs[0]["adb_port"] == 40369
    assert devs[0]["device_name"] == "OPPO A15s"
    assert devs[0]["vendor"] == "OPPO"


def test_connect_wifi_device_auto_switches_to_live_mdns_port(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    import raa.api.setup_ui as setup_ui_mod

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(setup_ui_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(setup_ui_mod, "_resolve_adb_executable", lambda _req: "adb")
    monkeypatch.setattr(
        setup_ui_mod, "_send_arp_windows", lambda ip, _idx: (ip, "0e:ee:bc:b6:8b:ba")
    )
    monkeypatch.setattr(setup_ui_mod, "_is_port_open", lambda _h, p, timeout=1.5: p == 42888)

    def fake_run(cmd, **_kwargs):
        if cmd[1:3] == ["mdns", "services"]:
            return SimpleNamespace(
                stdout="adb-dev\t_adb-tls-connect._tcp\t192.168.1.12:42888\n", stderr=""
            )
        if cmd[1:3] == ["connect", "192.168.1.12:42888"]:
            return SimpleNamespace(stdout="connected to 192.168.1.12:42888", stderr="")
        if cmd[1:5] == ["-s", "192.168.1.12:42888", "shell", "getprop"]:
            return SimpleNamespace(
                stdout="OPPO A15s" if cmd[5] == "ro.product.marketname" else "", stderr=""
            )
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    dummy_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=None)))
    res = asyncio.run(
        setup_ui_mod.connect_wifi_device(dummy_request, {"target": "192.168.1.12:40369"})
    )
    assert res["status"] == "success"
    assert res["device_info"]["port"] == "42888"
    assert res["device"]["ip"] == "192.168.1.12"
    assert res["device"]["adb_status"] == "connected"
    assert res["device"]["adb_port"] == 42888
    assert res["device"]["device_name"] == "OPPO A15s"
    saved = json.loads((cfg_dir / "wifi_labels.json").read_text(encoding="utf-8"))
    assert saved["0e:ee:bc:b6:8b:ba"]["adb_port"] == 42888


def test_disconnect_wifi_device_resolves_mdns_tls_serial(monkeypatch) -> None:
    import subprocess

    import raa.api.setup_ui as setup_ui_mod

    monkeypatch.setattr(setup_ui_mod, "_resolve_adb_executable", lambda _req: "adb")

    def fake_run(cmd, **_kwargs):
        if cmd[1:3] == ["disconnect", "192.168.1.5:42343"]:
            return SimpleNamespace(
                returncode=1, stdout="", stderr="error: no such device '192.168.1.5:42343'"
            )
        if cmd[1:3] == ["mdns", "services"]:
            return SimpleNamespace(
                returncode=0,
                stdout="adb-vivo-123\t_adb-tls-connect._tcp\t192.168.1.5:42343\n",
                stderr="",
            )
        if cmd[1:3] == ["devices", "-l"]:
            return SimpleNamespace(
                returncode=0,
                stdout="List of devices attached\nadb-vivo-123._adb-tls-connect._tcp\tdevice model:I2217\n",
                stderr="",
            )
        if cmd[1:3] == ["disconnect", "adb-vivo-123._adb-tls-connect._tcp"]:
            return SimpleNamespace(
                returncode=0, stdout="disconnected adb-vivo-123._adb-tls-connect._tcp", stderr=""
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    dummy_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=None)))
    res = asyncio.run(
        setup_ui_mod.disconnect_wifi_device(dummy_request, {"target": "192.168.1.5:42343"})
    )
    assert res["status"] == "success"
    assert "disconnected adb-vivo-123._adb-tls-connect._tcp" in res["message"]


def test_wifi_qr_pair_poll_does_not_hijack_other_device_mdns_serial(
    tmp_path: Path, monkeypatch
) -> None:
    import subprocess

    import raa.api.setup_ui as setup_ui_mod

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(setup_ui_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(setup_ui_mod, "_resolve_adb_executable", lambda _req: "adb")
    monkeypatch.setattr(
        setup_ui_mod, "_send_arp_windows", lambda ip, _idx: (ip, "0e:ee:bc:b6:8b:ba")
    )
    monkeypatch.setattr(setup_ui_mod, "_is_port_open", lambda _h, _p, timeout=0.25: False)

    async def fast_sleep(_sec):
        return None

    monkeypatch.setattr(setup_ui_mod.asyncio, "sleep", fast_sleep)

    def fake_run(cmd, **_kwargs):
        if cmd[1:3] == ["mdns", "services"]:
            return SimpleNamespace(
                stdout=(
                    "studio-second\t_adb-tls-pairing._tcp\t192.168.1.12:39001\n"
                    "adb-vivo-other\t_adb-tls-connect._tcp\t192.168.1.5:42343\n"
                ),
                stderr="",
            )
        if cmd[1] == "pair":
            return SimpleNamespace(stdout="Successfully paired to 192.168.1.12:39001", stderr="")
        if cmd[1:3] == ["devices", "-l"]:
            return SimpleNamespace(
                stdout="List of devices attached\nadb-vivo-other._adb-tls-connect._tcp\tdevice model:I2217\n",
                stderr="",
            )
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    setup_ui_mod._WIFI_QR_SESSIONS["sess_second"] = {
        "service_name": "studio-second",
        "password": "pw",
        "ip": "",
    }

    dummy_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=None)))
    res = asyncio.run(setup_ui_mod.poll_wifi_qr_pair(dummy_request, "sess_second"))
    assert res["status"] == "paired"
    assert res["connected"] is False
    assert res["device"]["ip"] == "192.168.1.12"
    assert res["device"]["mac"] == "0e:ee:bc:b6:8b:ba"
    assert res["device"]["device_name"] != "I2217"


def test_setup_tools_open_path_resolves_missing_tool_dir(tmp_path: Path, monkeypatch) -> None:
    import raa.api.setup_ui as setup_ui_mod

    tools_dir = tmp_path / "tools"
    opened: list[str] = []

    def fake_open(target_path: str) -> dict[str, str]:
        resolved = setup_ui_mod._resolve_existing_path(target_path)
        opened.append(resolved)
        return {"status": "success", "path": resolved, "message": "ok"}

    monkeypatch.setattr(setup_ui_mod, "_open_path_sync", fake_open)
    fake_tm = SimpleNamespace(
        tools_dir=tools_dir,
        list_tools=lambda: [{"tool_id": "iphone-control-mcp", "binary_path": None}],
    )
    dummy_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(runtime=SimpleNamespace(tool_manager=fake_tm)))
    )

    body = setup_ui_mod.ToolOpenPathBody(tool_name="iphone-control-mcp", path="")
    out = asyncio.run(setup_ui_mod.setup_tools_open_path(dummy_request, body))
    assert out["status"] == "success"
    assert tools_dir.is_dir()
    assert opened == [str(tools_dir.resolve())]
