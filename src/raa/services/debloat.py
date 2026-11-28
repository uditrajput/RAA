"""Rootless UAD-backed Android Device Debloat & Restore Service.

Modeled after Universal Android Debloater (UAD) and interactive ADB debloat
workflows (`android-debloat-prompt`): classifies installed packages by safety
tier (`recommended`, `advanced`, `expert`, `unsafe`, `protected_system`),
provides human-readable impact descriptions, enforces dry-run preview before
mutation, and generates reversible JSON backups plus `.sh`/`.ps1` undo scripts.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROTECTED_ANDROID_PACKAGES: frozenset[str] = frozenset(
    {
        "android",
        "com.android.systemui",
        "com.android.settings",
        "com.android.phone",
        "com.android.providers.settings",
        "com.android.providers.telephony",
        "com.android.providers.contacts",
        "com.android.packageinstaller",
        "com.google.android.packageinstaller",
        "com.android.permissioncontroller",
        "com.google.android.permissioncontroller",
        "com.android.vending",
        "com.google.android.gms",
        "com.google.android.gsf",
        "com.android.bluetooth",
        "com.android.nfc",
        "com.android.tv.settings",
        "com.google.android.inputmethod.latin",
    }
)

UAD_PACKAGE_CATALOG: dict[str, dict[str, str]] = {
    # Meta / Facebook preloads
    "com.facebook.katana": {
        "tier": "recommended",
        "vendor": "Meta",
        "description": "Facebook main app stub/preload.",
        "removal_impact": "Safe to disable; reinstallable from Play Store if needed.",
    },
    "com.facebook.system": {
        "tier": "recommended",
        "vendor": "Meta",
        "description": "Meta App Installer background service.",
        "removal_impact": "Safe to disable; prevents silent Meta app updates.",
    },
    "com.facebook.appmanager": {
        "tier": "recommended",
        "vendor": "Meta",
        "description": "Meta App Manager preload updater.",
        "removal_impact": "Safe to disable; no OS impact.",
    },
    "com.facebook.services": {
        "tier": "recommended",
        "vendor": "Meta",
        "description": "Meta background telemetry and push service.",
        "removal_impact": "Safe to disable; reduces background wakeups.",
    },
    # Xiaomi / MIUI / HyperOS
    "com.miui.analytics": {
        "tier": "recommended",
        "vendor": "Xiaomi",
        "description": "MIUI/HyperOS usage analytics and telemetry collector.",
        "removal_impact": "Safe to disable; stops telemetry without affecting system stability.",
    },
    "com.xiaomi.joyose": {
        "tier": "recommended",
        "vendor": "Xiaomi",
        "description": "Xiaomi cloud/game telemetry and junk push daemon.",
        "removal_impact": "Safe to disable; may slightly change Game Turbo defaults.",
    },
    "com.xiaomi.mipicks": {
        "tier": "recommended",
        "vendor": "Xiaomi",
        "description": "Xiaomi GetApps alternative app store.",
        "removal_impact": "Safe to disable if using Google Play Store.",
    },
    "com.xiaomi.mitv.ads": {
        "tier": "recommended",
        "vendor": "Xiaomi TV",
        "description": "Xiaomi PatchWall/MiTV ad delivery service.",
        "removal_impact": "Safe to disable; removes homescreen ad banners.",
    },
    "com.miui.cloudbackup": {
        "tier": "advanced",
        "vendor": "Xiaomi",
        "description": "Xiaomi Cloud backup client.",
        "removal_impact": "Disables Xiaomi Cloud backups; Google Backup still works.",
    },
    "com.miui.securitycenter": {
        "tier": "unsafe",
        "vendor": "Xiaomi",
        "description": "MIUI Security Center (handles permissions/battery on MIUI).",
        "removal_impact": "Removing on MIUI/HyperOS can cause bootloops or broken permissions.",
    },
    # Samsung
    "com.samsung.android.bixby.agent": {
        "tier": "recommended",
        "vendor": "Samsung",
        "description": "Samsung Bixby Voice assistant.",
        "removal_impact": "Safe to disable if using Google Assistant or no voice assistant.",
    },
    "com.samsung.android.game.gamehome": {
        "tier": "recommended",
        "vendor": "Samsung",
        "description": "Samsung Gaming Hub / Game Launcher.",
        "removal_impact": "Safe to disable; games remain directly launchable.",
    },
    "com.samsung.android.app.spage": {
        "tier": "advanced",
        "vendor": "Samsung",
        "description": "Samsung Free / Bixby Home feed.",
        "removal_impact": "Removes leftmost launcher news feed.",
    },
    "com.samsung.android.mdx": {
        "tier": "expert",
        "vendor": "Samsung",
        "description": "Link to Windows / cross-device continuity service.",
        "removal_impact": "Breaks Phone Link / Windows continuity if used.",
    },
    # Google / Android TV / OEM
    "com.google.android.apps.tachyon": {
        "tier": "recommended",
        "vendor": "Google",
        "description": "Google Meet (formerly Duo) preinstalled client.",
        "removal_impact": "Safe to disable if not used.",
    },
    "com.google.android.videos": {
        "tier": "recommended",
        "vendor": "Google",
        "description": "Google TV / Play Movies preload.",
        "removal_impact": "Safe to disable if not used.",
    },
    "com.google.android.tvrecommendations": {
        "tier": "recommended",
        "vendor": "Google TV",
        "description": "Android TV homescreen sponsored recommendations.",
        "removal_impact": "Safe to disable; cleans up TV homescreen recommendations.",
    },
    "com.google.android.apps.tv.launcherx": {
        "tier": "advanced",
        "vendor": "Google TV",
        "description": "Google TV default launcher.",
        "removal_impact": "Only disable if an alternate launcher (e.g. CleanYourTV) is set.",
    },
    "com.google.android.googlequicksearchbox": {
        "tier": "advanced",
        "vendor": "Google",
        "description": "Google App / Search widget / Assistant host.",
        "removal_impact": "Disables Google Assistant and Discover feed.",
    },
    "com.google.android.projection.gearhead": {
        "tier": "advanced",
        "vendor": "Google",
        "description": "Android Auto preinstalled service.",
        "removal_impact": "Breaks Android Auto car head-unit projection.",
    },
    "com.microsoft.appmanager": {
        "tier": "recommended",
        "vendor": "Microsoft",
        "description": "Your Phone / Link to Windows companion preload.",
        "removal_impact": "Safe to disable if not syncing with Windows.",
    },
    "com.heytap.browser": {
        "tier": "recommended",
        "vendor": "OPPO / OnePlus",
        "description": "HeyTap OEM browser with promotional feeds.",
        "removal_impact": "Safe to disable when using Chrome/Firefox.",
    },
}

_BLOAT_HEURISTIC_KEYWORDS = (
    "ads",
    "analytics",
    "telemetry",
    "facebook",
    "bixby",
    "mipicks",
    "joyose",
    "partner",
    "promotion",
    "sponsored",
    "tvrecommendations",
)

_PROTECTED_HEURISTIC_KEYWORDS = (
    "systemui",
    "permissioncontroller",
    "packageinstaller",
    "providers.settings",
    "providers.telephony",
    "inputmethod",
    "bluetooth",
    "tv.settings",
)


class AndroidDebloatService:
    """Provides rootless UAD-backed Android package inspection, safe debloating, and undo scripts."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.debloat_dir = workspace_root / "debloat"
        self.debloat_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def classify_package(package_name: str) -> dict[str, str]:
        """Classify an Android package using UAD-style safety tiers and impact metadata."""
        pkg = package_name.strip()
        low = pkg.lower()

        if pkg in PROTECTED_ANDROID_PACKAGES or any(
            kw in low for kw in _PROTECTED_HEURISTIC_KEYWORDS
        ):
            return {
                "package": pkg,
                "tier": "protected_system",
                "vendor": "Android Core",
                "description": "Critical OS, Play Services, or input/permission component.",
                "removal_impact": "BLOCKED: Disabling this package can break core device functionality.",
            }

        if pkg in UAD_PACKAGE_CATALOG:
            entry = UAD_PACKAGE_CATALOG[pkg]
            return {
                "package": pkg,
                "tier": entry["tier"],
                "vendor": entry["vendor"],
                "description": entry["description"],
                "removal_impact": entry["removal_impact"],
            }

        if any(kw in low for kw in _BLOAT_HEURISTIC_KEYWORDS):
            return {
                "package": pkg,
                "tier": "recommended",
                "vendor": "OEM / Third-Party",
                "description": "Heuristic match for telemetry, ads, or vendor preload.",
                "removal_impact": "Likely safe to disable; verify before confirming.",
            }

        return {
            "package": pkg,
            "tier": "unknown",
            "vendor": "Unknown",
            "description": "Uncatalogued package; no UAD safety entry.",
            "removal_impact": "Inspect app purpose before disabling.",
        }

    def _run_adb(self, device_id: str, args: list[str], timeout: int = 12) -> tuple[bool, str]:
        adb_exe = shutil.which("adb")
        if not adb_exe:
            return False, "adb binary not found on PATH."
        cmd = [adb_exe]
        if device_id.strip():
            cmd.extend(["-s", device_id.strip()])
        cmd.extend(args)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode == 0, out.strip()
        except Exception as exc:
            return False, str(exc)

    def inspect_packages(
        self,
        device_id: str = "",
        tier_filter: str | None = None,
    ) -> dict[str, Any]:
        """Inspect installed packages on an Android device and classify by UAD safety tier."""
        raw_packages: list[str] = []
        live_connected = False
        note = ""

        if device_id.strip():
            ok, out = self._run_adb(device_id, ["shell", "pm", "list", "packages", "-e"])
            if ok and out:
                live_connected = True
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("package:"):
                        raw_packages.append(line.split("package:", 1)[1].strip())
            else:
                note = (
                    out or f"Could not reach device '{device_id}'. Showing UAD reference catalog."
                )
        else:
            note = "No device_id provided. Showing UAD reference catalog."

        if not raw_packages:
            raw_packages = [
                *sorted(UAD_PACKAGE_CATALOG.keys()),
                "com.android.vending",
                "com.android.settings",
            ]

        classified = [self.classify_package(pkg) for pkg in raw_packages]
        if tier_filter and tier_filter.strip():
            target_tier = tier_filter.strip().lower()
            filtered = [item for item in classified if item["tier"] == target_tier]
        else:
            filtered = classified

        tier_counts: dict[str, int] = {}
        for item in classified:
            tier_counts[item["tier"]] = tier_counts.get(item["tier"], 0) + 1

        return {
            "status": "success",
            "device_id": device_id.strip(),
            "live_connected": live_connected,
            "note": note,
            "total_packages": len(classified),
            "filtered_count": len(filtered),
            "tier_counts": tier_counts,
            "packages": filtered,
        }

    def apply_debloat(
        self,
        packages: list[str],
        device_id: str = "",
        dry_run: bool = True,
        allow_expert: bool = False,
        restore: bool = False,
    ) -> dict[str, Any]:
        """Preview (dry_run=True) or apply rootless ADB debloat/restore with backup and undo scripts."""
        clean_pkgs = [p.strip() for p in packages if p.strip()]
        if not clean_pkgs:
            return {"status": "error", "message": "No packages provided."}

        classified = [self.classify_package(p) for p in clean_pkgs]
        blocked: list[dict[str, str]] = []
        actionable: list[dict[str, str]] = []

        for item in classified:
            tier = item["tier"]
            if not restore and (
                tier in {"protected_system", "unsafe"} or (tier == "expert" and not allow_expert)
            ):
                blocked.append(item)
            else:
                actionable.append(item)

        if dry_run:
            target_prefix = f"adb -s {device_id.strip()} " if device_id.strip() else "adb "
            preview = [
                {
                    **item,
                    "planned_command": (
                        f"{target_prefix}shell pm enable {item['package']}"
                        if restore
                        else f"{target_prefix}shell pm disable-user --user 0 {item['package']}"
                    ),
                }
                for item in actionable
            ]
            return {
                "status": "success",
                "mode": "dry_run_restore" if restore else "dry_run_debloat",
                "device_id": device_id.strip(),
                "confirmation_required": True,
                "actionable_count": len(preview),
                "blocked_count": len(blocked),
                "blocked_packages": blocked,
                "preview": preview,
                "message": "Dry-run preview generated. Re-run with dry_run=False to apply changes and write undo scripts.",
            }

        safe_host = (device_id.strip() or "offline").replace(":", "_").replace("/", "_")
        backup_file = self.debloat_dir / f"backup_{safe_host}.json"
        restore_sh = self.debloat_dir / f"restore_{safe_host}.sh"
        restore_ps1 = self.debloat_dir / f"restore_{safe_host}.ps1"

        adb_prefix = f"adb -s {device_id.strip()}" if device_id.strip() else "adb"
        actionable_names = [item["package"] for item in actionable]

        if not restore and actionable_names:
            restore_cmds = [f"{adb_prefix} shell pm enable {pkg}" for pkg in actionable_names]
            backup_payload = {
                "device_id": device_id.strip(),
                "backed_up_at": datetime.now(UTC).isoformat(),
                "packages": actionable_names,
                "restore_commands": restore_cmds,
            }
            backup_file.write_text(json.dumps(backup_payload, indent=2), encoding="utf-8")
            restore_sh.write_text(
                "#!/usr/bin/env sh\nset -e\n" + "\n".join(restore_cmds) + "\n",
                encoding="utf-8",
            )
            restore_ps1.write_text(
                "$ErrorActionPreference = 'Stop'\n" + "\n".join(restore_cmds) + "\n",
                encoding="utf-8",
            )

        results: list[dict[str, Any]] = []
        for item in actionable:
            pkg = item["package"]
            adb_args = (
                ["shell", "pm", "enable", pkg]
                if restore
                else ["shell", "pm", "disable-user", "--user", "0", pkg]
            )
            if device_id.strip() and shutil.which("adb"):
                ok, msg = self._run_adb(device_id, adb_args)
                results.append(
                    {
                        "package": pkg,
                        "tier": item["tier"],
                        "action": "enable" if restore else "disable",
                        "applied": ok,
                        "output": msg,
                    }
                )
            else:
                results.append(
                    {
                        "package": pkg,
                        "tier": item["tier"],
                        "action": "enable" if restore else "disable",
                        "applied": False,
                        "output": f"Staged command: {adb_prefix} {' '.join(adb_args)}",
                    }
                )

        return {
            "status": "success",
            "mode": "restore" if restore else "debloat",
            "device_id": device_id.strip(),
            "backup_file": str(backup_file) if not restore and actionable_names else None,
            "restore_script_sh": str(restore_sh) if not restore and actionable_names else None,
            "restore_script_ps1": str(restore_ps1) if not restore and actionable_names else None,
            "blocked_packages": blocked,
            "results": results,
        }

    def restore_from_backup(
        self,
        backup_file: str,
        device_id: str = "",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Restore previously debloated packages from a JSON backup file."""
        path = Path(backup_file)
        if not path.is_file():
            return {"status": "error", "message": f"Backup file not found: {backup_file}"}
        payload = json.loads(path.read_text(encoding="utf-8"))
        packages = [str(p) for p in payload.get("packages", []) if str(p).strip()]
        target_device = device_id.strip() or str(payload.get("device_id", "")).strip()
        return self.apply_debloat(
            packages=packages,
            device_id=target_device,
            dry_run=dry_run,
            restore=True,
        )
