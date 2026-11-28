"""Tests for UAD-backed rootless Android debloating, CLI, MCP tools, and hardened skills."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from raa.cli.main import app
from raa.runtime import Runtime
from raa.services.debloat import AndroidDebloatService
from raa.services.skills import SkillService


def test_debloat_service_classify_and_inspect(tmp_path: Path) -> None:
    svc = AndroidDebloatService(tmp_path)
    assert svc.classify_package("com.miui.analytics")["tier"] == "recommended"
    assert svc.classify_package("com.miui.securitycenter")["tier"] == "unsafe"
    assert svc.classify_package("com.android.systemui")["tier"] == "protected_system"

    res = svc.inspect_packages(tier_filter="recommended")
    assert res["status"] == "success"
    assert res["filtered_count"] >= 5
    assert all(p["tier"] == "recommended" for p in res["packages"])


def test_debloat_dry_run_execute_and_restore(tmp_path: Path) -> None:
    svc = AndroidDebloatService(tmp_path)
    pkgs = ["com.miui.analytics", "com.android.systemui", "com.samsung.android.mdx"]

    # Dry run previews without writing backup or mutating
    preview = svc.apply_debloat(packages=pkgs, dry_run=True)
    assert preview["status"] == "success"
    assert preview["mode"] == "dry_run_debloat"
    assert preview["actionable_count"] == 1
    assert preview["blocked_count"] == 2  # protected_system + expert

    # Execute stages commands, writes JSON backup + .sh/.ps1 undo scripts
    applied = svc.apply_debloat(packages=pkgs, dry_run=False)
    assert applied["status"] == "success"
    assert applied["mode"] == "debloat"
    backup_path = Path(applied["backup_file"])
    sh_path = Path(applied["restore_script_sh"])
    ps1_path = Path(applied["restore_script_ps1"])
    assert backup_path.is_file()
    assert sh_path.is_file()
    assert ps1_path.is_file()
    assert "pm enable com.miui.analytics" in sh_path.read_text(encoding="utf-8")

    # Restore from backup
    restored = svc.restore_from_backup(str(backup_path), dry_run=False)
    assert restored["status"] == "success"
    assert restored["mode"] == "restore"
    assert restored["results"][0]["package"] == "com.miui.analytics"
    assert restored["results"][0]["action"] == "enable"


async def test_debloat_mcp_tools_via_runtime(runtime: Runtime) -> None:
    inspect_out = await runtime.invoke(
        "android_debloat_inspect",
        {"tier_filter": "recommended"},
        profile="full",
    )
    assert inspect_out.data["status"] == "success"
    assert inspect_out.data["filtered_count"] >= 5

    apply_out = await runtime.invoke(
        "android_debloat_apply",
        {"packages": ["com.facebook.katana", "com.android.vending"], "dry_run": True},
        profile="full",
    )
    assert apply_out.data["status"] == "success"
    assert apply_out.data["actionable_count"] == 1
    assert apply_out.data["blocked_count"] == 1


def test_debloat_cli_commands() -> None:
    runner = CliRunner()
    res_inspect = runner.invoke(app, ["debloat", "inspect", "--tier", "recommended"])
    assert res_inspect.exit_code == 0

    res_apply = runner.invoke(app, ["debloat", "apply", "com.facebook.katana", "--dry-run"])
    assert res_apply.exit_code == 0


def test_hardened_skills_include_verification_gates() -> None:
    svc = SkillService()
    for skill_id in (
        "raa-controlled-rebuild",
        "raa-source-reconstruct",
        "raa-ui-redesign",
        "raa-security-audit",
        "report-and-export",
        "raa-self-evolving-recipes",
        "raa-android-tv-studio",
        "raa-wireless-device-gateway",
    ):
        skill = svc.get(skill_id)
        content = (skill.path / "SKILL.md").read_text(encoding="utf-8")
        assert "Verification" in content or "Anti-Rationalization" in content
    gw = svc.get("raa-wireless-device-gateway")
    assert "android_debloat_inspect" in gw.tools
    assert "android_debloat_apply" in gw.tools
