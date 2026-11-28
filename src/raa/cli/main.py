"""RAA command-line interface.

Every command calls the same registry and runtime as MCP and REST. The CLI is
not a second implementation.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table

from raa.config import ProfileName, Settings
from raa.errors import RAAError
from raa.logging import configure_logging
from raa.registry.profiles import ALL_PROFILES
from raa.runtime import Runtime
from raa.services.workspace import sanitize_filename
from raa.version import PROTOCOL_VERSION, __version__

app = typer.Typer(
    name="raa",
    help="RAA - Reverse Android Anything: evidence-first Android application intelligence.",
    no_args_is_help=True,
    add_completion=False,
)
project_app = typer.Typer(help="Create and inspect projects.", no_args_is_help=True)
artifact_app = typer.Typer(help="Ingest and inspect artifacts.", no_args_is_help=True)
tools_app = typer.Typer(help="Discover and call registered tools.", no_args_is_help=True)
recipe_app = typer.Typer(help="Run versioned macro-workflows.", no_args_is_help=True)
source_app = typer.Typer(
    help="Search, inspect and retrieve DEX class representations.",
    no_args_is_help=True,
)
skill_app = typer.Typer(help="List, show and install Agent Skills.", no_args_is_help=True)
serve_app = typer.Typer(help="Start MCP or REST servers.", no_args_is_help=True)
framework_app = typer.Typer(
    help="Framework detection and capability queries.", no_args_is_help=True
)
flutter_app = typer.Typer(help="Flutter asset and symbol inspection.", no_args_is_help=True)
react_native_app = typer.Typer(
    help="React Native bundle and module inspection.", no_args_is_help=True
)
unity_app = typer.Typer(help="Unity asset and IL2CPP metadata inspection.", no_args_is_help=True)
dotnet_app = typer.Typer(help=".NET assembly inspection.", no_args_is_help=True)
native_app = typer.Typer(help="Native library inspection and JNI mapping.", no_args_is_help=True)
ui_app = typer.Typer(help="UI reconstruction and runtime capture.", no_args_is_help=True)
graph_app = typer.Typer(help="Application intelligence graph queries.", no_args_is_help=True)
device_app = typer.Typer(help="Manage test devices, leases, and snapshots.", no_args_is_help=True)
dynamic_app = typer.Typer(
    help="Dynamic analysis, app execution, and memory dumps.", no_args_is_help=True
)
api_app = typer.Typer(help="API reverse-engineering studio.", no_args_is_help=True)
unpack_app = typer.Typer(
    help="Unpacking, deobfuscation, and retrace workflows.", no_args_is_help=True
)
diff_app = typer.Typer(help="Semantic artifact diff and change comparison.", no_args_is_help=True)
security_app = typer.Typer(
    help="Security, privacy, SBOM, and threat detection.", no_args_is_help=True
)
test_app = typer.Typer(help="Automated test generation and execution.", no_args_is_help=True)
rebuild_app = typer.Typer(
    help="Controlled APK patching, signing, and rebuild verification.", no_args_is_help=True
)
admin_app = typer.Typer(
    help="Administrative operations, engine verification, and audit queries.", no_args_is_help=True
)
ai_app = typer.Typer(
    help="On-device AI model inspection, prompts, and AppFunctions.", no_args_is_help=True
)
platform_app = typer.Typer(
    help="Universal platform expansion: iOS, HarmonyOS, PRoot, and Warp block sessions.",
    no_args_is_help=True,
)
swarm_app = typer.Typer(
    help="Multi-agent swarm governance, token budgeting, blackboard, and LoopX state persistence.",
    no_args_is_help=True,
)
cognitive_app = typer.Typer(
    help="Dual-context adversarial audit, Google ADK workflows, IAP monetization & exploit payoff economics.",
    no_args_is_help=True,
)
binary_app = typer.Typer(
    help="Native Ghidra/RetDec decompilers, Malimite Apple reversing, GDB/MI, and device lockscreen controls.",
    no_args_is_help=True,
)
canvas_app = typer.Typer(
    help="Autonomous UI reconstruction, Google Stitch, Apple HIG, Liquid Glass, Clean Architecture, and Sodu CI/CD.",
    no_args_is_help=True,
)
enterprise_app = typer.Typer(
    help="Enterprise MCP mesh (Postman, GitHub, Playwright, Apify), 7-CLI gateway, Nacos, WASM & mutation guardrails.",
    no_args_is_help=True,
)
offensive_app = typer.Typer(
    help="Offensive security operations, Yaklang playbooks, GUI computer-use & v3 benchmarks.",
    no_args_is_help=True,
)
channel_app = typer.Typer(help="Mobile channels and notification intensity.", no_args_is_help=True)
mcp_mesh_app = typer.Typer(help="External MCP mesh and service connectors.", no_args_is_help=True)
tv_app = typer.Typer(help="Android TV and 10-foot Living Canvas UI studio.", no_args_is_help=True)
debloat_app = typer.Typer(
    help="Rootless UAD-backed Android device debloating and restore.", no_args_is_help=True
)

app.add_typer(project_app, name="project")
app.add_typer(artifact_app, name="artifact")
app.add_typer(tools_app, name="tools")
app.add_typer(recipe_app, name="recipe")
app.add_typer(source_app, name="source")
app.add_typer(skill_app, name="skill")
app.add_typer(skill_app, name="skills")
app.add_typer(serve_app, name="serve")
app.add_typer(framework_app, name="framework")
app.add_typer(flutter_app, name="flutter")
app.add_typer(react_native_app, name="react-native")
app.add_typer(unity_app, name="unity")
app.add_typer(dotnet_app, name="dotnet")
app.add_typer(native_app, name="native")
app.add_typer(ui_app, name="ui")
app.add_typer(graph_app, name="graph")
app.add_typer(device_app, name="device")
app.add_typer(dynamic_app, name="dynamic")
app.add_typer(api_app, name="api")
app.add_typer(unpack_app, name="unpack")
app.add_typer(diff_app, name="diff")
app.add_typer(security_app, name="security")
app.add_typer(test_app, name="test")
app.add_typer(rebuild_app, name="rebuild")
app.add_typer(admin_app, name="admin")
app.add_typer(ai_app, name="ai")
app.add_typer(platform_app, name="platform")
app.add_typer(swarm_app, name="swarm")
app.add_typer(cognitive_app, name="cognitive")
app.add_typer(binary_app, name="binary")
app.add_typer(canvas_app, name="canvas")
app.add_typer(enterprise_app, name="enterprise")
app.add_typer(offensive_app, name="offensive")
app.add_typer(channel_app, name="channel")
app.add_typer(mcp_mesh_app, name="mcp-mesh")
app.add_typer(tv_app, name="tv")
app.add_typer(debloat_app, name="debloat")

console = Console()


@dataclass(slots=True)
class CliState:
    workspace: Path | None = None
    profile: str | None = None
    json_output: bool = False


@app.callback()
def main(
    ctx: typer.Context,
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace directory (default: .raa-workspace).",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Tool profile: minimal, core, full, dynamic, api, ui, admin.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
) -> None:
    if profile is not None and profile not in ALL_PROFILES:
        raise typer.BadParameter(f"Unknown profile '{profile}'. Valid: {', '.join(ALL_PROFILES)}")
    ctx.obj = CliState(workspace=workspace, profile=profile, json_output=json_output)


@app.command()
def version() -> None:
    """Print package and protocol versions."""

    typer.echo(f"raa {__version__}")
    typer.echo(f"protocol {PROTOCOL_VERSION}")


@app.command()
def init(
    ctx: typer.Context,
    ui: bool | None = typer.Option(
        None,
        "--ui/--no-ui",
        help="Launch the Setup & Tool Manager Web UI (auto-launches on first-time setup).",
    ),
) -> None:
    """Create the local workspace and database (and launch Setup UI on first run)."""

    state = _state(ctx)
    ws_root = (state.workspace or Path(".raa-workspace")).expanduser().resolve()
    is_first_run = not (ws_root / "raa.sqlite3").exists()
    runtime = _runtime(state)
    _emit(
        state,
        {
            "workspace": str(runtime.workspace.root),
            "database": str(runtime.database.path),
            "profile": runtime.settings.profile,
            "implemented_tools": runtime.registry.count(),
            "first_run": is_first_run,
        },
        title="Workspace initialized",
    )
    should_launch_ui = (ui is True) or (
        ui is None and is_first_run and runtime.settings.setup_auto_launch
    )
    if should_launch_ui and not state.json_output and not os.environ.get("PYTEST_CURRENT_TEST"):
        _serve_ui_and_open_browser(runtime, open_browser=True)


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Check workspace, database, MCP SDK and engine availability."""

    state = _state(ctx)
    payload = asyncio.run(_invoke(_runtime(state), "admin_doctor", {}))
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    table = Table(title="RAA doctor", show_header=True)
    table.add_column("Check")
    table.add_column("Value")
    for key in (
        "ok",
        "python",
        "platform",
        "profile",
        "workspace",
        "workspace_writable",
        "database_ok",
        "mcp_sdk",
        "implemented_tools",
    ):
        table.add_row(key, str(data.get(key)))
    engines = data.get("engines", {})
    table.add_row("engines", f"{engines.get('installed', 0)}/{engines.get('catalogued', 0)}")
    console.print(table)


@tools_app.command("list")
def tools_list(ctx: typer.Context) -> None:
    """List tools exposed by the selected profile."""

    state = _state(ctx)
    runtime = _runtime(state)
    profile = _profile(state.profile or runtime.settings.profile)
    specs = runtime.registry.for_profile(profile)
    if state.json_output:
        _emit(
            state,
            {
                "profile": profile,
                "items": [
                    {
                        "name": spec.name,
                        "family": spec.family,
                        "title": spec.title,
                        "scopes": sorted(spec.scopes),
                    }
                    for spec in specs
                ],
                "count": len(specs),
            },
        )
        return
    table = Table(title=f"Tools ({profile})")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Family")
    table.add_column("Scopes")
    table.add_column("Title")
    for spec in specs:
        table.add_row(
            spec.name,
            spec.family,
            ", ".join(sorted(spec.scopes)) or "-",
            spec.title,
        )
    console.print(table)


@tools_app.command("show")
def tools_show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Tool name."),
) -> None:
    """Show a tool description and input schema."""

    state = _state(ctx)
    runtime = _runtime(state)
    if not runtime.registry.has(name):
        _raise_not_found(name)
    spec = runtime.registry.get(name)
    payload = {
        "name": spec.name,
        "title": spec.title,
        "description": spec.description,
        "family": spec.family,
        "scopes": sorted(spec.scopes),
        "profiles": sorted(spec.profiles),
        "input_schema": spec.input_schema(),
    }
    _emit(state, payload)


@tools_app.command("call")
def tools_call(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Tool name."),
    args_json: str | None = typer.Option(None, "--args-json", help="Inline JSON arguments."),
    args_file: Path | None = typer.Option(None, "--args-file", help="Path to a JSON object."),
) -> None:
    """Call a tool through the registry."""

    state = _state(ctx)
    if bool(args_json) == bool(args_file):
        raise typer.BadParameter("Provide exactly one of --args-json or --args-file.")
    if args_file:
        try:
            arguments = json.loads(args_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise typer.BadParameter(f"Could not read arguments: {exc}") from exc
    else:
        try:
            arguments = json.loads(args_json or "{}")
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON: {exc}") from exc
    if not isinstance(arguments, dict):
        raise typer.BadParameter("Arguments must be a JSON object.")
    runtime = _runtime(state)
    payload = asyncio.run(_invoke(runtime, name, arguments))
    _emit(state, payload)


@tools_app.command("search")
def tools_search_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search keyword or reversing goal."),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Optional profile filter."),
    family: str | None = typer.Option(None, "--family", "-f", help="Optional family filter."),
    limit: int = typer.Option(20, "--limit", "-l", help="Max tools to return."),
) -> None:
    """Search capability registry by semantic keywords, descriptions, and reversing goals."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "query": query,
        "limit": limit,
    }
    if profile:
        args["profile"] = profile
    if family:
        args["family"] = family
    payload = asyncio.run(_invoke(_runtime(state), "mcp_tool_search", args))
    _emit(state, payload, title=f"Tools Search Results for '{query}'")


@tools_app.command("termux-harness")
def tools_termux_harness_cmd(
    ctx: typer.Context,
    workspace: str = typer.Option(
        "/data/data/com.termux/files/home/raa-harness",
        "--workspace",
        "-w",
        help="PRoot workspace path on device.",
    ),
    rootfs: str = typer.Option("debian_arm64", "--rootfs", "-r", help="Rootfs distribution."),
) -> None:
    """Configure an on-device PRoot reversing and patch harness in Termux."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "workspace_dir": workspace,
        "rootfs_type": rootfs,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "core"), "termux_workspace_harness", args, profile="core")
    )
    _emit(state, payload, title="On-Device Termux Workspace Harness")


@project_app.command("create")
def project_create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Project name."),
    description: str = typer.Option("", "--description", "-d"),
    scope: list[str] = typer.Option(
        [],
        "--scope",
        help="Repeat to grant explicit scopes. Defaults to the safe project set.",
    ),
) -> None:
    """Create a project."""

    state = _state(ctx)
    arguments: dict[str, Any] = {
        "name": name,
        "description": description,
    }
    if scope:
        arguments["scopes"] = scope
    payload = asyncio.run(_invoke(_runtime(state), "project_create", arguments))
    _emit(state, payload, title="Project created")


@project_app.command("list")
def project_list(
    ctx: typer.Context,
    limit: int = typer.Option(50, "--limit", min=1, max=200),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List projects."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(_runtime(state), "project_list", {"limit": limit, "offset": offset})
    )
    _emit(state, payload)


@project_app.command("show")
def project_show(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
) -> None:
    """Show one project and its scopes."""

    state = _state(ctx)
    payload = asyncio.run(_invoke(_runtime(state), "project_get", {"project_id": project_id}))
    _emit(state, payload)


@artifact_app.command("ingest")
def artifact_ingest(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    path: Path = typer.Argument(..., exists=True, dir_okay=False),
) -> None:
    """Ingest an APK/AAB/APKS/XAPK into a project."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "artifact_ingest",
            {"project_id": project_id, "path": str(path)},
        )
    )
    _emit(state, payload, title="Artifact ingested")


@artifact_app.command("list")
def artifact_list(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    limit: int = typer.Option(50, "--limit", min=1, max=200),
) -> None:
    """List artifacts in a project."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "artifact_list",
            {"project_id": project_id, "limit": limit},
        )
    )
    _emit(state, payload)


@artifact_app.command("files")
def artifact_files(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    artifact_id: str = typer.Argument(...),
    pattern: str | None = typer.Option(None, "--pattern", help="Case-insensitive glob."),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
) -> None:
    """List archive members without extracting them."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "artifact_list_files",
            {
                "project_id": project_id,
                "artifact_id": artifact_id,
                "pattern": pattern,
                "limit": limit,
            },
        )
    )
    _emit(state, payload)


@artifact_app.command("playstore-info")
def artifact_playstore_info(
    ctx: typer.Context,
    package_or_url: str = typer.Argument(..., help="Android package ID or play.google.com URL."),
    lang: str = typer.Option("en", "--lang", help="Store listing language code."),
    country: str = typer.Option("us", "--country", help="Store listing country code."),
) -> None:
    """Fetch public Google Play Store metadata for an app."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "playstore_app_info",
            {"package_or_url": package_or_url, "lang": lang, "country": country},
        )
    )
    _emit(state, payload, title="Play Store app info")


@artifact_app.command("playstore-download")
def artifact_playstore_download(
    ctx: typer.Context,
    package_or_url: str = typer.Argument(..., help="Android package ID or play.google.com URL."),
    project_id: str | None = typer.Option(None, "--project-id", "-p", help="Target project ID."),
    provider: str = typer.Option(
        "auto",
        "--provider",
        help="Download provider: auto, avd, adb, apkeep, or gplaycli.",
    ),
    avd_name: str | None = typer.Option(
        None,
        "--avd",
        help="AVD name from AVD Manager to boot and install from Google Play Store.",
    ),
    headless: bool = typer.Option(
        False,
        "--headless",
        help="Launch the AVD emulator headlessly (-no-window).",
    ),
    auto_tap_install: bool = typer.Option(
        True,
        "--auto-tap/--no-auto-tap",
        help="Automatically tap Play Store's Install button on the AVD.",
    ),
    version_code: int | None = typer.Option(None, "--version-code", help="Specific versionCode."),
    split_apk: bool = typer.Option(False, "--split-apk", help="Request split APKs if supported."),
    device_serial: str | None = typer.Option(None, "--device", "-s", help="ADB device serial."),
    auto_ingest: bool = typer.Option(
        True,
        "--ingest/--no-ingest",
        help="Automatically ingest downloaded APK/APKS into project_id.",
    ),
) -> None:
    """Download an Android app from Google Play Store via AVD Manager or fallback provider."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "playstore_download_app",
            {
                "package_or_url": package_or_url,
                "project_id": project_id,
                "provider": provider,
                "avd_name": avd_name,
                "headless": headless,
                "auto_tap_install": auto_tap_install,
                "version_code": version_code,
                "split_apk": split_apk,
                "device_serial": device_serial,
                "auto_ingest": auto_ingest,
            },
        )
    )
    _emit(state, payload, title="Play Store app downloaded")


@artifact_app.command("apkeep-download")
def artifact_apkeep_download(
    ctx: typer.Context,
    package_or_url: str = typer.Argument(..., help="Android package ID or play.google.com URL."),
    project_id: str | None = typer.Option(None, "--project-id", "-p", help="Target project ID."),
    source: str = typer.Option(
        "google-play",
        "--source",
        help="apkeep source: google-play (default), apk-pure, f-droid, or huawei-app-gallery.",
    ),
    version_code: int | None = typer.Option(None, "--version-code", help="Specific versionCode."),
    split_apk: bool = typer.Option(False, "--split-apk", help="Request split APKs if supported."),
    auto_ingest: bool = typer.Option(
        True,
        "--ingest/--no-ingest",
        help="Automatically ingest downloaded APK/APKS into project_id.",
    ),
) -> None:
    """Download an Android app via efforg/apkeep (Google Play first priority)."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "apkeep_download_app",
            {
                "package_or_url": package_or_url,
                "project_id": project_id,
                "source": source,
                "version_code": version_code,
                "split_apk": split_apk,
                "auto_ingest": auto_ingest,
            },
        )
    )
    _emit(state, payload, title="apkeep app downloaded")


@app.command("analyze")
def analyze(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    artifact_id: str = typer.Argument(...),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for completion."),
) -> None:
    """Run the built-in static analysis and print the report summary."""

    state = _state(ctx)
    runtime = _runtime(state)

    async def run() -> dict[str, Any]:
        started = await runtime.invoke(
            "analysis_start",
            {"project_id": project_id, "artifact_id": artifact_id},
            surface="cli",
        )
        if not wait:
            return started.model_dump(mode="json")
        job = await runtime.analysis.wait(project_id, started.data["id"])
        if job.status.value != "completed":
            return {
                "job": job.model_dump(mode="json"),
                "report": None,
            }
        report = await runtime.invoke(
            "analysis_get_report",
            {"project_id": project_id, "job_id": job.id},
            surface="cli",
        )
        return {
            "job": job.model_dump(mode="json"),
            "report": report.model_dump(mode="json"),
        }

    payload = asyncio.run(run())
    if state.json_output:
        _emit(state, payload)
        return
    report = payload.get("report")
    if not report:
        console.print(Pretty(payload))
        return
    data = report["data"]
    table = Table(title="Analysis report")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Report", data["report_id"])
    table.add_row("Artifact", data["filename"])
    table.add_row("Type", data["artifact_type"])
    table.add_row("SHA-256", data["sha256"])
    summary = data.get("summary", {})
    table.add_row("Package", str(summary.get("package", "-")))
    table.add_row(
        "SDK",
        f"min {summary.get('min_sdk', '-')} / target {summary.get('target_sdk', '-')}",
    )
    table.add_row("Exported components", str(summary.get("exported_component_count", "-")))
    table.add_row("Deep links", str(summary.get("deep_link_count", "-")))
    table.add_row("Frameworks", ", ".join(item["id"] for item in data["frameworks"]) or "-")
    table.add_row("Packers", ", ".join(item["id"] for item in data["packers"]) or "-")
    table.add_row("Findings", str(len(data["findings"])))
    table.add_row("Evidence", str(len(data["evidence_ids"])))
    console.print(table)
    for finding in data["findings"]:
        console.print(f"  [{finding['severity']}] {finding['title']}: {finding['detail']}")


@app.command("report")
def report(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    format: str = typer.Option("markdown", "--format", "-f"),
    filename: str | None = typer.Option(None, "--filename"),
) -> None:
    """Export a completed report to the workspace."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "report_generate",
            {
                "project_id": project_id,
                "job_id": job_id,
                "format": format,
                "filename": sanitize_filename(filename) if filename else None,
            },
        )
    )
    _emit(state, payload, title="Report exported")


@app.command("manifest")
def manifest(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
) -> None:
    """Print decoded manifest metadata from a completed analysis job."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "android_get_manifest",
            {"project_id": project_id, "job_id": job_id},
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    application = data["application"]
    table = Table(title=f"Manifest - {data.get('package') or 'unknown package'}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row(
        "Version", f"{data.get('version_name') or '-'} ({data.get('version_code') or '-'})"
    )
    table.add_row(
        "SDK", f"min {data.get('min_sdk') or '-'} / target {data.get('target_sdk') or '-'}"
    )
    table.add_row("Debuggable", str(application.get("debuggable")))
    table.add_row("Allow backup", str(application.get("allow_backup")))
    table.add_row("Cleartext traffic", str(application.get("effective_cleartext_traffic")))
    table.add_row("Network config", str(application.get("network_security_config") or "-"))
    table.add_row("Permissions", f"{len(data.get('requested_permissions', []))} requested")
    table.add_row("Components", str(len(data.get("components", []))))
    table.add_row("Deep links", str(len(data.get("deep_links", []))))
    console.print(table)


@app.command("components")
def components(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    kind: str | None = typer.Option(None, "--kind", help="Filter by component kind."),
    exported_only: bool = typer.Option(
        False,
        "--exported-only",
        help="Only effectively exported, enabled components.",
    ),
) -> None:
    """List manifest components and their exported status."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "android_list_components",
            {
                "project_id": project_id,
                "job_id": job_id,
                "kind": kind,
                "exported_only": exported_only,
                "limit": 500,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    table = Table(title=f"Components ({data['total']} matching, {data['exported_total']} exported)")
    table.add_column("Kind")
    table.add_column("Name", style="cyan")
    table.add_column("Exported")
    table.add_column("Source")
    table.add_column("Guard")
    table.add_column("Launcher")
    for component in data["components"]:
        guard = component.get("permission") or component.get("read_permission") or "-"
        table.add_row(
            component["kind"],
            component["name"],
            str(component["effective_exported"]),
            component["exported_source"],
            guard,
            str(component["launcher"]),
        )
    console.print(table)


@app.command("permissions")
def permissions(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
) -> None:
    """List requested permissions, declared permissions and features."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "android_list_permissions",
            {"project_id": project_id, "job_id": job_id},
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    table = Table(title="Permissions and features")
    table.add_column("Type")
    table.add_column("Name", style="cyan")
    table.add_column("Detail")
    for permission in data["requested"]:
        detail = "requested"
        if permission.get("max_sdk_version") is not None:
            detail += f" (maxSdk {permission['max_sdk_version']})"
        table.add_row("requested", permission["name"], detail)
    for permission in data["declared"]:
        detail = str(permission.get("protection_level") or "declared")
        table.add_row("declared", permission["name"], detail)
    for feature in data["features"]:
        detail = "required" if feature["required"] else "optional"
        table.add_row("feature", feature["name"], detail)
    console.print(table)


@app.command("resources")
def resources(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    type: str | None = typer.Option(None, "--type", help="Filter by resource type."),
    name: str | None = typer.Option(None, "--name", help="Filter by exact resource name."),
    config: str | None = typer.Option(None, "--config", help="Filter by configuration label."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    """List decoded resources with type, configuration and default values."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "android_list_resources",
            {
                "project_id": project_id,
                "job_id": job_id,
                "type": type,
                "name": name,
                "config": config,
                "limit": limit,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    summary = data["summary"]
    table = Table(
        title=(
            f"Resources ({data['total']} matching, {summary['entry_count']} IDs, "
            f"{summary['value_count']} variants)"
        )
    )
    table.add_column("Type")
    table.add_column("Name", style="cyan")
    table.add_column("ID")
    table.add_column("Variants", justify="right")
    table.add_column("Default")
    for item in data["resources"]:
        value = item.get("default_value")
        if value is not None:
            rendered = str(value.get("value"))
        elif item["complex"]:
            rendered = "complex"
        else:
            rendered = "-"
        table.add_row(
            item["type"],
            item["name"],
            item["resource_id"],
            str(item["variant_count"]),
            rendered,
        )
    console.print(table)


@app.command("resource")
def resource(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    identifier: str = typer.Argument(..., help="Resource ID (0x...) or exact name."),
    type: str | None = typer.Option(None, "--type", help="Type for ambiguous names."),
    config: str | None = typer.Option(None, "--config", help="Only this configuration."),
) -> None:
    """Show every configuration variant of one resource."""

    state = _state(ctx)
    arguments: dict[str, Any] = {"project_id": project_id, "job_id": job_id}
    if identifier.lower().startswith("0x"):
        arguments["resource_id"] = identifier
    else:
        arguments["name"] = identifier
        arguments["type"] = type
    arguments["config"] = config
    payload = asyncio.run(_invoke(_runtime(state), "android_get_resource", arguments))
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    table = Table(title=f"{data['type']}/{data['name']} ({data['resource_id']})")
    table.add_column("Config")
    table.add_column("Kind")
    table.add_column("Value")
    table.add_column("File reference")
    for variant in data["variants"]:
        value = variant.get("value")
        if value is None:
            rendered = f"complex ({variant['map_count']} maps)"
        else:
            rendered = str(value.get("value"))
        table.add_row(
            variant["config"],
            variant["value"]["type"] if value is not None else "complex",
            rendered,
            variant.get("file_reference") or "-",
        )
    console.print(table)


@source_app.command("search")
def source_search(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    query: str = typer.Argument(..., help="Class, member, descriptor or string fragment."),
    kind: str | None = typer.Option(
        None,
        "--kind",
        help="Restrict to class, method, field or string.",
    ),
    case_sensitive: bool = typer.Option(False, "--case-sensitive"),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Search indexed DEX classes, members and strings."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_search",
            {
                "project_id": project_id,
                "job_id": job_id,
                "query": query,
                "kind": kind,
                "case_sensitive": case_sensitive,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    table = Table(title=f"Source search ({data['total']} matches)")
    table.add_column("Kind")
    table.add_column("Class", style="cyan")
    table.add_column("Symbol")
    table.add_column("Descriptor / value")
    table.add_column("DEX")
    for item in data["results"]:
        symbol = item.get("name") or item.get("class") or item.get("value") or "-"
        descriptor = item.get("descriptor") or item.get("value") or "-"
        table.add_row(
            item["kind"],
            item.get("class") or "-",
            str(symbol),
            str(descriptor),
            item["dex_file"],
        )
    console.print(table)


@source_app.command("class")
def source_class(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    class_name: str = typer.Argument(..., help="Dotted class name or JVM descriptor."),
    include_source: bool = typer.Option(
        False,
        "--include-source",
        help="Run JADX and include bounded decompiled class source.",
    ),
    source_limit: int = typer.Option(100_000, "--source-limit", min=1, max=500_000),
    limit: int = typer.Option(100, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Show one class with declared fields and methods."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_get_class",
            {
                "project_id": project_id,
                "job_id": job_id,
                "class_name": class_name,
                "include_source": include_source,
                "source_limit": source_limit,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    console.print(f"[bold]{data['name']}[/bold] ({data['descriptor']})")
    console.print(
        f"  superclass={data.get('superclass') or '-'}  "
        f"interfaces={', '.join(data['interfaces']) or '-'}  "
        f"source={data.get('source_file') or '-'}  dex={data['dex_file']}"
    )
    console.print(f"  access={', '.join(data['access']) or '-'}")
    if data["fields"]:
        fields = Table(title=f"Fields ({data['field_total']})")
        fields.add_column("Name", style="cyan")
        fields.add_column("Type")
        fields.add_column("Access")
        for item in data["fields"]:
            fields.add_row(item["name"], item["descriptor"], ", ".join(item["access"]))
        console.print(fields)
    if data["methods"]:
        methods = Table(title=f"Methods ({data['method_total']})")
        methods.add_column("Name", style="cyan")
        methods.add_column("Descriptor")
        methods.add_column("Access")
        methods.add_column("Code")
        for item in data["methods"]:
            methods.add_row(
                item["name"],
                item["descriptor"],
                ", ".join(item["access"]),
                "yes" if item["has_code"] else "no",
            )
        console.print(methods)


@source_app.command("method")
def source_method(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    class_name: str = typer.Argument(...),
    method_name: str = typer.Argument(...),
    descriptor: str | None = typer.Option(None, "--descriptor"),
    include_source: bool = typer.Option(False, "--include-source"),
    source_limit: int = typer.Option(100_000, "--source-limit", min=1, max=500_000),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Show one method with bounded references and optional decompiled source."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_get_method",
            {
                "project_id": project_id,
                "job_id": job_id,
                "class_name": class_name,
                "method_name": method_name,
                "descriptor": descriptor,
                "include_source": include_source,
                "source_limit": source_limit,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    console.print(f"[bold]{data['class']}#{data['method']}[/bold]")
    for item in data["methods"]:
        console.print(
            f"  descriptor={item['descriptor']}  access={', '.join(item['access']) or '-'}  "
            f"code={'yes' if item['has_code'] else 'no'}"
        )
    table = Table(title=f"References ({data['total']})")
    table.add_column("Direction")
    table.add_column("Kind")
    table.add_column("Peer", style="cyan")
    table.add_column("Offset", justify="right")
    table.add_column("DEX")
    for item in data["references"]:
        peer = (
            f"{item['from_class']}#{item['from_method']}"
            if item["direction"] == "outgoing"
            else item["target"]
        )
        table.add_row(
            item["direction"],
            item["kind"],
            peer,
            str(item["offset"]),
            item["dex_file"],
        )
    console.print(table)
    source = data.get("source")
    if source:
        console.print(f"[bold]Decompiled source[/bold] ({source['file_reference']})")
        console.print(source["text"])


@source_app.command("smali")
def source_smali(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    class_name: str = typer.Argument(..., help="Dotted class name or JVM descriptor."),
    limit: int = typer.Option(100_000, "--limit", min=1, max=500_000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Decode one class to Smali with Apktool."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_get_smali",
            {
                "project_id": project_id,
                "job_id": job_id,
                "class_name": class_name,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    console.print(
        f"[bold]{data['class']}[/bold]  engine={data['engine_id']}  "
        f"file={data['file_reference']}  bytes={data['byte_count']}"
    )
    console.print(data["text"])


@source_app.command("refs")
def source_refs(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    query: str = typer.Argument(..., help="Class, method, field, type or string fragment."),
    kind: str = typer.Option(
        "any",
        "--kind",
        help="any, method_call, field_access, type_reference or string_reference.",
    ),
    case_sensitive: bool = typer.Option(False, "--case-sensitive"),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Find DEX bytecode references by symbol fragment."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_find_references",
            {
                "project_id": project_id,
                "job_id": job_id,
                "query": query,
                "kind": kind,
                "case_sensitive": case_sensitive,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    table = Table(title=f"DEX references ({data['total']} matches)")
    table.add_column("Kind")
    table.add_column("From", style="cyan")
    table.add_column("Target")
    table.add_column("Offset", justify="right")
    table.add_column("DEX")
    for item in data["references"]:
        table.add_row(
            item["kind"],
            f"{item['from_class']}#{item['from_method']}",
            item["target"],
            str(item["offset"]),
            item["dex_file"],
        )
    console.print(table)


def _source_relation_command(
    ctx: typer.Context,
    *,
    tool: str,
    project_id: str,
    job_id: str,
    class_name: str,
    method_name: str,
    descriptor: str | None,
    limit: int,
    offset: int,
) -> None:
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            tool,
            {
                "project_id": project_id,
                "job_id": job_id,
                "class_name": class_name,
                "method_name": method_name,
                "descriptor": descriptor,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    label = "Callers" if tool.endswith("callers") else "Callees"
    rows = data["callers"] if tool.endswith("callers") else data["callees"]
    table = Table(title=f"{label} of {class_name}#{method_name} ({data['total']})")
    table.add_column("Class", style="cyan")
    table.add_column("Method")
    table.add_column("Descriptor")
    table.add_column("Sites", justify="right")
    table.add_column("DEX")
    for item in rows:
        table.add_row(
            item.get("class") or "-",
            item.get("method") or "-",
            item.get("descriptor") or "-",
            str(item["call_site_count"]),
            item.get("dex_file") or "indexed",
        )
    console.print(table)
    if data.get("note"):
        console.print(data["note"])


@source_app.command("callers")
def source_callers(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    class_name: str = typer.Argument(...),
    method_name: str = typer.Argument(...),
    descriptor: str | None = typer.Option(None, "--descriptor"),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List distinct methods that call the given method."""

    _source_relation_command(
        ctx,
        tool="source_get_callers",
        project_id=project_id,
        job_id=job_id,
        class_name=class_name,
        method_name=method_name,
        descriptor=descriptor,
        limit=limit,
        offset=offset,
    )


@source_app.command("callees")
def source_callees(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    class_name: str = typer.Argument(...),
    method_name: str = typer.Argument(...),
    descriptor: str | None = typer.Option(None, "--descriptor"),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List distinct methods called by the given method."""

    _source_relation_command(
        ctx,
        tool="source_get_callees",
        project_id=project_id,
        job_id=job_id,
        class_name=class_name,
        method_name=method_name,
        descriptor=descriptor,
        limit=limit,
        offset=offset,
    )


@source_app.command("file")
def source_file(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    file_path: str = typer.Argument(..., help="Relative path inside the workspace or archive."),
    source: str = typer.Option("auto", "--source", help="auto, archive or workspace."),
    limit: int = typer.Option(100_000, "--limit", min=1, max=500_000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Retrieve a decoded source, resource or archive file."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_get_file",
            {
                "project_id": project_id,
                "job_id": job_id,
                "file_path": file_path,
                "source": source,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    if state.json_output:
        _emit(state, payload)
        return
    data = payload["data"]
    console.print(
        f"[bold]{data['file_path']}[/bold] (source: {data['source']}, {data['byte_count']} bytes)"
    )
    if data["is_binary"]:
        console.print("[yellow]Binary file; showing character representation[/yellow]")
    console.print(data["text"])


@source_app.command("hierarchy")
def source_hierarchy(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    class_name: str = typer.Argument(...),
    direction: str = typer.Option("both", "--direction", "-d", help="up, down, or both."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Retrieve inheritance and interface hierarchy for a class."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_get_hierarchy",
            {
                "project_id": project_id,
                "job_id": job_id,
                "class_name": class_name,
                "direction": direction,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title=f"Class hierarchy: {class_name}")


@source_app.command("xrefs")
def source_xrefs(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    symbol: str = typer.Argument(..., help="Symbol or entity ID to query."),
    kind: str | None = typer.Option(None, "--kind", "-k", help="Relationship kind filter."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Find cross-references to a symbol or entity with kind and confidence."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "source_get_xrefs",
            {
                "project_id": project_id,
                "job_id": job_id,
                "symbol": symbol,
                "kind": kind,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title=f"Cross-references: {symbol}")


@source_app.command("rename-symbol")
def source_rename_symbol_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    original: str = typer.Argument(..., help="Original obfuscated symbol name."),
    renamed: str = typer.Argument(..., help="Human-readable renamed identifier."),
    symbol_type: str = typer.Option(
        "class", "--type", "-t", help="Symbol type: class, method, field."
    ),
    export_mapping: bool = typer.Option(
        False, "--export-mapping", help="Export updated mapping.txt."
    ),
) -> None:
    """Rename an obfuscated symbol and propagate across project views."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "symbol_type": symbol_type,
        "original_name": original,
        "renamed_name": renamed,
        "export_mapping": export_mapping,
    }
    payload = asyncio.run(_invoke(_runtime(state), "source_rename_symbol", args))
    _emit(state, payload, title="Symbol Deobfuscation Rename")


@source_app.command("wasm-decompile")
def source_wasm_decompile_cmd(
    ctx: typer.Context,
    file_path: Path | None = typer.Option(None, "--file", "-f", help="Path to .wasm file on disk."),
    hex_bytes: str | None = typer.Option(None, "--hex", help="Hex-encoded WASM bytes string."),
) -> None:
    """Decompile embedded WebAssembly (.wasm) modules into WebAssembly Text format (WAT)."""
    state = _state(ctx)
    args: dict[str, Any] = {}
    if file_path:
        args["file_path"] = str(file_path)
    if hex_bytes:
        args["wasm_bytes_hex"] = hex_bytes
    payload = asyncio.run(_invoke(_runtime(state), "wasm_decompile", args))
    _emit(state, payload, title="WebAssembly Disassembly & Inspection")


@graph_app.command("query")
def graph_query(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    root_id: str | None = typer.Option(None, "--root", "-r", help="Starting entity ID."),
    max_depth: int = typer.Option(2, "--depth", min=1, max=5),
    direction: str = typer.Option(
        "outgoing", "--direction", "-d", help="outgoing, incoming, or both."
    ),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Traverse and query the AAIR entity and relationship graph."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "graph_query",
            {
                "project_id": project_id,
                "job_id": job_id,
                "root_id": root_id,
                "max_depth": max_depth,
                "direction": direction,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title="Graph query results")


@graph_app.command("neighborhood")
def graph_neighborhood(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    entity_id: str = typer.Argument(..., help="Target entity ID."),
    radius: int = typer.Option(1, "--radius", "-r", min=1, max=3),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Retrieve local graph neighborhood around an AAIR entity."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "graph_get_neighborhood",
            {
                "project_id": project_id,
                "job_id": job_id,
                "entity_id": entity_id,
                "radius": radius,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title=f"Neighborhood for {entity_id}")


@framework_app.command("capabilities")
def framework_capabilities(
    ctx: typer.Context,
    framework_id: str | None = typer.Option(
        None, "--id", "-i", help="Optional framework identifier."
    ),
) -> None:
    """Query supported operations and limits for frameworks."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "framework_get_capabilities",
            {"framework_id": framework_id},
        )
    )
    _emit(state, payload, title="Framework capabilities")


@framework_app.command("skip-inspect")
def framework_skip_inspect_cmd(
    ctx: typer.Context,
    apk_path: str | None = typer.Option(None, "--apk", "-a", help="Path to APK file."),
    project_id: str | None = typer.Option(None, "--project", "-p", help="Target project ID."),
    no_models: bool = typer.Option(False, "--no-models", help="Skip model reconstruction."),
) -> None:
    """Inspect Skip Swift transpiler signatures and reconstruct Swift models."""
    state = _state(ctx)
    args: dict[str, Any] = {"deobfuscate_models": not no_models}
    if apk_path:
        args["apk_path"] = apk_path
    if project_id:
        args["project_id"] = project_id
    payload = asyncio.run(_invoke(_runtime(state), "skip_swift_framework_inspect", args))
    _emit(state, payload, title="Skip Swift Transpiled Framework Inspection")


@flutter_app.command("assets")
def flutter_assets(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List assets declared in flutter_assets and font manifests."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "flutter_list_assets",
            {"project_id": project_id, "job_id": job_id, "limit": limit, "offset": offset},
        )
    )
    _emit(state, payload, title="Flutter assets")


@flutter_app.command("symbols")
def flutter_symbols(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    use_engine: bool = typer.Option(
        False, "--use-engine", help="Attempt Blutter decompilation when enabled."
    ),
) -> None:
    """Extract Dart snapshot symbols and Flutter engine version."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "flutter_get_symbols",
            {"project_id": project_id, "job_id": job_id, "use_engine": use_engine},
        )
    )
    _emit(state, payload, title="Flutter symbols")


@flutter_app.command("patch-tls")
def flutter_patch_tls_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Source APK artifact ID."),
    output_name: str = typer.Option(
        "patched_tls.apk", "--output-name", "-o", help="Output filename."
    ),
) -> None:
    """Patch BoringSSL TLS verification offsets for Burp/mitmproxy interception."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "flutter_patch_tls",
            {"project_id": project_id, "artifact_id": artifact_id, "output_name": output_name},
        )
    )
    _emit(state, payload, title="Flutter TLS Patch")


@flutter_app.command("dump-strings")
def flutter_dump_strings_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Source APK artifact ID."),
    min_length: int = typer.Option(5, "--min-length", help="Minimum string length."),
) -> None:
    """Scrape ASCII/UTF-8 strings from libapp.so Dart snapshot."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "flutter_dump_strings",
            {"project_id": project_id, "artifact_id": artifact_id, "min_length": min_length},
        )
    )
    _emit(state, payload, title="Flutter Dart Strings")


@flutter_app.command("snapshot")
def flutter_snapshot_cmd(
    ctx: typer.Context,
    snapshot_path: str | None = typer.Option(
        None, "--snapshot-path", "-s", help="Path to snapshot or libapp.so."
    ),
    arch: str = typer.Option("arm64", "--arch", "-a", help="CPU architecture."),
) -> None:
    """Parse Dart AOT snapshot header and extract isolate strings."""
    state = _state(ctx)
    args: dict[str, Any] = {"architecture": arch}
    if snapshot_path:
        args["snapshot_path"] = snapshot_path
    payload = asyncio.run(_invoke(_runtime(state), "flutter_dart_snapshot_inspect", args))
    _emit(state, payload, title="Dart AOT Snapshot Inspection")


@flutter_app.command("ssl-bypass")
def flutter_ssl_bypass_cmd(
    ctx: typer.Context,
    arch: str = typer.Option("arm64", "--arch", "-a", help="Target CPU architecture."),
    libflutter: str | None = typer.Option(
        None, "--libflutter", "-l", help="Path to libflutter.so."
    ),
) -> None:
    """Generate targeted Frida hooks to bypass Flutter BoringSSL verification."""
    state = _state(ctx)
    args: dict[str, Any] = {"architecture": arch}
    if libflutter:
        args["libflutter_path"] = libflutter
    payload = asyncio.run(_invoke(_runtime(state), "flutter_ssl_pinning_bypass_gen", args))
    _emit(state, payload, title="Flutter BoringSSL Pinning Bypass")


@flutter_app.command("proxy-patch")
def flutter_proxy_patch_cmd(
    ctx: typer.Context,
    libflutter: str | None = typer.Option(
        None, "--libflutter", "-l", help="Path to libflutter.so."
    ),
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Proxy host IP."),
    port: int = typer.Option(8080, "--port", "-p", help="Proxy port."),
    output: str | None = typer.Option(None, "--output", "-o", help="Patched library output path."),
) -> None:
    """Patch libflutter.so ELF binary directly to reroute Dart sockets to a proxy."""
    state = _state(ctx)
    args: dict[str, Any] = {"proxy_host": host, "proxy_port": port}
    if libflutter:
        args["libflutter_path"] = libflutter
    if output:
        args["output_path"] = output
    payload = asyncio.run(_invoke(_runtime(state), "flutter_engine_proxy_patch", args))
    _emit(state, payload, title="Flutter Engine Proxy Patch")


@react_native_app.command("bundle")
def react_native_bundle(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    bundle_path: str | None = typer.Option(None, "--bundle-path", help="Custom bundle path."),
) -> None:
    """Inspect React Native JavaScript or Hermes bundle."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "react_native_inspect_bundle",
            {"project_id": project_id, "job_id": job_id, "bundle_path": bundle_path},
        )
    )
    _emit(state, payload, title="React Native bundle")


@react_native_app.command("modules")
def react_native_modules(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
) -> None:
    """List NativeModules, TurboModules, and ReactPackages found in DEX."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "react_native_list_modules",
            {"project_id": project_id, "job_id": job_id},
        )
    )
    _emit(state, payload, title="React Native modules")


@react_native_app.command("hermes-extract")
def react_native_hermes_extract_cmd(
    ctx: typer.Context,
    bundle_path: str | None = typer.Option(
        None, "--bundle-path", "-b", help="Path to APK or bundle."
    ),
) -> None:
    """Scan assets for React Native bundle and detect Hermes bytecode format."""
    state = _state(ctx)
    args: dict[str, Any] = {}
    if bundle_path:
        args["bundle_path"] = bundle_path
    payload = asyncio.run(_invoke(_runtime(state), "rn_hermes_bundle_extract", args))
    _emit(state, payload, title="Hermes Bytecode Bundle Extraction")


@react_native_app.command("hermes-decompile")
def react_native_hermes_decompile_cmd(
    ctx: typer.Context,
    bundle_path: str | None = typer.Option(
        None, "--bundle-path", "-b", help="Path to Hermes bundle."
    ),
    no_secrets: bool = typer.Option(False, "--no-secrets", help="Disable secret harvesting."),
) -> None:
    """Decompile Hermes bytecode into JavaScript AST and scan for secrets."""
    state = _state(ctx)
    args: dict[str, Any] = {"extract_secrets": not no_secrets}
    if bundle_path:
        args["bundle_path"] = bundle_path
    payload = asyncio.run(_invoke(_runtime(state), "rn_hermes_decompile", args))
    _emit(state, payload, title="Hermes Bytecode Decompilation & Secrets")


@unity_app.command("assets")
def unity_assets(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List Unity asset files, streaming assets, and data files."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "unity_list_assets",
            {"project_id": project_id, "job_id": job_id, "limit": limit, "offset": offset},
        )
    )
    _emit(state, payload, title="Unity assets")


@unity_app.command("metadata")
def unity_metadata(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    use_engine: bool = typer.Option(
        False, "--use-engine", help="Attempt Il2CppDumper analysis when enabled."
    ),
) -> None:
    """Extract IL2CPP metadata summary from global-metadata.dat."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "unity_get_metadata",
            {"project_id": project_id, "job_id": job_id, "use_engine": use_engine},
        )
    )
    _emit(state, payload, title="Unity metadata")


@unity_app.command("dump-metadata")
def unity_dump_metadata_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Source APK artifact ID."),
) -> None:
    """Parse Il2Cpp global-metadata.dat and dump C# class prototypes."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "unity_dump_metadata",
            {"project_id": project_id, "artifact_id": artifact_id},
        )
    )
    _emit(state, payload, title="Unity Il2Cpp Metadata")


@dotnet_app.command("assemblies")
def dotnet_assemblies(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List managed .NET assemblies (DLLs) in the container."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "dotnet_list_assemblies",
            {"project_id": project_id, "job_id": job_id, "limit": limit, "offset": offset},
        )
    )
    _emit(state, payload, title=".NET assemblies")


@dotnet_app.command("type")
def dotnet_type(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    assembly_name: str = typer.Argument(..., help="Assembly file name (e.g. 'App.dll')."),
    type_name: str | None = typer.Option(None, "--type-name", "-t", help="Full type name."),
    decompile: bool = typer.Option(False, "--decompile", help="Attempt ILSpy decompilation."),
) -> None:
    """Inspect or decompile a managed .NET type."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "dotnet_get_type",
            {
                "project_id": project_id,
                "job_id": job_id,
                "assembly_name": assembly_name,
                "type_name": type_name,
                "decompile": decompile,
            },
        )
    )
    _emit(state, payload, title=".NET type")


@native_app.command("analyze")
def native_analyze(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    library_path: str = typer.Argument(..., help="Path to .so file within the APK."),
) -> None:
    """Inspect ELF header, architecture, machine, bitness and endianness."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "native_analyze_library",
            {"project_id": project_id, "job_id": job_id, "library_path": library_path},
        )
    )
    _emit(state, payload, title="Native library analysis")


@native_app.command("symbols")
def native_symbols(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    library_path: str = typer.Argument(..., help="Path to .so file within the APK."),
    kind: str = typer.Option("all", "--kind", help="all, exported, imported or jni."),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Extract exported, imported, and JNI symbols from an ELF shared library."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "native_get_symbols",
            {
                "project_id": project_id,
                "job_id": job_id,
                "library_path": library_path,
                "kind": kind,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title="Native symbols")


@native_app.command("jni-map")
def native_jni_map(
    ctx: typer.Context,
    project_id: str = typer.Argument(...),
    job_id: str = typer.Argument(...),
    status: str = typer.Option("all", "--status", help="all, bound, dynamic or unresolved."),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Correlate declared Java/Kotlin native methods to native library symbols."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "jni_map",
            {
                "project_id": project_id,
                "job_id": job_id,
                "status": status,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title="JNI mapping")


@native_app.command("libraries")
def native_libraries_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Inventory native shared libraries (.so) across all supported ABIs."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "native_list_libraries", args))
    _emit(state, payload, title="Native Library Inventory")


@ui_app.command("screens")
def ui_screens(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
    runtime_only: bool = typer.Option(False, "--runtime-only", help="Show only runtime screens."),
) -> None:
    """List static candidate screens and observed runtime screens."""
    state = _state(ctx)
    filter_rt = True if runtime_only else None
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_list_screens",
            {
                "project_id": project_id,
                "job_id": job_id,
                "limit": limit,
                "offset": offset,
                "filter_runtime": filter_rt,
            },
        )
    )
    _emit(state, payload, title="UI Screens")


@ui_app.command("screen")
def ui_screen(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    screen_id: str = typer.Argument(..., help="Target screen ID."),
) -> None:
    """Retrieve detailed screen model with regions and provenance."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_get_screen",
            {"project_id": project_id, "job_id": job_id, "screen_id": screen_id},
        )
    )
    _emit(state, payload, title=f"Screen: {screen_id}")


@ui_app.command("assets")
def ui_assets(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    kind: str | None = typer.Option(None, "--kind", "-k", help="Asset kind filter."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List UI assets (layouts, drawables, fonts, strings, themes)."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_list_assets",
            {
                "project_id": project_id,
                "job_id": job_id,
                "kind": kind,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title="UI Assets")


@ui_app.command("hierarchy")
def ui_hierarchy(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    screen_id: str | None = typer.Option(None, "--screen", "-s", help="Screen ID."),
    capture_id: str | None = typer.Option(None, "--capture", "-c", help="Capture ID."),
) -> None:
    """Retrieve UIAutomator accessibility hierarchy tree."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_get_hierarchy",
            {
                "project_id": project_id,
                "job_id": job_id,
                "screen_id": screen_id,
                "capture_id": capture_id,
            },
        )
    )
    _emit(state, payload, title="UI Hierarchy")


@ui_app.command("ocr")
def ui_ocr(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    screen_id: str | None = typer.Option(None, "--screen", "-s", help="Screen ID."),
    capture_id: str | None = typer.Option(None, "--capture", "-c", help="Capture ID."),
) -> None:
    """Retrieve OCR text and bounding box regions."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_get_ocr",
            {
                "project_id": project_id,
                "job_id": job_id,
                "screen_id": screen_id,
                "capture_id": capture_id,
            },
        )
    )
    _emit(state, payload, title="UI OCR")


@ui_app.command("correlate")
def ui_correlate(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    screen_id: str | None = typer.Option(None, "--screen", "-s", help="Screen ID filter."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Retrieve correlations linking UI components and layouts to code."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_get_source_correlations",
            {
                "project_id": project_id,
                "job_id": job_id,
                "screen_id": screen_id,
                "limit": limit,
                "offset": offset,
            },
        )
    )
    _emit(state, payload, title="UI Source Correlations")


@ui_app.command("coverage")
def ui_coverage(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
) -> None:
    """Report exploration coverage across discovered and visited screens."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_get_coverage",
            {"project_id": project_id, "job_id": job_id},
        )
    )
    _emit(state, payload, title="UI Coverage Report")


@ui_app.command("compare")
def ui_compare(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    screen_a: str = typer.Argument(..., help="First screen ID."),
    screen_b: str = typer.Argument(..., help="Second screen ID."),
) -> None:
    """Compare two screens across visual IoU, OCR, and structural fidelity."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_compare_screens",
            {
                "project_id": project_id,
                "job_id": job_id,
                "screen_a_id": screen_a,
                "screen_b_id": screen_b,
            },
        )
    )
    _emit(state, payload, title="Screen Comparison")


@ui_app.command("to-code")
def ui_to_code_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    job_id: str = typer.Argument(..., help="Completed analysis job ID."),
    screen_id: str = typer.Argument(..., help="Screen ID to export."),
    target: str = typer.Option(
        "compose", "--target", "-t", help="compose, flutter, react_native, html."
    ),
) -> None:
    """Export screen to Jetpack Compose, Flutter, React Native, or HTML."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "ui_to_code",
            {"project_id": project_id, "job_id": job_id, "screen_id": screen_id, "target": target},
        )
    )
    _emit(state, payload, title=f"UI-to-Code ({target})")


@ui_app.command("capture")
def ui_capture_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str | None = typer.Option(None, "--device-id", "-d", help="Leased device ID."),
    screen_name: str = typer.Option("MainScreen", "--screen-name", "-s", help="Screen name."),
) -> None:
    """Capture running application screen screenshot and view hierarchy."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "ui"),
            "ui_runtime_capture",
            {"project_id": project_id, "device_id": device_id, "screen_name": screen_name},
            profile="ui",
        )
    )
    _emit(state, payload, title="Runtime UI Capture")


@ui_app.command("webview")
def ui_webview_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str | None = typer.Option(None, "--device-id", "-d", help="Leased device ID."),
    port: int = typer.Option(9222, "--port", "-p", help="CDP remote debugging port."),
) -> None:
    """Inspect embedded Android WebViews via Chrome DevTools Protocol."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "ui"),
            "ui_webview_inspect",
            {"project_id": project_id, "device_id": device_id, "port": port},
            profile="ui",
        )
    )
    _emit(state, payload, title="WebView Inspection")


@ui_app.command("redesign")
def ui_redesign_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    screen_id: str = typer.Argument(..., help="Screen ID to redesign."),
    target_framework: str = typer.Option(
        "compose",
        "--framework",
        "-f",
        help="Target framework (compose, react_native, tailwind).",
    ),
) -> None:
    """Synthesize modern 8pt grid redesign with generated production code."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "ui"),
            "ui_redesign_generate",
            {
                "project_id": project_id,
                "screen_id": screen_id,
                "target_framework": target_framework,
            },
            profile="ui",
        )
    )
    _emit(state, payload, title="UI Redesign Generation")


@ui_app.command("visual-compare")
def ui_visual_compare_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    original_screen_id: str = typer.Argument(..., help="Original screen ID."),
    redesigned_screen_id: str = typer.Argument(..., help="Redesigned screen ID."),
) -> None:
    """Compare original and redesigned screens pixel-by-pixel with visual diff."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "ui"),
            "ui_visual_compare",
            {
                "project_id": project_id,
                "original_screen_id": original_screen_id,
                "redesigned_screen_id": redesigned_screen_id,
            },
            profile="ui",
        )
    )
    _emit(state, payload, title="Visual Comparison")


@ui_app.command("prune-ax-tree")
def ui_prune_ax_tree_cmd(
    ctx: typer.Context,
    hierarchy_xml: str | None = typer.Option(None, "--xml", "-x", help="Raw hierarchy XML."),
) -> None:
    """Prune and compress Android layout/accessibility hierarchy for LLM reasoning."""
    state = _state(ctx)
    args: dict[str, Any] = {}
    if hierarchy_xml:
        args["hierarchy_xml"] = hierarchy_xml
    payload = asyncio.run(_invoke(_runtime(state, "ui"), "ui_ax_tree_prune", args, profile="ui"))
    _emit(state, payload, title="AX Tree LLM Pruning")


@ui_app.command("generate-icon")
def ui_generate_icon_cmd(
    ctx: typer.Context,
    name: str = typer.Option("ic_launcher", "--name", "-n", help="Icon base name."),
    background_color: str = typer.Option(
        "#1A73E8", "--bg", "-b", help="Background hex color code."
    ),
    output_dir: str | None = typer.Option(
        None, "--output-dir", "-o", help="Optional target output directory."
    ),
) -> None:
    """Generate complete Android 8+ Adaptive Icon suite and monochrome tint layers."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "icon_name": name,
        "background_color": background_color,
    }
    if output_dir:
        args["output_dir"] = output_dir
    payload = asyncio.run(_invoke(_runtime(state, "ui"), "ui_icon_generate", args, profile="ui"))
    _emit(state, payload, title="Adaptive Icon Suite Generated")


@ui_app.command("generate-banner")
def ui_generate_banner_cmd(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Application title."),
    tagline: str = typer.Option("Modern Mobile Experience", "--tagline", "-t", help="App tagline."),
    primary_color: str = typer.Option(
        "#0D47A1", "--primary", "-p", help="Primary gradient hex color."
    ),
    secondary_color: str = typer.Option(
        "#1976D2", "--secondary", "-s", help="Secondary gradient hex color."
    ),
    accent_color: str = typer.Option("#00E676", "--accent", "-a", help="Accent brand hex color."),
    output_path: str | None = typer.Option(
        None, "--output", "-o", help="Optional path to save SVG banner."
    ),
) -> None:
    """Generate exact 1024x500 Google Play Console compliant feature graphic banner."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "app_title": title,
        "tagline": tagline,
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "accent_color": accent_color,
    }
    if output_path:
        args["output_path"] = output_path
    payload = asyncio.run(_invoke(_runtime(state, "ui"), "ui_banner_generate", args, profile="ui"))
    _emit(state, payload, title="Play Store Feature Graphic Banner Generated")


@ui_app.command("generate-notification-icon")
def ui_generate_notification_icon_cmd(
    ctx: typer.Context,
    name: str = typer.Option(
        "ic_stat_notification", "--name", "-n", help="Notification icon name."
    ),
    output_dir: str | None = typer.Option(
        None, "--output-dir", "-o", help="Optional target output directory."
    ),
) -> None:
    """Generate Android 13+ compliant monochrome alpha-only status bar notification icon."""
    state = _state(ctx)
    args: dict[str, Any] = {"name": name}
    if output_dir:
        args["output_dir"] = output_dir
    payload = asyncio.run(
        _invoke(_runtime(state, "ui"), "ui_notification_icon_generate", args, profile="ui")
    )
    _emit(state, payload, title="Notification Silhouette Icon Generated")


@ui_app.command("semantic-modernize")
def ui_semantic_modernize_cmd(
    ctx: typer.Context,
    xml_content: str = typer.Argument(..., help="Legacy layout XML content string."),
    package_name: str = typer.Option(
        "com.example.ui", "--package", "-p", help="Target package name."
    ),
    screen_name: str = typer.Option(
        "ModernizedScreen", "--name", "-n", help="Composable screen name."
    ),
    edge_to_edge: bool = typer.Option(
        True, "--edge-to-edge/--no-edge-to-edge", help="Enable edge-to-edge insets."
    ),
) -> None:
    """Execute 10-step semantic migration converting legacy XML into Material 3 Jetpack Compose."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "xml_content": xml_content,
        "target_package": package_name,
        "screen_name": screen_name,
        "enable_edge_to_edge": edge_to_edge,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "ui"), "ui_xml_semantic_modernize", args, profile="ui")
    )
    _emit(state, payload, title="Semantic Compose Modernization")


@ui_app.command("parity-diff")
def ui_parity_diff_cmd(
    ctx: typer.Context,
    xml_count: int = typer.Option(5, "--xml-count", "-x", help="Count of original XML elements."),
    compose_count: int = typer.Option(
        5, "--compose-count", "-c", help="Count of Compose elements."
    ),
    has_text: bool = typer.Option(True, "--has-text/--no-text", help="Text label parity status."),
    has_click: bool = typer.Option(
        True, "--has-click/--no-click", help="Click handler parity status."
    ),
) -> None:
    """Evaluate structural and semantic parity score between legacy XML and Compose."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "xml_element_count": xml_count,
        "compose_element_count": compose_count,
        "has_text_parity": has_text,
        "has_click_parity": has_click,
    }
    payload = asyncio.run(_invoke(_runtime(state, "ui"), "ui_parity_diff", args, profile="ui"))
    _emit(state, payload, title="Compose Migration Parity Evaluation")


@ui_app.command("visual-navigate")
def ui_visual_navigate_cmd(
    ctx: typer.Context,
    target_query: str = typer.Argument(..., help="Natural language element description."),
    width: int = typer.Option(1080, "--width", "-w", help="Screen width in pixels."),
    height: int = typer.Option(2400, "--height", "-h", help="Screen height in pixels."),
    action: str = typer.Option(
        "tap", "--action", "-a", help="Touch action: tap, swipe, long_press."
    ),
) -> None:
    """Resolve visual element query to normalized bounding box and tap coordinates."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_query": target_query,
        "screen_width": width,
        "screen_height": height,
        "action_type": action,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "ui"), "ui_visual_grounding_navigate", args, profile="ui")
    )
    _emit(state, payload, title="Visual Grounding Navigation")


@ui_app.command("notification-audit")
def ui_notification_audit_cmd(
    ctx: typer.Context,
    apk_path: str | None = typer.Option(None, "--apk", "-a", help="Path to APK file."),
    res_dir: str | None = typer.Option(None, "--res", "-r", help="Path to res directory."),
) -> None:
    """Audit notification bar icon compliance, contrast ratios, and manifest metadata."""
    state = _state(ctx)
    args: dict[str, Any] = {}
    if apk_path:
        args["apk_path"] = apk_path
    if res_dir:
        args["res_dir"] = res_dir
    payload = asyncio.run(
        _invoke(_runtime(state, "ui"), "ui_notification_icon_audit", args, profile="ui")
    )
    _emit(state, payload, title="Status Bar Notification Icon & Metadata Audit")


@recipe_app.command("list")
def recipe_list(ctx: typer.Context) -> None:
    """List installed recipes."""

    state = _state(ctx)
    payload = asyncio.run(_invoke(_runtime(state), "recipe_list", {}))
    _emit(state, payload)


@recipe_app.command("run")
def recipe_run(
    ctx: typer.Context,
    recipe_id: str = typer.Argument(...),
    args_json: str = typer.Option("{}", "--args-json"),
) -> None:
    """Run a recipe with JSON arguments."""

    state = _state(ctx)
    try:
        arguments = json.loads(args_json)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON: {exc}") from exc
    if not isinstance(arguments, dict):
        raise typer.BadParameter("Arguments must be a JSON object.")
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "recipe_run",
            {"recipe_id": recipe_id, "arguments": arguments},
        )
    )
    _emit(state, payload)


@recipe_app.command("get-run")
def recipe_get_run(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Recipe execution run identifier."),
) -> None:
    """Retrieve execution trace and evidence for a recipe run."""

    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "recipe_get_run",
            {"run_id": run_id},
        )
    )
    _emit(state, payload, title="Recipe Run Trace")


SKILL_TARGETS = {
    "claude-code",
    "claude-desktop",
    "codex",
    "cursor",
    "gemini",
    "vscode",
    "generic",
}


@skill_app.command("list")
def skill_list(ctx: typer.Context) -> None:
    """List available Agent Skills."""

    state = _state(ctx)
    runtime = _runtime(state)
    skills = runtime.skills.discover()
    if state.json_output:
        _emit(
            state,
            {"skills": [skill.summary() for skill in skills], "count": len(skills)},
        )
        return
    table = Table(title="Agent Skills")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Version")
    table.add_column("Tools")
    table.add_column("Description")
    for skill in skills:
        table.add_row(
            skill.id,
            skill.version,
            str(len(skill.tools)),
            skill.description,
        )
    console.print(table)
    if not skills:
        console.print("[dim]No skills found in the repository or packaged resources.[/dim]")


@skill_app.command("show")
def skill_show(
    ctx: typer.Context,
    skill_id: str = typer.Argument(..., help="Skill identifier."),
) -> None:
    """Print a skill's SKILL.md."""

    state = _state(ctx)
    runtime = _runtime(state)
    try:
        skill = runtime.skills.get(skill_id)
    except RAAError as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc
    if state.json_output:
        _emit(state, {**skill.summary(), "content": skill.content})
        return
    typer.echo(skill.content)


@skill_app.command("install")
def skill_install(
    ctx: typer.Context,
    skill_id: str | None = typer.Argument(None, help="Skill identifier."),
    target: str = typer.Option(
        "generic",
        "--target",
        help="Host target: claude-code, claude-desktop, codex, cursor, gemini, vscode or generic.",
    ),
    directory: Path | None = typer.Option(
        None,
        "--dir",
        help="Explicit destination directory. Defaults to <workspace>/skills/<target>.",
    ),
    install_all: bool = typer.Option(
        False,
        "--all",
        help="Install every available skill.",
    ),
) -> None:
    """Copy skills into a workspace-local directory."""

    state = _state(ctx)
    if target not in SKILL_TARGETS:
        raise typer.BadParameter(
            f"Unknown target '{target}'. Valid: {', '.join(sorted(SKILL_TARGETS))}"
        )
    if install_all == bool(skill_id):
        raise typer.BadParameter("Provide a skill id or --all, not both or neither.")
    runtime = _runtime(state)
    destination = directory or (runtime.workspace.root / "skills" / target)
    try:
        selected = (
            runtime.skills.discover() if install_all else [runtime.skills.get(skill_id or "")]
        )
        written = [
            path for skill in selected for path in runtime.skills.install(skill.id, destination)
        ]
    except RAAError as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc
    _emit(
        state,
        {
            "data": {
                "target": target,
                "destination": str(destination.resolve()),
                "skills": [skill.id for skill in selected],
                "files_written": len(written),
            }
        },
        title="Skills installed",
    )


@serve_app.command("mcp")
def serve_mcp(
    ctx: typer.Context,
    transport: str = typer.Option("stdio", "--transport", help="stdio or http."),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8766, "--port", min=1, max=65535),
) -> None:
    """Serve the MCP surface over stdio or Streamable HTTP."""

    state = _state(ctx)
    runtime = _runtime(state)
    profile = _profile(state.profile or runtime.settings.profile)
    if transport == "stdio":
        asyncio.run(_run_stdio(runtime, profile))
        return
    if transport != "http":
        raise typer.BadParameter("transport must be 'stdio' or 'http'")
    import uvicorn

    from raa.mcp.server import build_http_app

    uvicorn.run(
        build_http_app(runtime, profile, host=host),
        host=host,
        port=port,
        log_level=runtime.settings.log_level.lower(),
    )


@serve_app.command("api")
def serve_api(
    ctx: typer.Context,
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port", min=1, max=65535),
) -> None:
    """Serve the REST/OpenAPI surface."""

    state = _state(ctx)
    runtime = _runtime(state)
    import uvicorn

    from raa.api.app import create_app

    uvicorn.run(
        create_app(runtime),
        host=host or runtime.settings.api_host,
        port=port or runtime.settings.api_port,
        log_level=runtime.settings.log_level.lower(),
    )


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _serve_ui_and_open_browser(
    runtime: Runtime,
    *,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool = True,
) -> None:
    import uvicorn

    from raa.api.app import create_app

    target_host = host or runtime.settings.api_host
    target_port = port or runtime.settings.setup_port
    setup_url = f"http://{target_host}:{target_port}/setup"

    if open_browser and not os.environ.get("PYTEST_CURRENT_TEST"):
        threading.Timer(0.8, webbrowser.open, args=(setup_url,)).start()

    if _is_port_open(target_host, target_port):
        console.print(
            f"[green]RAA Setup & Tool Manager UI is already running at[/green] {setup_url}"
        )
        return

    console.print(f"[cyan]Starting RAA Setup & Tool Manager UI at[/cyan] {setup_url}")
    uvicorn.run(
        create_app(runtime),
        host=target_host,
        port=target_port,
        log_level=runtime.settings.log_level.lower(),
    )


@app.command("setup-ui")
def setup_ui_cmd(
    ctx: typer.Context,
    host: str | None = typer.Option(None, "--host", help="Bind host (default from RAA_API_HOST)."),
    port: int | None = typer.Option(
        None, "--port", min=1, max=65535, help="Bind port (default 8765)."
    ),
    open_browser: bool = typer.Option(
        True, "--browser/--no-browser", help="Open Setup UI in browser."
    ),
) -> None:
    """Start the RAA Setup & Tool Manager Web UI server."""
    state = _state(ctx)
    runtime = _runtime(state)
    _serve_ui_and_open_browser(runtime, host=host, port=port, open_browser=open_browser)


@app.command("setup")
def setup(
    ctx: typer.Context,
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="claude-code, claude-desktop, codex, cursor, gemini, vscode or generic.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional file to write. Printed to stdout otherwise.",
    ),
    skip: bool = typer.Option(
        False,
        "--skip",
        help="Mark setup as skipped and use pure-Python fallbacks.",
    ),
    serve: bool = typer.Option(
        True,
        "--serve/--no-serve",
        help="Start the interactive Setup & Tool Manager Web UI server.",
    ),
    host: str | None = typer.Option(None, "--host", help="Bind host for Setup UI."),
    port: int | None = typer.Option(
        None, "--port", min=1, max=65535, help="Bind port for Setup UI."
    ),
    open_browser: bool = typer.Option(
        True, "--browser/--no-browser", help="Open Setup UI in browser."
    ),
) -> None:
    """Launch interactive setup & tool manager web UI, register skip, or print MCP client config."""

    state = _state(ctx)
    runtime = _runtime(state)

    if skip:
        res = runtime.tool_manager.register_skip()
        _emit(state, res)
        return

    if agent is not None or output is not None:
        agent_name = agent or "generic"
        profile = _profile(state.profile or runtime.settings.profile)
        args = [
            "--profile",
            profile,
            "--workspace",
            str(runtime.workspace.root),
            "serve",
            "mcp",
        ]
        command = f"raa {' '.join(args)}"
        config = _client_config(agent_name, command, args)
        if output is None:
            typer.echo(config)
            return
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(config + "\n", encoding="utf-8")
        _emit(state, {"agent": agent_name, "path": str(output)})
        return

    res = runtime.tool_manager.reopen_setup()
    _emit(state, res)
    if serve and not state.json_output and not os.environ.get("PYTEST_CURRENT_TEST"):
        _serve_ui_and_open_browser(runtime, host=host, port=port, open_browser=open_browser)


# --- Device and Dynamic commands ---


@device_app.command("list")
def device_list_cmd(
    ctx: typer.Context,
    device_type: str | None = typer.Option(
        None, "--type", "-t", help="Platform: avd, redroid, physical, emulator, mock."
    ),
    available_only: bool = typer.Option(
        False, "--available-only", help="Filter to only available devices."
    ),
) -> None:
    """List test devices and leases."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "device_list",
            {"device_type": device_type, "available_only": available_only},
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Test Devices")


@device_app.command("lease")
def device_lease_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID to lease."),
    duration: int = typer.Option(3600, "--duration", "-d", help="Lease duration in seconds."),
) -> None:
    """Lease a clean device exclusively for a project."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "device_lease",
            {"project_id": project_id, "device_id": device_id, "duration_seconds": duration},
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Device Leased")


@device_app.command("release")
def device_release_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID to release."),
) -> None:
    """Release a device and restore it to a clean baseline."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "device_release",
            {"project_id": project_id, "device_id": device_id},
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Device Released")


@device_app.command("snapshot")
def device_snapshot_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    name: str = typer.Argument(..., help="Snapshot name."),
    action: str = typer.Option("create", "--action", "-a", help="create or restore."),
) -> None:
    """Create or restore a disposable device snapshot."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "device_snapshot",
            {"project_id": project_id, "device_id": device_id, "name": name, "action": action},
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Device Snapshot")


@dynamic_app.command("install")
def dynamic_install_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Artifact ID."),
    package_name: str | None = typer.Option(None, "--package", "-p", help="Package name."),
) -> None:
    """Install an authorized application build APK onto a leased device."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "app_install",
            {
                "project_id": project_id,
                "device_id": device_id,
                "artifact_id": artifact_id,
                "package_name": package_name,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="App Installed")


@dynamic_app.command("launch")
def dynamic_launch_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    package_name: str = typer.Argument(..., help="Package name."),
    activity: str | None = typer.Option(None, "--activity", help="Activity to start."),
) -> None:
    """Launch an application package/activity on a leased device."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "app_launch",
            {
                "project_id": project_id,
                "device_id": device_id,
                "package_name": package_name,
                "activity": activity,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="App Launched")


@dynamic_app.command("stop")
def dynamic_stop_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    package_name: str = typer.Argument(..., help="Package name."),
) -> None:
    """Stop an application on a leased device."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "app_stop",
            {
                "project_id": project_id,
                "device_id": device_id,
                "package_name": package_name,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="App Stopped")


@dynamic_app.command("instrument-start")
def dynamic_instrument_start_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    package_name: str = typer.Argument(..., help="Package name."),
    hooks: list[str] = typer.Option([], "--hook", "-h", help="Reviewed hook IDs to attach."),
) -> None:
    """Start reviewed instrumentation hooks on an application."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "instrument_start",
            {
                "project_id": project_id,
                "device_id": device_id,
                "package_name": package_name,
                "hook_ids": hooks,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Instrumentation Started")


@dynamic_app.command("instrument-stop")
def dynamic_instrument_stop_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    session_id: str = typer.Argument(..., help="Active instrumentation session ID."),
) -> None:
    """Stop instrumentation and finalize session manifest."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "instrument_stop",
            {"project_id": project_id, "session_id": session_id},
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Instrumentation Stopped")


@dynamic_app.command("events")
def dynamic_events_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    session_id: str = typer.Argument(..., help="Instrumentation session ID."),
    category: str | None = typer.Option(None, "--category", "-c", help="Hook category filter."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Retrieve paginated, redacted runtime interception events."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "runtime_get_events",
            {
                "project_id": project_id,
                "session_id": session_id,
                "category": category,
                "limit": limit,
                "offset": offset,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Runtime Events")


@dynamic_app.command("logcat")
def dynamic_logcat_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Log tag filter."),
    package_name: str | None = typer.Option(None, "--package", "-p", help="Package filter."),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """Retrieve filtered and redacted logcat message stream."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "runtime_get_logcat",
            {
                "project_id": project_id,
                "device_id": device_id,
                "tag": tag,
                "package_name": package_name,
                "limit": limit,
                "offset": offset,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Logcat")


@dynamic_app.command("dump-dex")
def dynamic_dump_dex_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    package_name: str = typer.Argument(..., help="Package name."),
) -> None:
    """Dump memory-mapped runtime DEX bytecode from process memory."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dump_dex",
            {
                "project_id": project_id,
                "device_id": device_id,
                "package_name": package_name,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="DEX Dumps")


@dynamic_app.command("dump-native")
def dynamic_dump_native_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    package_name: str = typer.Argument(..., help="Package name."),
    library: str | None = typer.Option(None, "--library", "-l", help="Specific library name."),
) -> None:
    """Dump loaded native shared libraries from process memory."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dump_native",
            {
                "project_id": project_id,
                "device_id": device_id,
                "package_name": package_name,
                "library_name": library,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Native Dumps")


@dynamic_app.command("dump-heap")
def dynamic_dump_heap_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Device ID."),
    package_name: str = typer.Argument(..., help="Package name."),
    max_bytes: int = typer.Option(10_000_000, "--max-bytes", help="Maximum heap size."),
) -> None:
    """Extract an HPROF memory dump from a running process."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dump_heap",
            {
                "project_id": project_id,
                "device_id": device_id,
                "package_name": package_name,
                "max_bytes": max_bytes,
            },
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Heap Dump")


@dynamic_app.command("inject-gadget")
def dynamic_inject_gadget_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Source APK artifact ID."),
    target_arch: str = typer.Option("arm64-v8a", "--arch", "-a", help="Target CPU architecture."),
) -> None:
    """Embed Frida Gadget shared library into an APK for non-rooted dynamic instrumentation."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dynamic_inject_gadget",
            {"project_id": project_id, "artifact_id": artifact_id, "target_arch": target_arch},
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Frida Gadget Injection")


@dynamic_app.command("dump-storage")
def dynamic_dump_storage_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str | None = typer.Option(None, "--device-id", "-d", help="Optional device ID."),
    target_type: str = typer.Option("all", "--type", "-t", help="all, sqlite, or shared_prefs."),
) -> None:
    """Extract internal SQLite databases and SharedPreferences XML from application sandbox."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dynamic_dump_storage",
            {"project_id": project_id, "device_id": device_id, "target_type": target_type},
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Storage Dump")


@dynamic_app.command("webview-cdp")
def dynamic_webview_cdp_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    package_name: str = typer.Option(
        "com.example.app", "--package", "-p", help="Target package name."
    ),
    port: int = typer.Option(9222, "--port", help="Forwarded CDP port."),
    eval_script: str | None = typer.Option(
        None, "--eval", "-e", help="JavaScript expression to evaluate."
    ),
) -> None:
    """Attach to in-app WebView via Chrome DevTools Protocol."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "package_name": package_name,
        "forwarded_port": port,
    }
    if eval_script:
        args["eval_script"] = eval_script
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_webview_cdp_attach", args, profile="dynamic")
    )
    _emit(state, payload, title="In-App WebView CDP Session")


@dynamic_app.command("perfetto-record")
def dynamic_perfetto_record_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    package_name: str = typer.Option(
        "com.example.app", "--package", "-p", help="Target package name."
    ),
    duration_ms: int = typer.Option(5000, "--duration", "-d", help="Trace duration in ms."),
    device_id: str | None = typer.Option(None, "--device-id", help="Optional device identifier."),
) -> None:
    """Record Perfetto system trace via ADB capturing thread scheduling and Binder IPC."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "package_name": package_name,
        "duration_ms": duration_ms,
    }
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_perfetto_record", args, profile="dynamic")
    )
    _emit(state, payload, title="Perfetto Trace Recording Configured")


@dynamic_app.command("perfetto-query")
def dynamic_perfetto_query_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    package_name: str = typer.Option(
        "com.example.app", "--package", "-p", help="Target package name."
    ),
    events_log: str | None = typer.Option(
        None, "--log", "-l", help="Raw trace event text or ftrace log."
    ),
) -> None:
    """Analyze Perfetto ftrace event logs to detect Binder IPC storms and ANR deadlocks."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "target_package": package_name,
    }
    if events_log:
        args["events_log"] = events_log
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_perfetto_query", args, profile="dynamic")
    )
    _emit(state, payload, title="Perfetto Trace Analysis & Binder Storm Detection")


@dynamic_app.command("iot-sniffer")
def dynamic_iot_sniffer_cmd(
    ctx: typer.Context,
    traffic: str = typer.Argument(..., help="Raw packet capture text or event logs."),
    subnet: str | None = typer.Option(None, "--subnet", "-s", help="Optional subnet filter."),
) -> None:
    """Dissect and parse local multicast/broadcast IoT traffic (mDNS, SSDP, WS-Discovery)."""
    state = _state(ctx)
    args: dict[str, Any] = {"traffic_input": traffic}
    if subnet:
        args["subnet_filter"] = subnet
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "net_iot_sniffer", args, profile="dynamic")
    )
    _emit(state, payload, title="IoT Protocol Dissector")


@dynamic_app.command("wireguard-start")
def dynamic_wireguard_start_cmd(
    ctx: typer.Context,
    package: str = typer.Option("com.example.app", "--package", "-p", help="Target package."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Optional device ID."),
    interface: str = typer.Option("wg0", "--interface", "-i", help="Interface name."),
    server_addr: str = typer.Option("10.0.0.1/24", "--server-addr", help="Server CIDR."),
    client_addr: str = typer.Option("10.0.0.2/32", "--client-addr", help="Client CIDR."),
    listen_port: int = typer.Option(51820, "--port", help="UDP listen port."),
    proxy_port: int = typer.Option(8080, "--proxy-port", help="Traffic redirect proxy port."),
) -> None:
    """Establish zero-trust WireGuard capture tunnel on test device."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_package": package,
        "interface_name": interface,
        "server_address": server_addr,
        "client_address": client_addr,
        "listen_port": listen_port,
        "proxy_port": proxy_port,
    }
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_wireguard_tunnel_start", args, profile="dynamic")
    )
    _emit(state, payload, title="WireGuard Tunnel Started")


@dynamic_app.command("wireguard-stop")
def dynamic_wireguard_stop_cmd(
    ctx: typer.Context,
    package: str = typer.Option("com.example.app", "--package", "-p", help="Target package."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Optional device ID."),
    interface: str = typer.Option("wg0", "--interface", "-i", help="Interface name."),
) -> None:
    """Tear down active WireGuard tunnel on device and restore routing."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_package": package,
        "interface_name": interface,
    }
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_wireguard_tunnel_stop", args, profile="dynamic")
    )
    _emit(state, payload, title="WireGuard Tunnel Stopped")


@dynamic_app.command("fleet-discover")
def dynamic_fleet_discover_cmd(
    ctx: typer.Context,
    subnet: str = typer.Option("192.168.1.0/24", "--subnet", "-s", help="Subnet CIDR to scan."),
    timeout_ms: int = typer.Option(500, "--timeout", "-t", help="Connect timeout in ms."),
    max_hosts: int = typer.Option(32, "--max-hosts", "-m", help="Max hosts to evaluate."),
) -> None:
    """Discover wireless ADB devices across local subnets and orchestrate persistent connections."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "subnet_cidr": subnet,
        "timeout_ms": timeout_ms,
        "max_hosts": max_hosts,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_adb_fleet_discover", args, profile="dynamic")
    )
    _emit(state, payload, title="Wireless ADB Fleet Discovery")


@dynamic_app.command("burp-bridge")
def dynamic_burp_bridge_cmd(
    ctx: typer.Context,
    burp_url: str = typer.Option(
        "http://127.0.0.1:1337", "--burp-url", "-u", help="Burp Suite API endpoint."
    ),
    port: int = typer.Option(8999, "--port", "-p", help="Bridge MCP listener port."),
) -> None:
    """Configure bidirectional MCP bridge between Burp Suite and RAA."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "burp_api_url": burp_url,
        "bridge_port": port,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_burp_mcp_bridge", args, profile="dynamic")
    )
    _emit(state, payload, title="Burp Suite MCP Bridge")


@dynamic_app.command("traffic-audit")
def dynamic_traffic_audit_cmd(
    ctx: typer.Context,
    domain: str | None = typer.Option(None, "--domain", "-d", help="Target domain filter."),
    no_redact: bool = typer.Option(False, "--no-redact", help="Disable PII/credential redaction."),
) -> None:
    """Passively analyze HTTP traffic flows for security flaws with PII redaction."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_domain": domain,
        "redact_pii": not no_redact,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_traffic_passive_audit", args, profile="dynamic")
    )
    _emit(state, payload, title="Passive Traffic Security & PII Audit")


@dynamic_app.command("p2p-tunnel")
def dynamic_p2p_tunnel_cmd(
    ctx: typer.Context,
    device_id: str = typer.Argument(..., help="Target remote Android device ID."),
    tunnel_type: str = typer.Option(
        "iroh_p2p", "--type", "-t", help="P2P protocol: iroh_p2p, wireguard_derp."
    ),
    port: int = typer.Option(55555, "--port", "-p", help="Local listen port for ADB forward."),
) -> None:
    """Establish encrypted P2P NAT-traversal tunnel to remote Android device."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "device_id": device_id,
        "tunnel_type": tunnel_type,
        "local_listen_port": port,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_p2p_device_tunnel", args, profile="dynamic")
    )
    _emit(state, payload, title="P2P Device Tunnel")


@dynamic_app.command("virtual-display-start")
def dynamic_virtual_display_start_cmd(
    ctx: typer.Context,
    name: str = typer.Option("raa-headless-0", "--name", "-n", help="Virtual display name."),
    width: int = typer.Option(1080, "--width", "-w", help="Display width."),
    height: int = typer.Option(2400, "--height", "-h", help="Display height."),
    pkg: str | None = typer.Option(None, "--pkg", "-p", help="Target package to launch."),
) -> None:
    """Create and start a headless Android VirtualDisplay session."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "display_name": name,
        "width": width,
        "height": height,
        "target_package": pkg,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_virtual_display_start", args, profile="dynamic")
    )
    _emit(state, payload, title="Headless VirtualDisplay Started")


@dynamic_app.command("virtual-display-stop")
def dynamic_virtual_display_stop_cmd(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Active VirtualDisplay session ID."),
) -> None:
    """Tear down and release an active headless VirtualDisplay session."""
    state = _state(ctx)
    args: dict[str, Any] = {"session_id": session_id}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_virtual_display_stop", args, profile="dynamic")
    )
    _emit(state, payload, title="Headless VirtualDisplay Stopped")


@dynamic_app.command("gui-crawl")
def dynamic_gui_crawl_cmd(
    ctx: typer.Context,
    target_package: str = typer.Argument(..., help="Target application package name."),
    steps: int = typer.Option(5, "--steps", "-s", help="Maximum autonomous crawling steps."),
    goal: str = typer.Option(
        "Explore main UI and trigger deep activities", "--goal", "-g", help="Agent goal prompt."
    ),
    no_bypass: bool = typer.Option(False, "--no-bypass", help="Disable permission auto-bypass."),
) -> None:
    """Autonomously crawl Flutter/Canvas mobile apps using multimodal visual grounding."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_package": target_package,
        "max_steps": steps,
        "goal_prompt": goal,
        "allow_permission_bypass": not no_bypass,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_gui_agent_crawl", args, profile="dynamic")
    )
    _emit(state, payload, title="Multimodal GUI Crawl Trajectory")


@dynamic_app.command("scrcpy-inject")
def dynamic_scrcpy_inject_cmd(
    ctx: typer.Context,
    action_type: str = typer.Option(
        "touch", "--type", "-t", help="Action type (touch, text, keycode)."
    ),
    x: int = typer.Option(540, "-x", help="X coordinate."),
    y: int = typer.Option(1200, "-y", help="Y coordinate."),
    action: str = typer.Option("down", "--action", "-a", help="Touch action (down, up)."),
    keycode: int | None = typer.Option(None, "--keycode", "-k", help="Android keycode."),
    text: str | None = typer.Option(None, "--text", help="Text to inject."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
    port: int = typer.Option(27183, "--port", "-p", help="Scrcpy control port."),
) -> None:
    """Inject low-latency input event via binary scrcpy control protocol."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action_type": action_type,
        "x": x,
        "y": y,
        "action": action,
        "control_port": port,
    }
    if keycode is not None:
        args["keycode"] = keycode
    if text is not None:
        args["text"] = text
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_scrcpy_inject_fast", args, profile="dynamic")
    )
    _emit(state, payload, title="Scrcpy Fast Action Injection")


@dynamic_app.command("scrcpy-frame")
def dynamic_scrcpy_frame_cmd(
    ctx: typer.Context,
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
    width: int = typer.Option(1080, "--width", "-w", help="Frame width."),
    height: int = typer.Option(2400, "--height", "-h", help="Frame height."),
    codec: str = typer.Option("h264", "--codec", "-c", help="Video codec."),
) -> None:
    """Capture low-latency video frame stream from SurfaceControl."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "width": width,
        "height": height,
        "video_codec": codec,
    }
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_scrcpy_frame_capture", args, profile="dynamic")
    )
    _emit(state, payload, title="Scrcpy Video Frame Capture")


@dynamic_app.command("state-verify")
def dynamic_state_verify_cmd(
    ctx: typer.Context,
    action: str = typer.Option("tap_login", "--action", "-a", help="Transition action name."),
    tolerance: float = typer.Option(0.9, "--tolerance", "-t", help="Minimum parity score."),
) -> None:
    """Verify GUI agent state transitions against deterministic state schemas."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "transition_action": action,
        "match_tolerance": tolerance,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_gui_state_verify", args, profile="dynamic")
    )
    _emit(state, payload, title="Deterministic Mobile State Verification")


@dynamic_app.command("rms-hook")
def dynamic_rms_hook_cmd(
    ctx: typer.Context,
    category: str = typer.Option(
        "crypto", "--category", "-c", help="Subsystem (crypto, keystore, shared_preferences)."
    ),
    package: str | None = typer.Option(None, "--package", "-p", help="Target package name."),
) -> None:
    """Generate pre-configured Frida hooks for Crypto, KeyStore, or SharedPreferences."""
    state = _state(ctx)
    args: dict[str, Any] = {"category": category}
    if package:
        args["target_package"] = package
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_rms_hook_generate", args, profile="dynamic")
    )
    _emit(state, payload, title="RMS Pre-Configured Runtime Hooks")


@dynamic_app.command("rms-override")
def dynamic_rms_override_cmd(
    ctx: typer.Context,
    target_class: str = typer.Option(
        "com.target.app.SecurityCheck", "--class", "-C", help="Target Java class."
    ),
    target_method: str = typer.Option(
        "isDeviceRooted", "--method", "-m", help="Target method name."
    ),
    override_val: str | None = typer.Option(
        "false", "--return", "-r", help="Return value override (true, false, null, string)."
    ),
    no_log: bool = typer.Option(False, "--no-log", help="Disable argument logging."),
) -> None:
    """Codelessly hook target Java method, logging arguments and overriding return value."""
    state = _state(ctx)
    val: Any = override_val
    if override_val is not None:
        if override_val.lower() == "true":
            val = True
        elif override_val.lower() == "false":
            val = False
        elif override_val.lower() in ("null", "none"):
            val = None
    args: dict[str, Any] = {
        "target_class": target_class,
        "target_method": target_method,
        "return_value_override": val,
        "log_arguments": not no_log,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_rms_method_override", args, profile="dynamic")
    )
    _emit(state, payload, title="RMS Dynamic Method Override")


@dynamic_app.command("lamda-connect")
def dynamic_lamda_connect_cmd(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="LAMDA agent daemon host IP."),
    port: int = typer.Option(65000, "--port", "-p", help="LAMDA agent daemon gRPC/WebRTC port."),
    token: str | None = typer.Option(None, "--token", "-t", help="Optional auth token."),
) -> None:
    """Connect to on-device LAMDA agent daemon via WebRTC/gRPC."""
    state = _state(ctx)
    args: dict[str, Any] = {"host": host, "port": port}
    if token:
        args["auth_token"] = token
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_lamda_daemon_connect", args, profile="dynamic")
    )
    _emit(state, payload, title="LAMDA Device Agent Connection")


@dynamic_app.command("lamda-touch")
def dynamic_lamda_touch_cmd(
    ctx: typer.Context,
    event_type: str = typer.Option(
        "tap", "--type", "-t", help="Touch event type (tap, swipe, hold)."
    ),
    x: int = typer.Option(540, "--x", "-x", help="X coordinate."),
    y: int = typer.Option(1200, "--y", "-y", help="Y coordinate."),
    duration: int = typer.Option(50, "--duration", "-d", help="Gesture duration in ms."),
    session_id: str | None = typer.Option(None, "--session", "-s", help="LAMDA session ID."),
) -> None:
    """Dispatch kernel-level multi-touch gestures via LAMDA."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "event_type": event_type,
        "x": x,
        "y": y,
        "duration_ms": duration,
    }
    if session_id:
        args["session_id"] = session_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_lamda_touch_event", args, profile="dynamic")
    )
    _emit(state, payload, title="LAMDA Kernel Touch Dispatch")


@dynamic_app.command("docker-spawn")
def dynamic_docker_spawn_cmd(
    ctx: typer.Context,
    image: str = typer.Option(
        "budtmo/docker-android:emulator_11.0",
        "--image",
        "-i",
        help="Docker Android container image.",
    ),
    device_name: str = typer.Option(
        "Samsung Galaxy S10", "--device", "-d", help="Emulated device profile name."
    ),
    kvm: bool = typer.Option(True, "--kvm/--no-kvm", help="Enable KVM acceleration."),
    adb_port: int = typer.Option(5555, "--adb-port", help="Host ADB port forward."),
    novnc_port: int = typer.Option(6080, "--novnc-port", help="Host noVNC web streaming port."),
) -> None:
    """Spawn ephemeral disposable containerized Android emulator sandbox."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "image": image,
        "device_name": device_name,
        "kvm_enabled": kvm,
        "adb_port": adb_port,
        "novnc_port": novnc_port,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_docker_android_spawn", args, profile="dynamic")
    )
    _emit(state, payload, title="Docker Android Sandbox Spawned")


@dynamic_app.command("docker-teardown")
def dynamic_docker_teardown_cmd(
    ctx: typer.Context,
    container_id: str = typer.Argument(..., help="Target Docker Android container ID."),
    purge_volumes: bool = typer.Option(
        True, "--purge/--no-purge", help="Purge container attached storage volumes."
    ),
) -> None:
    """Tear down and purge containerized Docker Android sandbox."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "container_id": container_id,
        "purge_volumes": purge_volumes,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_docker_android_teardown", args, profile="dynamic")
    )
    _emit(state, payload, title="Docker Android Sandbox Teardown")


@dynamic_app.command("agent-control")
def dynamic_agent_control_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "launch", "--action", "-a", help="Action (launch, ax_tree, eval_js, logcat)."
    ),
    package: str | None = typer.Option(None, "--package", "-p", help="Target package name."),
    script_js: str | None = typer.Option(None, "--script", "-s", help="JavaScript code snippet."),
    log_filter: str | None = typer.Option(None, "--filter", "-f", help="Logcat filter substring."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target ADB device ID."),
) -> None:
    """Dispatch protocol-driven agent actions for mobile automation."""
    state = _state(ctx)
    args: dict[str, Any] = {"action": action}
    if package:
        args["target_package"] = package
    if script_js:
        args["script_js"] = script_js
    if log_filter:
        args["log_filter"] = log_filter
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_agent_device_control", args, profile="dynamic")
    )
    _emit(state, payload, title="Agent Mobile Device Control")


@dynamic_app.command("visual-diff")
def dynamic_visual_diff_cmd(
    ctx: typer.Context,
    original: str | None = typer.Option(None, "--orig", "-o", help="Original screenshot path."),
    rebuilt: str | None = typer.Option(None, "--rebuilt", "-r", help="Rebuilt screenshot path."),
    tolerance: float = typer.Option(0.05, "--tolerance", "-t", help="Tolerance threshold (0-1)."),
) -> None:
    """Audit visual differences between UI screens with font and layout awareness."""
    state = _state(ctx)
    args: dict[str, Any] = {"tolerance": tolerance}
    if original:
        args["original_screenshot_path"] = original
    if rebuilt:
        args["rebuilt_screenshot_path"] = rebuilt
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_visual_diff_audit", args, profile="dynamic")
    )
    _emit(state, payload, title="Visual Regression Layout & Font Diff")


@dynamic_app.command("arm-translate")
def dynamic_arm_translate_cmd(
    ctx: typer.Context,
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target ADB device ID."),
    abi: str = typer.Option("x86_64", "--abi", help="Target emulator ABI (x86, x86_64)."),
    api_level: int = typer.Option(30, "--api", help="Target Android API level."),
    package: str = typer.Option(
        "houdini", "--pkg", help="Translation package (houdini, arm_translation)."
    ),
) -> None:
    """Flash and configure ARM/ARM64 binary translation into x86/x86_64 emulators."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "emulator_abi": abi,
        "android_api": api_level,
        "translation_package": package,
    }
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dyn_emulator_arm_translation_inject",
            args,
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Emulator ARM Translation Injector")


@dynamic_app.command("gui-record")
def dynamic_gui_record_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "record", "--action", "-a", help="Action (record, stop_record, playback)."
    ),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Session ID."),
    fuzz: bool = typer.Option(False, "--fuzz", help="Inject boundary fuzz mutations."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Record human UI interactions or replay action graphs with boundary fuzzing."""
    state = _state(ctx)
    args: dict[str, Any] = {"action": action, "fuzz_boundaries": fuzz}
    if session_id:
        args["session_id"] = session_id
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_gui_record_playback", args, profile="dynamic")
    )
    _emit(state, payload, title="GUI Task Recording & Replay")


@dynamic_app.command("accessibility-agent")
def dynamic_accessibility_agent_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "start", "--action", "-a", help="Action (install_agent, start, stop, status)."
    ),
    package: str | None = typer.Option(None, "--package", "-p", help="Target package name."),
    mode: str = typer.Option("autonomous_fuzz", "--mode", "-m", help="Exploration mode."),
    max_steps: int = typer.Option(50, "--steps", help="Maximum exploration steps."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Control standalone on-device Android Accessibility Service agent."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action": action,
        "exploration_mode": mode,
        "max_steps": max_steps,
    }
    if package:
        args["target_package"] = package
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dyn_ondevice_accessibility_agent",
            args,
            profile="dynamic",
        )
    )
    _emit(state, payload, title="On-Device Accessibility Agent")


@dynamic_app.command("qa-replay")
def dynamic_qa_replay_cmd(
    ctx: typer.Context,
    package: str | None = typer.Option(None, "--package", "-p", help="Target package name."),
    no_perfetto: bool = typer.Option(
        False, "--no-perfetto", help="Disable Perfetto trace capture on FPS drops."
    ),
    fps_drop: int = typer.Option(45, "--fps-threshold", help="FPS drop threshold."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Replay QA test scenario with real-time telemetry and Perfetto trace slicing."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "capture_perfetto_on_drop": not no_perfetto,
        "fps_drop_threshold": fps_drop,
    }
    if package:
        args["target_package"] = package
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_qa_scenario_replay", args, profile="dynamic")
    )
    _emit(state, payload, title="QA Scenario Replay & Perfetto Telemetry")


@dynamic_app.command("appfunction-invoke")
def dynamic_appfunction_invoke_cmd(
    ctx: typer.Context,
    package: str = typer.Option(
        "com.target.application", "--package", "-p", help="Target package."
    ),
    function_id: str = typer.Option("orderFood", "--func", "-f", help="Function ID."),
    caller: str = typer.Option(
        "com.google.android.googlequicksearchbox", "--caller", "-c", help="Caller package."
    ),
    fuzz: bool = typer.Option(False, "--fuzz", help="Fuzz schemas and permission checks."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Invoke or security-fuzz Android 16 AppFunctionDeclaration IPC endpoints."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "package_name": package,
        "function_id": function_id,
        "caller_package": caller,
        "fuzz_mode": fuzz,
    }
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_appfunction_invoke", args, profile="dynamic")
    )
    _emit(state, payload, title="Android 16 AppFunction Invoker & Fuzzer")


@dynamic_app.command("vpn-intercept")
def dynamic_vpn_intercept_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "status", "--action", "-a", help="Action (start, stop, status, inject_ca)."
    ),
    package: str | None = typer.Option(None, "--package", "-p", help="Target package name."),
    host: str = typer.Option("127.0.0.1", "--host", help="Proxy host IP."),
    port: int = typer.Option(8000, "--port", help="Proxy port."),
    cert: str | None = typer.Option(None, "--cert", "-c", help="CA cert file path for inject_ca."),
    system_cert: bool = typer.Option(False, "--system", help="Inject as system root CA."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Control transparent VPN interception, proxy forwarding, and CA cert injection."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action": action,
        "proxy_host": host,
        "proxy_port": port,
        "system_cert": system_cert,
    }
    if package:
        args["package_name"] = package
    if cert:
        args["ca_cert_path"] = cert
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "dyn_httptoolkit_vpn_intercept",
            args,
            profile="dynamic",
        )
    )
    _emit(state, payload, title="HTTP Toolkit Transparent VPN Interception")


@dynamic_app.command("rasp-bypass")
def dynamic_rasp_bypass_cmd(
    ctx: typer.Context,
    package: str = typer.Option(
        "com.target.application", "--package", "-p", help="Target package name."
    ),
    bypasses: str = typer.Option(
        "freerasp,root,debugger,emulator",
        "--bypasses",
        "-b",
        help="Comma-separated bypass modules (freerasp,root,debugger,emulator).",
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="File to save Frida JS."),
    inject: bool = typer.Option(False, "--inject", "-i", help="Auto-inject via Frida."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Generate and deploy targeted Frida RASP and anti-tamper hooks."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_package": package,
        "bypasses": [b.strip() for b in bypasses.split(",") if b.strip()],
        "auto_inject": inject,
    }
    if output:
        args["output_script_path"] = output
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_rasp_bypass_gen", args, profile="dynamic")
    )
    _emit(state, payload, title="Frida RASP & Anti-Tamper Bypass Generator")


@dynamic_app.command("device-mutate")
def dynamic_device_mutate_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "status",
        "--action",
        "-a",
        help="Action: status, dark_mode, network, battery, display, reset_all.",
    ),
    network_profile: str = typer.Option(
        "offline", "--network", help="Network: offline, wifi_only, data_only, online."
    ),
    dark_mode: bool = typer.Option(True, "--dark/--no-dark", help="Enable or disable dark mode."),
    battery_level: int | None = typer.Option(
        None, "--battery-level", min=0, max=100, help="Battery level percent."
    ),
    density: int | None = typer.Option(None, "--density", help="Display density in DPI."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Mutate device runtime properties (dark mode, battery, network, display) for chaos tests."""
    state = _state(ctx)
    params: dict[str, Any] = {
        "enabled": dark_mode,
        "profile": network_profile,
    }
    if battery_level is not None:
        params["level"] = battery_level
    if density is not None:
        params["density"] = density

    args: dict[str, Any] = {
        "action": action,
        "params": params,
    }
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dyn_device_env_mutate", args, profile="dynamic")
    )
    _emit(state, payload, title="Device Runtime Environment Mutator")


@dynamic_app.command("shizuku-exec")
def dynamic_shizuku_exec_cmd(
    ctx: typer.Context,
    command: str = typer.Argument("pm list packages", help="Privileged shell command."),
    action: str = typer.Option(
        "exec", "--action", "-a", help="Action: exec, status, grant_permission, set_appop."
    ),
    package: str | None = typer.Option(None, "--package", "-p", help="Target package name."),
    permission: str | None = typer.Option(None, "--permission", help="Permission name."),
    appop: str | None = typer.Option(None, "--appop", help="AppOp name."),
    mode: str = typer.Option("allow", "--mode", "-m", help="AppOp mode (allow, ignore, deny)."),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Execute privileged operations without root using Shizuku Binder IPC or rish."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "command": command,
        "action": action,
        "mode": mode,
    }
    if package:
        args["package_name"] = package
    if permission:
        args["permission"] = permission
    if appop:
        args["appop"] = appop
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "core"), "shizuku_privileged_exec", args, profile="core")
    )
    _emit(state, payload, title="Shizuku Privileged Execution Bridge")


@dynamic_app.command("termux-bundle")
def dynamic_termux_bundle_cmd(
    ctx: typer.Context,
    action: str = typer.Option("list", "--action", "-a", help="Action: list, deploy, exec, clean."),
    command: str | None = typer.Option(
        None, "--cmd", "-c", help="Command to run using deployed binaries."
    ),
    target_dir: str = typer.Option(
        "/data/local/tmp/raa_bin", "--target-dir", help="On-device destination dir."
    ),
    device_id: str | None = typer.Option(None, "--device", "-d", help="Target device ID."),
) -> None:
    """Deploy, list, execute, or clean standalone on-device ARM64 analysis binaries."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action": action,
        "target_dir": target_dir,
    }
    if command:
        args["command"] = command
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(
        _invoke(_runtime(state, "core"), "termux_ondevice_binary_bundle", args, profile="core")
    )
    _emit(state, payload, title="On-Device Standalone Analysis Binary Bundle")


# --- API Reverse-Engineering Studio Commands ---


@api_app.command("capture-start")
def api_capture_start_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    mode: str = typer.Option(
        "proxy", "--mode", "-m", help="Capture mode: static-only, proxy, in-app, replay."
    ),
    target: list[str] | None = typer.Option(
        None, "--target", "-t", help="Allowed target host pattern (can repeat)."
    ),
) -> None:
    """Start an authorized API capture session."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_capture_start",
            {
                "project_id": project_id,
                "mode": mode,
                "target_hosts": target or [],
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Capture Session Started")


@api_app.command("capture-stop")
def api_capture_stop_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    session_id: str = typer.Argument(..., help="Active capture session ID."),
) -> None:
    """Stop an active API capture session and finalize recorded flows."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_capture_stop",
            {
                "project_id": project_id,
                "session_id": session_id,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Capture Session Stopped")


@api_app.command("capture-status")
def api_capture_status_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    session_id: str | None = typer.Option(
        None, "--session", "-s", help="Optional session ID to query."
    ),
) -> None:
    """Query active or historical capture sessions."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_capture_status",
            {
                "project_id": project_id,
                "session_id": session_id,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Capture Status")


@api_app.command("flows")
def api_flows_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    host: str | None = typer.Option(None, "--host", "-h", help="Filter by host."),
    method: str | None = typer.Option(None, "--method", "-m", help="Filter by HTTP method."),
    status_code: int | None = typer.Option(
        None, "--status", "-s", help="Filter by HTTP status code."
    ),
    limit: int = typer.Option(50, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List normalized, redacted API flows."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_list_flows",
            {
                "project_id": project_id,
                "host": host,
                "method": method,
                "status_code": status_code,
                "limit": limit,
                "offset": offset,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Captured Flows")


@api_app.command("flow")
def api_flow_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    flow_id: str = typer.Argument(..., help="Unique flow identifier."),
) -> None:
    """Retrieve a complete, normalized and redacted flow record."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_get_flow",
            {
                "project_id": project_id,
                "flow_id": flow_id,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Flow Record")


@api_app.command("cluster")
def api_cluster_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
) -> None:
    """Cluster captured flows into stable HTTP operations."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_cluster_operations",
            {"project_id": project_id},
            profile="api",
        )
    )
    _emit(state, payload, title="Clustered Operations")


@api_app.command("operations")
def api_operations_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    host: str | None = typer.Option(None, "--host", "-h", help="Filter by host."),
    method: str | None = typer.Option(None, "--method", "-m", help="Filter by HTTP method."),
) -> None:
    """List discovered API operations."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_list_operations",
            {
                "project_id": project_id,
                "host": host,
                "method": method,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="API Operations")


@api_app.command("operation")
def api_operation_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    operation_id: str = typer.Argument(..., help="Operation identifier."),
) -> None:
    """Get details of a clustered API operation."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_get_operation",
            {
                "project_id": project_id,
                "operation_id": operation_id,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="API Operation")


@api_app.command("infer")
def api_infer_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    operation_id: str | None = typer.Option(
        None, "--operation", "-o", help="Optional operation ID to restrict inference."
    ),
) -> None:
    """Infer JSON/REST schemas across clustered operations."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_infer_schemas",
            {
                "project_id": project_id,
                "operation_id": operation_id,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Inferred Schemas")


@api_app.command("generate-spec")
def api_generate_spec_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    title: str = typer.Option("Reverse-Engineered API", "--title", "-t", help="API title."),
    version: str = typer.Option("1.0.0", "--version", "-v", help="API specification version."),
) -> None:
    """Generate and lint an OpenAPI 3.1 specification."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_generate_spec",
            {
                "project_id": project_id,
                "title": title,
                "version": version,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="OpenAPI 3.1 Specification")


@api_app.command("generate-client")
def api_generate_client_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    language: str = typer.Option(
        "python", "--language", "-l", help="Target client language (python)."
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Optional directory to write client files."
    ),
) -> None:
    """Generate typed client code and run compile/smoke tests."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_generate_client",
            {
                "project_id": project_id,
                "language": language,
                "output_dir": output,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Generated Client")


@api_app.command("test-contracts")
def api_test_contracts_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    operation_id: str | None = typer.Option(
        None, "--operation", "-o", help="Optional operation ID filter."
    ),
) -> None:
    """Run contract conformance tests against recorded flows or live endpoints."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_run_contract_tests",
            {
                "project_id": project_id,
                "operation_id": operation_id,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Contract Test Results")


@api_app.command("diff")
def api_diff_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    candidate_spec: str = typer.Argument(
        ..., help="Path to candidate OpenAPI JSON spec file or inline JSON string."
    ),
) -> None:
    """Diff a candidate OpenAPI spec against the inferred baseline contract."""
    state = _state(ctx)
    candidate_path = Path(candidate_spec)
    if candidate_path.exists() and candidate_path.is_file():
        spec_data = json.loads(candidate_path.read_text(encoding="utf-8"))
    else:
        spec_data = json.loads(candidate_spec)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_diff_contracts",
            {
                "project_id": project_id,
                "candidate_spec": spec_data,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="Contract Diff")


@api_app.command("drift")
def api_drift_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
) -> None:
    """Get accumulated schema and contract drift findings."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_get_drift",
            {"project_id": project_id},
            profile="api",
        )
    )
    _emit(state, payload, title="Contract Drift")


@api_app.command("export-har")
def api_export_har_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Optional output HAR file path."
    ),
) -> None:
    """Export normalized and redacted flows as standard HAR 1.2 with _raa metadata."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_export_har",
            {
                "project_id": project_id,
                "output_path": output,
            },
            profile="api",
        )
    )
    _emit(state, payload, title="HAR Export")


@api_app.command("synthesize")
def api_synthesize_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    title: str = typer.Option("Synthesized API", "--title", help="API title."),
    version: str = typer.Option("1.0.0", "--version", help="API version."),
) -> None:
    """Cluster routes and synthesize schemas into an OpenAPI 3.1 specification."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_synthesize_spec",
            {"project_id": project_id, "title": title, "version": version},
            profile="api",
        )
    )
    _emit(state, payload, title="OpenAPI Spec Synthesis")


@api_app.command("export-postman")
def api_export_postman_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    collection_name: str = typer.Option(
        "Synthesized Collection", "--name", help="Collection name."
    ),
) -> None:
    """Export reverse-engineered routes to Postman Collection v2.1."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "api"),
            "api_export_postman",
            {"project_id": project_id, "collection_name": collection_name},
            profile="api",
        )
    )
    _emit(state, payload, title="Postman Collection Export")


@api_app.command("crawl-docs")
def api_crawl_docs_cmd(
    ctx: typer.Context,
    base_url: str = typer.Argument(..., help="Target API base URL."),
    doc_content: str | None = typer.Option(None, "--content", "-c", help="Documentation text."),
) -> None:
    """Harvest endpoints and schemas from API developer documentation."""
    state = _state(ctx)
    args: dict[str, Any] = {"base_url": base_url}
    if doc_content:
        args["doc_content"] = doc_content
    payload = asyncio.run(
        _invoke(_runtime(state, "api"), "crawl_endpoint_docs", args, profile="api")
    )
    _emit(state, payload, title="Endpoint Documentation Harvest")


@api_app.command("audit-privacy")
def api_audit_privacy_cmd(
    ctx: typer.Context,
    policy_text: str = typer.Argument(..., help="Privacy policy content text."),
    permissions: list[str] = typer.Option(
        [], "--perm", "-p", help="App permissions to cross-reference."
    ),
) -> None:
    """Cross-audit remote privacy policy disclosures against APK permissions."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "policy_text": policy_text,
        "declared_permissions": permissions,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "api"), "crawl_privacy_policy_audit", args, profile="api")
    )
    _emit(state, payload, title="Privacy Policy Cross-Audit")


@api_app.command("ip-intel")
def api_ip_intel_cmd(
    ctx: typer.Context,
    ips: str = typer.Argument(..., help="Comma or space-separated list of IP addresses."),
    threshold: float = typer.Option(60.0, "--threshold", "-t", help="Threat threshold score."),
) -> None:
    """Analyze backend IP addresses for ASN attribution, cloud hosting, and threat scores."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "ip_addresses": ips,
        "threat_threshold": threshold,
    }
    payload = asyncio.run(_invoke(_runtime(state, "api"), "net_ip_intel", args, profile="api"))
    _emit(state, payload, title="Backend IP Intelligence")


@api_app.command("cti-check")
def api_cti_check_cmd(
    ctx: typer.Context,
    targets: list[str] = typer.Argument(..., help="Target IP addresses or domain names to check."),
    threshold: int = typer.Option(40, "--threshold", "-t", help="Threat threshold score (0-100)."),
) -> None:
    """Check IP addresses and domains against CTI threat intelligence feeds."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "targets": targets,
        "threat_threshold": threshold,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "api"), "net_cti_reputation_check", args, profile="api")
    )
    _emit(state, payload, title="CTI Threat Intelligence Check")


@api_app.command("semantic-waf")
def api_semantic_waf_cmd(
    ctx: typer.Context,
    endpoint: str = typer.Argument(..., help="Target mobile API endpoint URL."),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method (GET, POST, etc.)."),
    param: list[str] = typer.Option([], "--param", "-p", help="Query param in key=val format."),
    body: str | None = typer.Option(None, "--body", "-b", help="Request body string."),
) -> None:
    """Audit mobile API endpoint against SQLi, CMDi, NoSQLi, and Path Traversal via AST WAF."""
    state = _state(ctx)
    query_params: dict[str, Any] = {}
    for p in param:
        if "=" in p:
            k, v = p.split("=", 1)
            query_params[k] = v
        else:
            query_params[p] = "1"

    args: dict[str, Any] = {
        "endpoint_url": endpoint,
        "http_method": method,
        "query_params": query_params if query_params else None,
        "request_body": body,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "api"), "api_semantic_waf_audit", args, profile="api")
    )
    _emit(state, payload, title="Semantic WAF & Injection Audit")


@api_app.command("bypass-403")
def api_bypass_403_cmd(
    ctx: typer.Context,
    target_url: str = typer.Argument(..., help="Target API endpoint returning 401/403."),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method (GET, POST, etc.)."),
    header: list[str] = typer.Option(
        [], "--header", "-H", help="Base header in 'Key: Value' format (can repeat)."
    ),
) -> None:
    """Generate 401/403 access control bypass mutations (headers, paths, verbs) via nomore403."""
    state = _state(ctx)
    base_headers: dict[str, str] = {}
    for h in header:
        if ":" in h:
            k, v = h.split(":", 1)
            base_headers[k.strip()] = v.strip()

    args: dict[str, Any] = {
        "target_url": target_url,
        "http_method": method,
        "base_headers": base_headers if base_headers else None,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "api"), "api_bypass_403_test", args, profile="api")
    )
    _emit(state, payload, title="API 401/403 Bypass Mutation Vectors")


@api_app.command("proxy-rotate")
def api_proxy_rotate_cmd(
    ctx: typer.Context,
    target_url: str = typer.Argument(
        ..., help="Target API host or base URL to proxy egress towards."
    ),
    region: list[str] = typer.Option(
        [], "--region", "-r", help="Cloud regions to distribute egress across (can repeat)."
    ),
    provider: str = typer.Option(
        "aws_api_gateway", "--provider", "-p", help="Cloud proxy provider."
    ),
    max_retries: int = typer.Option(5, "--retries", help="Max retries on rate limits."),
) -> None:
    """Create a multi-region rotating cloud gateway proxy session to bypass rate limits (429)."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_url": target_url,
        "regions": region if region else None,
        "provider": provider,
        "max_retries": max_retries,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "api"), "api_rotating_proxy_session", args, profile="api")
    )
    _emit(state, payload, title="Cloud Rotating Proxy Session")


@unpack_app.command("detect")
def unpack_detect_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    job_id: str | None = typer.Option(None, "--job", "-j", help="Optional analysis job ID."),
    include_apkid: bool = typer.Option(False, "--apkid", help="Run APKiD external engine."),
) -> None:
    """Detect packers, protectors, obfuscators, and anti-analysis mechanisms."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id, "include_apkid": include_apkid}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if job_id:
        args["job_id"] = job_id
    payload = asyncio.run(_invoke(_runtime(state), "packer_detect", args))
    _emit(state, payload, title="Packer Detection")


@unpack_app.command("extract")
def unpack_extract_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Optional destination directory."
    ),
) -> None:
    """Statically carve and extract embedded DEX and payload containers."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if output:
        args["output_dir"] = output
    payload = asyncio.run(_invoke(_runtime(state), "unpack_extract", args))
    _emit(state, payload, title="Payload Extraction")


@unpack_app.command("verify")
def unpack_verify_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    file_path: str = typer.Argument(..., help="Path to dumped DEX file."),
    reanalyze: bool = typer.Option(
        True, "--reanalyze/--no-reanalyze", help="Ingest into project catalog for re-analysis."
    ),
) -> None:
    """Verify structural integrity, checksums, and completeness of dumped DEX."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "unpack_verify",
            {"project_id": project_id, "file_path": file_path, "reanalyze": reanalyze},
        )
    )
    _emit(state, payload, title="Dump Completeness Verification")


@unpack_app.command("deobfuscate")
def unpack_deobfuscate_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    target: str = typer.Argument(..., help="Target class or component name."),
    strategy: str = typer.Option(
        "simplify",
        "--strategy",
        "-s",
        help="simplify, reflection_resolve, string_decrypt, dead_code_prune.",
    ),
    source: str | None = typer.Option(None, "--source", help="Optional source code or Smali text."),
) -> None:
    """Apply Dalvik deobfuscation transformations with strict provenance tracking."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "deobfuscate",
            {
                "project_id": project_id,
                "target": target,
                "strategy": strategy,
                "source_text": source,
            },
        )
    )
    _emit(state, payload, title="Deobfuscation Result")


@unpack_app.command("retrace")
def unpack_retrace_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    mapping_file: str = typer.Argument(..., help="Path to ProGuard/R8 mapping.txt file."),
    stack_trace: str | None = typer.Option(
        None, "--stacktrace", "-t", help="Optional obfuscated crash log or stack trace."
    ),
) -> None:
    """Parse ProGuard/R8 mapping files and translate symbols or stack traces."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "retrace",
            {
                "project_id": project_id,
                "mapping_file": mapping_file,
                "stack_trace": stack_trace,
            },
        )
    )
    _emit(state, payload, title="Retrace Translation")


# --- Diff Commands ---


@diff_app.command("compare")
def diff_compare_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    base_artifact_id: str = typer.Argument(..., help="Baseline artifact ID."),
    target_artifact_id: str = typer.Argument(..., help="Comparison target artifact ID."),
    categories: list[str] | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter categories (manifest, code, resource, native, api, ui).",
    ),
) -> None:
    """Compare two artifacts and produce a semantic diff report."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "base_artifact_id": base_artifact_id,
        "target_artifact_id": target_artifact_id,
    }
    if categories:
        args["categories"] = categories
    payload = asyncio.run(_invoke(_runtime(state), "artifact_compare", args))
    _emit(state, payload, title="Artifact Diff")


@diff_app.command("list")
def diff_list_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    diff_id: str = typer.Argument(..., help="Diff comparison ID."),
    category: str | None = typer.Option(None, "--category", "-c", help="Filter category."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List paginated changes from a diff comparison."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "diff_id": diff_id,
        "limit": limit,
        "offset": offset,
    }
    if category:
        args["category"] = category
    payload = asyncio.run(_invoke(_runtime(state), "diff_list_changes", args))
    _emit(state, payload, title="Diff Changes")


@diff_app.command("get")
def diff_get_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    diff_id: str = typer.Argument(..., help="Diff comparison ID."),
    change_id: str = typer.Argument(..., help="Change item ID."),
) -> None:
    """Inspect one specific change item in detail."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "diff_get",
            {"project_id": project_id, "diff_id": diff_id, "change_id": change_id},
        )
    )
    _emit(state, payload, title="Diff Change Detail")


@diff_app.command("export")
def diff_export_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    diff_id: str = typer.Argument(..., help="Diff comparison ID."),
    format: str = typer.Option("json", "--format", "-f", help="json, markdown, or unified."),
) -> None:
    """Export diff comparison as JSON, Markdown, or unified diff."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "diff_export",
            {"project_id": project_id, "diff_id": diff_id, "format": format},
        )
    )
    _emit(state, payload, title="Diff Export")


# --- Security Commands ---


@security_app.command("scan")
def security_scan_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    categories: list[str] | None = typer.Option(None, "--category", "-c", help="MASVS categories."),
) -> None:
    """Run static MASVS/MASTG security checks."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if categories:
        args["categories"] = categories
    payload = asyncio.run(_invoke(_runtime(state), "security_scan_static", args))
    _emit(state, payload, title="Static Security Scan")


@security_app.command("findings")
def security_findings_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    severity: str | None = typer.Option(
        None, "--severity", "-s", help="info, low, medium, high, critical."
    ),
    masvs: str | None = typer.Option(None, "--masvs", "-m", help="MASVS category filter."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
) -> None:
    """List normalized security findings."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id, "limit": limit, "offset": offset}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if severity:
        args["severity"] = severity
    if masvs:
        args["masvs_category"] = masvs
    payload = asyncio.run(_invoke(_runtime(state), "security_get_findings", args))
    _emit(state, payload, title="Security Findings")


@security_app.command("secrets")
def security_secrets_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Locate embedded credentials, API keys, and tokens with redaction."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "security_find_secret_locations", args))
    _emit(state, payload, title="Secret Locations")


@security_app.command("privacy")
def security_privacy_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    pii_type: str | None = typer.Option(None, "--type", "-t", help="location, contacts, etc."),
) -> None:
    """Detect sensitive PII source-to-sink transmission flows."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if pii_type:
        args["pii_type"] = pii_type
    payload = asyncio.run(_invoke(_runtime(state), "privacy_data_flows", args))
    _emit(state, payload, title="Privacy Data Flows")


@security_app.command("sdks")
def security_sdks_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    category: str | None = typer.Option(None, "--category", "-c", help="Optional category."),
) -> None:
    """Inventory third-party SDKs and tracking libraries."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if category:
        args["category"] = category
    payload = asyncio.run(_invoke(_runtime(state), "sdk_inventory", args))
    _emit(state, payload, title="SDK Inventory")


@security_app.command("sbom")
def security_sbom_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    format: str = typer.Option("cyclonedx", "--format", "-f", help="cyclonedx or spdx."),
) -> None:
    """Generate CycloneDX 1.5 or SPDX 2.3 Software Bill of Materials."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id, "format": format}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sbom_generate", args))
    _emit(state, payload, title="Software Bill of Materials")


@security_app.command("vulns")
def security_vulns_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    min_severity: str = typer.Option(
        "low", "--min-severity", "-s", help="Minimum severity threshold."
    ),
) -> None:
    """Correlate software components with known CVE/OSV advisories."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id, "min_severity": min_severity}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "vulnerability_scan", args))
    _emit(state, payload, title="Vulnerability Scan")


@security_app.command("yara")
def security_yara_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    rules: str | None = typer.Option(
        None, "--rules", "-r", help="Optional path to custom rules file."
    ),
) -> None:
    """Scan container with YARA rules."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if rules:
        args["rules_path"] = rules
    payload = asyncio.run(_invoke(_runtime(state), "yara_scan", args))
    _emit(state, payload, title="YARA Scan")


@security_app.command("capa")
def security_capa_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    rules: str | None = typer.Option(None, "--rules", "-r", help="Optional path to custom rules."),
) -> None:
    """Detect offensive capabilities with capa."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    if rules:
        args["rules_path"] = rules
    payload = asyncio.run(_invoke(_runtime(state), "capa_scan", args))
    _emit(state, payload, title="Capa Capabilities")


@security_app.command("quark")
def security_quark_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Calculate behavioral threat score using Quark rules."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "quark_score", args))
    _emit(state, payload, title="Quark Behavioral Score")


@security_app.command("ioc")
def security_ioc_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    export: str | None = typer.Option(
        None, "--export", "-e", help="Export format: json, csv, stix."
    ),
) -> None:
    """Extract and optionally export Indicators of Compromise."""
    state = _state(ctx)
    if export:
        args: dict[str, Any] = {"project_id": project_id, "format": export}
        if artifact_id:
            args["artifact_id"] = artifact_id
        payload = asyncio.run(_invoke(_runtime(state), "ioc_export", args))
        _emit(state, payload, title="IOC Export")
    else:
        args = {"project_id": project_id}
        if artifact_id:
            args["artifact_id"] = artifact_id
        payload = asyncio.run(_invoke(_runtime(state), "ioc_extract", args))
        _emit(state, payload, title="Extracted IOCs")


@security_app.command("enrich")
def security_enrich_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
    provider: str = typer.Option("internal", "--provider", "-p", help="Threat intel provider."),
    consent: bool = typer.Option(
        False, "--consent", help="Grant explicit consent for remote query."
    ),
) -> None:
    """Query external threat intelligence (consent-gated)."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "provider": provider,
        "user_consent": consent,
    }
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sample_enrich", args))
    _emit(state, payload, title="Threat Intel Enrichment")


@security_app.command("play-protect")
def security_play_protect_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Pre-flight audit against Google Play Protect and store policies."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_play_protect_audit", args))
    _emit(state, payload, title="Play Protect Pre-Flight Audit")


@security_app.command("dcl")
def security_dcl_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Scan for unverified Dynamic Code Loading (DCL) routines."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_dcl_detect", args))
    _emit(state, payload, title="Dynamic Code Loading Detection")


@security_app.command("mobsf")
def security_mobsf_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Evaluate MobSF static security rule catalog against manifest and code."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_mobsf_rule_scan", args))
    _emit(state, payload, title="MobSF Static Rule Scan")


@security_app.command("cvss")
def security_cvss_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Generate CVSS v3.1 risk scorecard and category breakdown."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_cvss_scorecard_generate", args))
    _emit(state, payload, title="CVSS v3.1 Risk Scorecard")


@security_app.command("sarif")
def security_sarif_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Export security findings in OASIS SARIF v2.1.0 format."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_sarif_export", args))
    _emit(state, payload, title="OASIS SARIF 2.1 Export")


@security_app.command("stride")
def security_stride_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Model vulnerabilities under STRIDE mapped to MITRE ATT&CK for Mobile."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_stride_model", args))
    _emit(state, payload, title="Mobile STRIDE Threat Model")


@security_app.command("poc")
def security_poc_cmd(
    ctx: typer.Context,
    finding_id: str = typer.Argument(..., help="Finding ID."),
    title: str = typer.Option("Vulnerability Finding", "--title", "-t", help="Finding title."),
    package: str = typer.Option("com.example.app", "--package", "-p", help="Target package."),
    component: str | None = typer.Option(None, "--component", "-c", help="Component name."),
    param: str | None = typer.Option(None, "--param", help="Parameter name."),
) -> None:
    """Generate reproducible, non-destructive Proof-of-Concept exploit commands."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "finding_id": finding_id,
        "title": title,
        "target_package": package,
    }
    if component:
        args["component"] = component
    if param:
        args["parameter"] = param
    payload = asyncio.run(_invoke(_runtime(state), "sec_poc_generate", args))
    _emit(state, payload, title="Executable PoC Generator")


@security_app.command("intent-redirection")
def security_intent_redirection_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Scan for untrusted Intent Redirection vulnerabilities."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_intent_redirection_scan", args))
    _emit(state, payload, title="Intent Redirection Taint Scan")


@security_app.command("pending-intent")
def security_pending_intent_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Scan for implicit mutable PendingIntent vulnerabilities."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_pending_intent_audit", args))
    _emit(state, payload, title="PendingIntent Mutability Audit")


@security_app.command("aidl-auth")
def security_aidl_auth_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Optional artifact ID."),
) -> None:
    """Audit Bound Services and AIDL stubs for caller authentication flaws."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_aidl_auth_audit", args))
    _emit(state, payload, title="AIDL & Bound Service Caller Verification")


@security_app.command("poc-validate")
def security_poc_validate_cmd(
    ctx: typer.Context,
    target_package: str = typer.Argument(..., help="Target application package."),
    vuln_type: str = typer.Option("intent_redirection", "--type", "-t", help="Vulnerability type."),
    component: str | None = typer.Option(None, "--component", "-c", help="Target component."),
    intent_action: str | None = typer.Option(None, "--action", "-a", help="Intent action."),
    intent_data: str | None = typer.Option(None, "--data", "-d", help="Intent URI data."),
) -> None:
    """Validate an exploit Proof-of-Concept for safety, syntax, and real exploitability."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_package": target_package,
        "vuln_type": vuln_type,
    }
    if component:
        args["target_component"] = component
    if intent_action:
        args["intent_action"] = intent_action
    if intent_data:
        args["intent_data"] = intent_data
    payload = asyncio.run(_invoke(_runtime(state), "sec_poc_validate", args))
    _emit(state, payload, title="Exploit PoC Validation")


@security_app.command("masvs-audit")
def security_masvs_audit_cmd(
    ctx: typer.Context,
    debuggable: bool = typer.Option(False, "--debuggable", help="Flag if debuggable is enabled."),
    cleartext: bool = typer.Option(False, "--cleartext", help="Flag if cleartext is allowed."),
    minified: bool = typer.Option(True, "--minified/--no-minified", help="Obfuscation status."),
) -> None:
    """Audit application security posture against the 7 OWASP MASVS v2.0 domains."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "is_debuggable": debuggable,
        "uses_cleartext": cleartext,
        "is_minified": minified,
    }
    payload = asyncio.run(_invoke(_runtime(state), "sec_masvs_audit", args))
    _emit(state, payload, title="OWASP MASVS v2.0 Compliance Audit")


@security_app.command("copilot-suggest")
def security_copilot_suggest_cmd(
    ctx: typer.Context,
    goal: str = typer.Argument(..., help="Analyst query or reversing goal."),
    framework: list[str] = typer.Option([], "--framework", "-f", help="Detected frameworks."),
) -> None:
    """Recommend next reversing tools, parameters, and Frida snippets for an analyst query."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "user_goal": goal,
        "detected_frameworks": framework,
    }
    payload = asyncio.run(_invoke(_runtime(state), "copilot_suggest_next", args))
    _emit(state, payload, title="Reversing Copilot Recommendations")


@security_app.command("bugbounty-report")
def security_bugbounty_report_cmd(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Vulnerability finding title."),
    vuln_type: str = typer.Option("IDOR", "--type", "-t", help="Vulnerability type."),
    severity: str = typer.Option("High", "--severity", "-s", help="Severity level."),
    target: str = typer.Option("com.example.app", "--target", help="Target component or app."),
    description: str = typer.Option(
        "Vulnerability found during analysis", "--desc", "-d", help="Finding description."
    ),
    steps: list[str] = typer.Option(["Open app", "Trigger payload"], "--step", help="Steps."),
    impact: str = typer.Option("Unauthorized data disclosure", "--impact", help="Impact."),
    platform: str = typer.Option("HackerOne", "--platform", "-p", help="Target platform."),
) -> None:
    """Format security finding into a submission-ready Bug Bounty report."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "title": title,
        "vulnerability_type": vuln_type,
        "severity": severity,
        "target": target,
        "description": description,
        "steps_to_reproduce": steps,
        "impact": impact,
        "platform": platform,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "sec_bugbounty_report_format", args, profile="admin")
    )
    _emit(state, payload, title="Bug Bounty Submission Report")


@security_app.command("email-intel")
def security_email_intel_cmd(
    ctx: typer.Context,
    emails: list[str] = typer.Argument(..., help="Target email addresses to analyze."),
) -> None:
    """Check developer emails across developer platforms (GitHub, AWS, Google, Docker)."""
    state = _state(ctx)
    args: dict[str, Any] = {"emails": emails}
    payload = asyncio.run(_invoke(_runtime(state), "sec_leaked_email_intel", args))
    _emit(state, payload, title="Developer Email OSINT Footprint")


@security_app.command("apkleaks-scan")
def security_apkleaks_scan_cmd(
    ctx: typer.Context,
    apk_path: str | None = typer.Option(None, "--apk", "-a", help="Path to target APK file."),
    min_entropy: float = typer.Option(
        2.5, "--entropy", "-e", help="Minimum Shannon entropy threshold."
    ),
) -> None:
    """Mine Dalvik bytecode and assets for cloud credentials and API tokens."""
    state = _state(ctx)
    args: dict[str, Any] = {"min_entropy": min_entropy}
    if apk_path:
        args["apk_path"] = apk_path
    payload = asyncio.run(_invoke(_runtime(state), "sec_apkleaks_secret_scan", args))
    _emit(state, payload, title="APKLeaks Cloud Credential Harvest")


@security_app.command("taint-trace")
def security_taint_trace_cmd(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project", "-p", help="Target project ID."),
    artifact_id: str | None = typer.Option(None, "--artifact", "-a", help="Target artifact ID."),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Strict GDPR enforcement."),
) -> None:
    """Trace sensitive Android privacy APIs to network and logging transmission sinks."""
    state = _state(ctx)
    args: dict[str, Any] = {"enforce_strict_gdpr": strict}
    if project_id:
        args["project_id"] = project_id
    if artifact_id:
        args["artifact_id"] = artifact_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_sensitive_api_taint_trace", args))
    _emit(state, payload, title="Sensitive API Call-Graph & Privacy Taint Trace")


@security_app.command("mastg-run")
def security_mastg_run_cmd(
    ctx: typer.Context,
    package: str = typer.Option(
        "com.target.application", "--package", "-p", help="Target package."
    ),
    test_id: list[str] | None = typer.Option(
        None, "--test", "-t", help="Specific MASTG test ID(s)."
    ),
) -> None:
    """Execute formal OWASP MASTG verification test procedures against MASVS controls."""
    state = _state(ctx)
    args: dict[str, Any] = {"target_package": package}
    if test_id:
        args["test_ids"] = test_id
    payload = asyncio.run(_invoke(_runtime(state), "sec_mastg_procedure_run", args))
    _emit(state, payload, title="OWASP MASTG Verification Scorecard")


@security_app.command("arch-diagram")
def security_arch_diagram_cmd(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project", "-p", help="Target project ID."),
    apk_path: str | None = typer.Option(None, "--apk", "-a", help="Path to APK file."),
    title: str = typer.Option(
        "APK Architecture & Data-Flow Taint Graph", "--title", "-t", help="Diagram title."
    ),
    theme: str = typer.Option("dark", "--theme", help="Diagram visual theme (dark, light)."),
    output: str | None = typer.Option(None, "--output", "-o", help="Output path for HTML diagram."),
    no_taint: bool = typer.Option(False, "--no-taint", help="Exclude taint flow paths."),
) -> None:
    """Render interactive architecture diagram with real-time node search & taint tracing."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "title": title,
        "theme": theme,
        "include_taint_flows": not no_taint,
    }
    if project_id:
        args["project_id"] = project_id
    if apk_path:
        args["apk_path"] = apk_path
    if output:
        args["output_path"] = output
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "sec_arch_diagram_render", args, profile="admin")
    )
    _emit(state, payload, title="Interactive Architecture & Taint Flow Diagram")


@security_app.command("code-review")
def security_code_review_cmd(
    ctx: typer.Context,
    source_dir: str | None = typer.Option(
        None, "--dir", "-d", help="Directory with decompiled sources."
    ),
    ruleset: str = typer.Option(
        "all", "--ruleset", "-r", help="Rule category (all, crypto, sqli)."
    ),
    severity: str = typer.Option("low", "--severity", "-s", help="Minimum severity threshold."),
    max_findings: int = typer.Option(50, "--max", "-m", help="Max findings to report."),
) -> None:
    """Audit decompiled Java/Kotlin sources with hybrid AST and semantic security checks."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "ruleset": ruleset,
        "severity_threshold": severity,
        "max_findings": max_findings,
    }
    if source_dir:
        args["source_dir"] = source_dir
    payload = asyncio.run(_invoke(_runtime(state), "sec_source_code_review", args))
    _emit(state, payload, title="Decompiled Source Code Security Review")


@security_app.command("rasp-scan")
def security_rasp_scan_cmd(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="Path to APK file or decompiled source directory."),
    deep_native: bool = typer.Option(
        True, "--native/--no-native", help="Scan native ELF binaries."
    ),
    frameworks: str | None = typer.Option(
        None,
        "--frameworks",
        "-f",
        help="Comma-separated frameworks filter (freerasp,promon,dexguard).",
    ),
) -> None:
    """Scan Smali and native libraries for RASP, root detection, and anti-hooking checks."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "target_path": target,
        "deep_native_scan": deep_native,
    }
    if frameworks:
        args["frameworks"] = [f.strip() for f in frameworks.split(",") if f.strip()]
    payload = asyncio.run(_invoke(_runtime(state), "sec_rasp_signature_scan", args))
    _emit(state, payload, title="RASP & Tamper Detection Signature Scanner")


# --- On-Device AI Commands ---


@ai_app.command("inspect-model")
def ai_inspect_model_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    model_name: str | None = typer.Option(None, "--model", "-m", help="Model file name."),
) -> None:
    """Inspect on-device ML models (TFLite, LiteRT, ONNX) for operators and risks."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if model_name:
        args["model_name"] = model_name
    payload = asyncio.run(_invoke(_runtime(state), "ai_model_inspect", args))
    _emit(state, payload, title="On-Device AI Model Inspection")


@ai_app.command("extract-prompts")
def ai_extract_prompts_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    corpus: str | None = typer.Option(None, "--corpus", "-c", help="Text corpus to scan."),
) -> None:
    """Extract embedded LLM system prompts and RAG vector store configurations."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if corpus:
        args["corpus_text"] = corpus
    payload = asyncio.run(_invoke(_runtime(state), "ai_prompt_extract", args))
    _emit(state, payload, title="AI Prompt & Instruction Extraction")


@ai_app.command("appfunctions")
def ai_appfunctions_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    metadata_xml: str | None = typer.Option(None, "--xml", "-x", help="AppFunction metadata XML."),
) -> None:
    """Discover Android 16 AppFunction declarations exposed to AI agents."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if metadata_xml:
        args["metadata_xml"] = metadata_xml
    payload = asyncio.run(_invoke(_runtime(state), "ai_appfunction_discover", args))
    _emit(state, payload, title="Android 16 AppFunctions Discovery")


# --- Test Commands ---


@test_app.command("generate")
def test_generate_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Target artifact ID."),
    test_type: str = typer.Option("api", "--type", "-t", help="Test type: api, ui, integration."),
    framework: str = typer.Option(
        "pytest", "--framework", "-f", help="Framework: pytest, appium, espresso, playwright."
    ),
) -> None:
    """Generate automated test suites from analysis evidence."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "artifact_id": artifact_id,
        "test_type": test_type,
        "framework": framework,
    }
    payload = asyncio.run(_invoke(_runtime(state), "test_generate", args))
    _emit(state, payload, title="Test Suite Generation")


@test_app.command("run")
def test_run_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    test_id: str = typer.Argument(..., help="Generated test ID."),
    target_url: str | None = typer.Option(
        None, "--target-url", "-u", help="Optional target base URL."
    ),
    device_id: str | None = typer.Option(
        None, "--device-id", "-d", help="Optional target leased device ID."
    ),
) -> None:
    """Execute generated test suite against authorized environment."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "test_id": test_id,
    }
    if target_url:
        args["target_url"] = target_url
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(_invoke(_runtime(state), "test_run", args))
    _emit(state, payload, title="Test Suite Execution")


# --- Controlled Rebuild Commands ---


@rebuild_app.command("patch")
def rebuild_patch_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Target base artifact ID."),
    operation: str = typer.Option(
        ...,
        "--operation",
        "-o",
        help=(
            "Patch operation: network_security_bypass, set_debuggable, set_allow_backup,"
            " inject_frida_gadget, custom_smali."
        ),
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Simulate changes without producing new APK."
    ),
) -> None:
    """Plan and apply controlled modifications to APK container."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "artifact_id": artifact_id,
        "operation": operation,
        "dry_run": dry_run,
    }
    payload = asyncio.run(_invoke(_runtime(state), "apk_patch", args))
    _emit(state, payload, title="APK Container Patch")


@rebuild_app.command("sign")
def rebuild_sign_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Target artifact ID to sign."),
) -> None:
    """Sign an APK container with test or project credentials."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "artifact_id": artifact_id,
    }
    payload = asyncio.run(_invoke(_runtime(state), "apk_sign", args))
    _emit(state, payload, title="APK Container Sign")


@rebuild_app.command("install")
def rebuild_install_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    device_id: str = typer.Argument(..., help="Leased target device ID."),
    artifact_id: str = typer.Argument(..., help="Artifact ID to install."),
) -> None:
    """Install an APK onto a leased Android device."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "device_id": device_id,
        "artifact_id": artifact_id,
    }
    payload = asyncio.run(_invoke(_runtime(state), "device_install", args))
    _emit(state, payload, title="Device APK Install")


@rebuild_app.command("verify")
def rebuild_verify_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    base_artifact_id: str = typer.Argument(..., help="Original baseline artifact ID."),
    patched_artifact_id: str = typer.Argument(..., help="Patched comparison artifact ID."),
) -> None:
    """Compare behavioral divergence between baseline and patched artifacts."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "base_artifact_id": base_artifact_id,
        "patched_artifact_id": patched_artifact_id,
    }
    payload = asyncio.run(_invoke(_runtime(state), "verify_behavior", args))
    _emit(state, payload, title="Behavioral Verification")


@rebuild_app.command("align-16kb")
def rebuild_align_16kb_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
    artifact_id: str = typer.Argument(..., help="Target artifact ID."),
    patch: bool = typer.Option(False, "--patch", help="Auto-patch non-compliant ELF headers."),
) -> None:
    """Audit and patch native shared libraries for Android 15 16KB alignment."""
    state = _state(ctx)
    args = {"project_id": project_id, "artifact_id": artifact_id, "patch": patch}
    payload = asyncio.run(_invoke(_runtime(state), "rebuild_elf_align_16kb", args))
    _emit(state, payload, title="Android 15 16KB ELF Alignment")


@rebuild_app.command("agents-spec")
def rebuild_agents_spec_cmd(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project", "-p", help="Target project ID."),
    app_name: str = typer.Option(
        "ModernizedApp", "--app-name", "-n", help="App name for guidelines."
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output path for AGENTS.md."),
) -> None:
    """Generate standardized repository-level AGENTS.md contract for rebuilt projects."""
    state = _state(ctx)
    args: dict[str, Any] = {"app_name": app_name}
    if project_id:
        args["project_id"] = project_id
    if output:
        args["output_path"] = output
    payload = asyncio.run(_invoke(_runtime(state), "rebuild_agents_spec_generate", args))
    _emit(state, payload, title="AGENTS.md Architecture Contract")


# --- Admin Commands ---


@admin_app.command("verify")
def admin_verify_cmd(
    ctx: typer.Context,
    engine_id: str | None = typer.Option(
        None, "--engine", "-e", help="Optional engine ID to verify."
    ),
) -> None:
    """Verify engine pack manifest, integration mode, and binary hash integrity."""
    state = _state(ctx)
    args: dict[str, Any] = {}
    if engine_id:
        args["engine_id"] = engine_id
    payload = asyncio.run(_invoke(_runtime(state, "admin"), "admin_engine_verify", args))
    _emit(state, payload, title="Engine Pack Verification")


@admin_app.command("audit")
def admin_audit_cmd(
    ctx: typer.Context,
    tool: str | None = typer.Option(None, "--tool", "-t", help="Filter by tool name."),
    outcome: str | None = typer.Option(
        None, "--outcome", "-o", help="Filter by outcome (success, error)."
    ),
    error_code: str | None = typer.Option(None, "--error-code", help="Filter by error code."),
    project_id: str | None = typer.Option(None, "--project", "-p", help="Filter by project ID."),
    request_id: str | None = typer.Option(None, "--request", "-r", help="Filter by request ID."),
    limit: int = typer.Option(50, "--limit", "-l", help="Max audit entries to return."),
    offset: int = typer.Option(0, "--offset", help="Pagination offset."),
) -> None:
    """Query append-only audit trail logs with filtering and pagination."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }
    if tool:
        args["tool"] = tool
    if outcome:
        args["outcome"] = outcome
    if error_code:
        args["error_code"] = error_code
    if project_id:
        args["project_id"] = project_id
    if request_id:
        args["request_id"] = request_id
    payload = asyncio.run(_invoke(_runtime(state, "admin"), "admin_audit_query", args))
    _emit(state, payload, title="Audit Trail Events")


@admin_app.command("engines")
def admin_engines_cmd(ctx: typer.Context) -> None:
    """List catalogued reverse engineering engines and availability."""
    state = _state(ctx)
    payload = asyncio.run(_invoke(_runtime(state, "admin"), "admin_engine_list", {}))
    _emit(state, payload, title="Engine Catalogue")


@admin_app.command("licenses")
def admin_licenses_cmd(ctx: typer.Context) -> None:
    """Inventory of engines grouped by license and distribution class."""
    state = _state(ctx)
    payload = asyncio.run(_invoke(_runtime(state, "admin"), "admin_license_report", {}))
    _emit(state, payload, title="License Report")


@admin_app.command("coverage")
def admin_coverage_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Target project ID."),
) -> None:
    """Compute reverse engineering and reconstruction coverage metrics."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "admin"),
            "agent_coverage_get",
            {"project_id": project_id},
        )
    )
    _emit(state, payload, title="Agent Analysis Coverage")


@admin_app.command("audit-verify")
def admin_audit_verify_cmd(ctx: typer.Context) -> None:
    """Cryptographically verify the tamper-evident hash chain of the audit trail."""
    state = _state(ctx)
    payload = asyncio.run(_invoke(_runtime(state, "admin"), "admin_audit_verify", {}))
    _emit(state, payload, title="Audit Trail Integrity Verification")


@admin_app.command("sbom")
def admin_sbom_cmd(
    ctx: typer.Context,
    format: str = typer.Option(
        "cyclonedx", "--format", "-f", help="SBOM format: 'cyclonedx' or 'spdx'."
    ),
) -> None:
    """Generate standardized CycloneDX or SPDX Software Bill of Materials."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "admin_sbom_generate", {"format": format})
    )
    _emit(state, payload, title=f"Software Bill of Materials ({format.upper()})")


@admin_app.command("backup")
def admin_backup_cmd(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Project ID to back up."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Optional output tar.gz path."),
) -> None:
    """Create a compressed .tar.gz backup bundle of a project."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "admin"),
            "admin_backup_create",
            {"project_id": project_id, "output_path": str(output) if output else None},
        )
    )
    _emit(state, payload, title="Project Backup Created")


@admin_app.command("restore")
def admin_restore_cmd(
    ctx: typer.Context,
    bundle_path: Path = typer.Argument(..., help="Path to .raa.bundle.tar.gz file."),
    name: str | None = typer.Option(None, "--name", "-n", help="Optional new project name."),
) -> None:
    """Restore an enterprise project from a backup bundle."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "admin"),
            "admin_backup_restore",
            {"bundle_path": str(bundle_path), "new_name": name},
        )
    )
    _emit(state, payload, title="Project Restored from Backup")


@admin_app.command("retention")
def admin_retention_cmd(
    ctx: typer.Context,
    days: int = typer.Option(30, "--days", "-d", help="Retention threshold in days."),
) -> None:
    """Enforce data retention policy by pruning expired backups and temporary caches."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "admin_retention_purge", {"retention_days": days})
    )
    _emit(state, payload, title="Retention Policy Enforced")


@admin_app.command("metrics")
def admin_metrics_cmd(ctx: typer.Context) -> None:
    """Display system observability metrics, database storage, and runtime telemetry."""
    state = _state(ctx)
    payload = asyncio.run(_invoke(_runtime(state, "admin"), "admin_system_metrics", {}))
    _emit(state, payload, title="System Observability Metrics")


@admin_app.command("signature-verify")
def admin_signature_verify_cmd(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Content or file name."),
    content_type: str = typer.Option("skill", "--type", "-t", help="Type: skill, recipe, file."),
    signature: str | None = typer.Option(None, "--sig", "-s", help="Digital signature hex digest."),
    file_path: Path | None = typer.Option(None, "--file", "-f", help="Optional file path on disk."),
) -> None:
    """Verify digital signature and cryptographic authenticity of skills, recipes, or files."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state, "admin"),
            "admin_signature_verify",
            {
                "name": name,
                "content_type": content_type,
                "signature": signature,
                "file_path": str(file_path) if file_path else None,
            },
        )
    )
    _emit(state, payload, title="Signature Verification Result")


@admin_app.command("ztna-config")
def admin_ztna_config_cmd(
    ctx: typer.Context,
    name: str = typer.Option("raa-mcp-gateway", "--name", "-n", help="Gateway name."),
    port: int = typer.Option(8443, "--port", "-p", help="Gateway listen port."),
    client: list[str] = typer.Option(
        ["cursor", "claude-code"], "--client", "-c", help="Allowed clients."
    ),
    token: str | None = typer.Option(None, "--token", "-t", help="Fixed bearer token."),
) -> None:
    """Generate Zero-Trust MCP Gateway configuration and agent client templates."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "server_name": name,
        "listen_port": port,
        "allowed_clients": client,
        "enable_mtls": True,
    }
    if token:
        args["auth_token"] = token
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "admin_ztna_tunnel_config", args, profile="admin")
    )
    _emit(state, payload, title="Zero-Trust Remote MCP Gateway Configuration")


# --- Platform Universal Expansion Commands ---


@platform_app.command("ios-inspect")
def platform_ios_inspect_cmd(
    ctx: typer.Context,
    ipa_path: str = typer.Argument(..., help="Path to Apple iOS .ipa file."),
    entitlements: bool = typer.Option(
        True, "--entitlements/--no-entitlements", help="Extract mobileprovision entitlements."
    ),
) -> None:
    """Inspect Apple iOS .ipa container, Info.plist permissions, and Mach-O headers."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "ipa_path": ipa_path,
        "extract_entitlements": entitlements,
    }
    payload = asyncio.run(_invoke(_runtime(state), "ios_ipa_inspect", args))
    _emit(state, payload, title="Apple iOS IPA Application Inspection")


@platform_app.command("macho-disassemble")
def platform_macho_disassemble_cmd(
    ctx: typer.Context,
    binary_path: str = typer.Argument(..., help="Path to Mach-O binary executable."),
    deep_symbols: bool = typer.Option(
        True, "--symbols/--no-symbols", help="Scan for Swift and Objective-C symbols."
    ),
) -> None:
    """Disassemble Apple 64-bit Mach-O binary, FairPlay cryptid, and dynamic libraries."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "binary_path": binary_path,
        "deep_symbols": deep_symbols,
    }
    payload = asyncio.run(_invoke(_runtime(state), "ios_macho_disassemble", args))
    _emit(state, payload, title="Apple Mach-O 64-Bit Binary Disassembler")


@platform_app.command("harmony-inspect")
def platform_harmony_inspect_cmd(
    ctx: typer.Context,
    hap_path: str = typer.Argument(..., help="Path to Huawei HarmonyOS .hap package."),
) -> None:
    """Inspect Huawei HarmonyOS / OpenHarmony .hap package, manifests, and abilities."""
    state = _state(ctx)
    args: dict[str, Any] = {"hap_path": hap_path}
    payload = asyncio.run(_invoke(_runtime(state), "harmony_hap_inspect", args))
    _emit(state, payload, title="Huawei HarmonyOS HAP Package Inspection")


@platform_app.command("harmony-disassemble")
def platform_harmony_disassemble_cmd(
    ctx: typer.Context,
    abc_path: str = typer.Argument(..., help="Path to ArkTS classes.abc bytecode file."),
) -> None:
    """Disassemble Huawei ArkTS classes.abc bytecode into ArkUI decorators and components."""
    state = _state(ctx)
    args: dict[str, Any] = {"abc_path": abc_path}
    payload = asyncio.run(_invoke(_runtime(state), "harmony_abc_disassemble", args))
    _emit(state, payload, title="Huawei ArkTS Bytecode Disassembler")


@platform_app.command("proot")
def platform_proot_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "status", "--action", "-a", help="Action: status, init, exec, install_pkg, purge."
    ),
    command: str | None = typer.Option(None, "--cmd", "-c", help="Command to run in PRoot."),
    distro: str = typer.Option("debian", "--distro", "-d", help="Linux distro: debian, alpine."),
    workspace_dir: str = typer.Option(
        "/data/local/tmp/raa_proot", "--dir", help="On-device rootfs dir."
    ),
    device_id: str | None = typer.Option(None, "--device", help="Target ADB device ID."),
) -> None:
    """Manage on-device standalone Linux PRoot container without root or PC tethering."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action": action,
        "distro": distro,
        "workspace_dir": workspace_dir,
    }
    if command:
        args["command"] = command
    if device_id:
        args["device_id"] = device_id
    payload = asyncio.run(_invoke(_runtime(state), "termux_proot_workspace_manage", args))
    _emit(state, payload, title="On-Device Standalone PRoot Linux Container")


@platform_app.command("warp-session")
def platform_warp_session_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "record_block",
        "--action",
        "-a",
        help="Action: record_block, get_session, bookmark_block, export_runbook, clear.",
    ),
    session_id: str = typer.Option("default_session", "--session", "-s", help="Warp session ID."),
    command: str | None = typer.Option(None, "--cmd", "-c", help="Command executed."),
    output: str | None = typer.Option(None, "--output", "-o", help="Command output."),
    block_id: str | None = typer.Option(None, "--block", "-b", help="Block ID to bookmark."),
) -> None:
    """Manage interactive Warp-style terminal block sessions and export audit runbooks."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action": action,
        "session_id": session_id,
    }
    if command:
        args["command"] = command
    if output:
        args["output"] = output
    if block_id:
        args["block_id"] = block_id
    payload = asyncio.run(_invoke(_runtime(state), "warp_block_session_manage", args))
    _emit(state, payload, title="Interactive Warp Terminal Block Session")


@platform_app.command("cross-compare")
def platform_cross_compare_cmd(
    ctx: typer.Context,
    android: str | None = typer.Option(None, "--android", "-a", help="Path to Android APK."),
    ios: str | None = typer.Option(None, "--ios", "-i", help="Path to Apple iOS IPA."),
    harmony: str | None = typer.Option(None, "--harmony", "-h", help="Path to HarmonyOS HAP."),
) -> None:
    """Compare Android, iOS, and HarmonyOS apps side-by-side for permissions and parity."""
    state = _state(ctx)
    args: dict[str, Any] = {}
    if android:
        args["android_apk_path"] = android
    if ios:
        args["ios_ipa_path"] = ios
    if harmony:
        args["harmony_hap_path"] = harmony
    payload = asyncio.run(_invoke(_runtime(state), "platform_cross_target_compare", args))
    _emit(state, payload, title="Cross-Platform Android, iOS & HarmonyOS Target Compare")


# --- Phase 15: Swarm CLI Commands ---


@swarm_app.command("govern")
def swarm_govern_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    name: str = typer.Option("RAA Swarm", "--name", "-n", help="Swarm name."),
    lead_role: str = typer.Option(
        "swarm_director_agent", "--lead", "-l", help="Lead coordinator role ID."
    ),
) -> None:
    """Configure multi-agent swarm hierarchy and roles."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "swarm_name": name,
        "lead_role": lead_role,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "swarm_org_govern", args, profile="swarm")
    )
    _emit(state, payload, title="Swarm Governance Configuration")


@swarm_app.command("budget")
def swarm_budget_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    tokens: int = typer.Option(0, "--tokens", "-t", help="Tokens consumed."),
    cost: float = typer.Option(0.0, "--cost", "-c", help="Cost in USD."),
    subagent: str | None = typer.Option(None, "--subagent", "-s", help="Subagent name."),
    token_cap: int | None = typer.Option(None, "--token-cap", help="Set token ceiling."),
    cost_cap: float | None = typer.Option(None, "--cost-cap", help="Set cost ceiling in USD."),
) -> None:
    """Track token spend and enforce budget ceilings."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "project_id": project_id,
        "tokens": tokens,
        "cost_usd": cost,
    }
    if subagent:
        args["subagent_name"] = subagent
    if token_cap is not None:
        args["set_token_cap"] = token_cap
    if cost_cap is not None:
        args["set_cost_cap_usd"] = cost_cap
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "swarm_budget_meter", args, profile="swarm")
    )
    _emit(state, payload, title="Swarm Budget Metering")


@swarm_app.command("spawn-deerflow")
def swarm_spawn_deerflow_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    goal: str = typer.Option(..., "--goal", "-g", help="Mission goal for deep research."),
    agent_name: str = typer.Option("deerflow_researcher", "--agent", "-a", help="Agent name."),
    max_depth: int = typer.Option(3, "--depth", "-d", help="Max recursive exploration depth."),
) -> None:
    """Spawn a long-horizon Deer-Flow research subagent."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "mission_goal": goal,
        "agent_name": agent_name,
        "max_depth": max_depth,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "subagent_deerflow_spawn", args, profile="swarm")
    )
    _emit(state, payload, title="Deer-Flow Long-Horizon Subagent Spawn")


@swarm_app.command("sop")
def swarm_sop_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    sop_name: str = typer.Option("framework_audit", "--sop", "-s", help="SOP template name."),
    target: str = typer.Option(..., "--target", "-t", help="Target APK or package entity."),
) -> None:
    """Execute standardized multi-role reverse-engineering SOP."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "sop_name": sop_name,
        "target_entity": target,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "sop_pipeline_execute", args, profile="swarm")
    )
    _emit(state, payload, title="MetaGPT SOP Pipeline Execution")


@swarm_app.command("blackboard-post")
def swarm_blackboard_post_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    topic: str = typer.Option(..., "--topic", help="Topic channel (e.g. crypto, network)."),
    author: str = typer.Option(..., "--author", help="Author agent name."),
    hypothesis: str = typer.Option(..., "--hypothesis", help="Hypothesis or finding."),
    confidence: float = typer.Option(0.7, "--confidence", help="Confidence score 0.0-1.0."),
) -> None:
    """Post hypothesis or evidence to the shared swarm blackboard."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "topic": topic,
        "author": author,
        "hypothesis": hypothesis,
        "confidence": confidence,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "swarm_blackboard_post", args, profile="swarm")
    )
    _emit(state, payload, title="Swarm Blackboard Post")


@swarm_app.command("blackboard-read")
def swarm_blackboard_read_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    topic: str | None = typer.Option(None, "--topic", help="Optional topic filter."),
    author: str | None = typer.Option(None, "--author", help="Optional author filter."),
) -> None:
    """Read findings and hypotheses from the shared swarm blackboard."""
    state = _state(ctx)
    args: dict[str, Any] = {"project_id": project_id}
    if topic:
        args["topic"] = topic
    if author:
        args["author"] = author
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "swarm_blackboard_read", args, profile="swarm")
    )
    _emit(state, payload, title="Swarm Blackboard Entries")


@swarm_app.command("edict-gate")
def swarm_edict_gate_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    action: str = typer.Option(..., "--action", "-a", help="Action type proposed."),
    summary: str = typer.Option(..., "--summary", "-s", help="Drafted changes and justification."),
    risk: str = typer.Option(
        "medium", "--risk", "-r", help="Assessed risk: low, medium, high, critical."
    ),
    bypass: bool = typer.Option(False, "--bypass", help="Request bypass."),
) -> None:
    """Evaluate Tri-Chamber Edict review and veto gates."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "action_type": action,
        "draft_summary": summary,
        "risk_level": risk,
        "bypass_requested": bypass,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "swarm_edict_gate_evaluate", args, profile="swarm")
    )
    _emit(state, payload, title="Edict Tri-Chamber Governance Evaluation")


@swarm_app.command("loopx")
def swarm_loopx_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        ...,
        "--action",
        "-a",
        help="Action: create, status, enqueue_attention, step, checkpoint, list.",
    ),
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    goal_id: str | None = typer.Option(None, "--goal-id", help="Goal ID."),
    title: str = typer.Option("", "--title", help="Goal title."),
    attention: str | None = typer.Option(None, "--attention", help="Attention queue item."),
) -> None:
    """Control 24/7 long-horizon reversing goals via LoopX control plane."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action": action,
        "project_id": project_id,
    }
    if goal_id:
        args["goal_id"] = goal_id
    if title:
        args["title"] = title
    if attention:
        args["attention_item"] = attention
    payload = asyncio.run(
        _invoke(_runtime(state, "swarm"), "loopx_goal_control_plane", args, profile="swarm")
    )
    _emit(state, payload, title="LoopX Goal Control Plane")


# --- Phase 16: Cognitive, Adversarial & Exploit Economics CLI Commands ---


@cognitive_app.command("elephant-draft")
def cognitive_elephant_draft_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    target: str = typer.Option(..., "--target", "-t", help="Target component or class."),
    overview: str = typer.Option(
        "Full architecture overview", "--overview", "-o", help="Architecture overview."
    ),
    codebase: str = typer.Option(
        "Decompiled classes and manifest context", "--codebase", "-c", help="Codebase context."
    ),
) -> None:
    """Draft full-context reversing specification using Elephant agent."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "target_component": target,
        "architecture_overview": overview,
        "codebase_context": codebase,
        "claims": [
            {"claim_id": "claim_01", "claim_text": f"Component {target} handles sensitive crypto."}
        ],
    }
    payload = asyncio.run(_invoke(_runtime(state), "audit_elephant_draft_spec", args))
    _emit(state, payload, title="Elephant Full-Context Reversing Specification")


@cognitive_app.command("goldfish-review")
def cognitive_goldfish_review_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    claim_id: str = typer.Option(..., "--claim-id", help="Claim identifier."),
    claim_text: str = typer.Option(..., "--claim-text", help="Claim text to review."),
    evidence: list[str] = typer.Option(
        [], "--evidence", "-e", help="Isolated empirical evidence snippets."
    ),
) -> None:
    """Execute zero-context adversarial audit on proposed findings."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "claim_id": claim_id,
        "claim_text": claim_text,
        "isolated_evidence": evidence,
    }
    payload = asyncio.run(_invoke(_runtime(state), "audit_goldfish_adversarial_review", args))
    _emit(state, payload, title="Goldfish Zero-Context Adversarial Review")


@cognitive_app.command("adk-workflow")
def cognitive_adk_workflow_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    name: str = typer.Option("adk_pipeline", "--name", "-n", help="ADK workflow name."),
) -> None:
    """Execute Google ADK Python state machine workflow with OpenTelemetry tracing."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "workflow_name": name,
    }
    payload = asyncio.run(_invoke(_runtime(state), "adk_workflow_run", args))
    _emit(state, payload, title="Google ADK Workflow Execution")


@cognitive_app.command("strategy-select")
def cognitive_strategy_select_cmd(
    ctx: typer.Context,
    target: str = typer.Option(..., "--target", "-t", help="Target APK or component."),
    obfuscation: str = typer.Option(
        "low", "--obfuscation", help="none, low, medium, high, packed."
    ),
    crypto: bool = typer.Option(False, "--crypto", help="Whether target has native JNI crypto."),
    loc: int = typer.Option(1000, "--loc", help="Estimated lines of code."),
) -> None:
    """Select optimal cognitive reasoning paradigm (Fast ReAct, Plan-Solve, Debate)."""
    state = _state(ctx)
    args = {
        "target": target,
        "obfuscation_level": obfuscation,
        "has_native_crypto": crypto,
        "lines_of_code": loc,
    }
    payload = asyncio.run(_invoke(_runtime(state), "reasoning_strategy_select", args))
    _emit(state, payload, title="Cognitive Reasoning Strategy Decision")


@cognitive_app.command("iap-audit")
def cognitive_iap_audit_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
) -> None:
    """Audit In-App Purchase and monetization workflows for client-side bypasses."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "declared_permissions": ["com.android.vending.BILLING"],
        "decompiled_classes": ["com.target.billing.BillingManager"],
        "string_constants": ["onPurchasesUpdated", "verifyReceiptLocally"],
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "api"), "fin_iap_billing_audit", args, profile="api")
    )
    _emit(state, payload, title="IAP & Monetization Vulnerability Audit")


@cognitive_app.command("exploit-payoff")
def cognitive_exploit_payoff_cmd(
    ctx: typer.Context,
    vuln_id: str = typer.Option(..., "--vuln-id", help="Vulnerability ID."),
    title: str = typer.Option(..., "--title", help="Vulnerability title."),
    severity: str = typer.Option("high", "--severity", help="low, medium, high, critical."),
    skill: str = typer.Option("intermediate", "--skill", help="Attacker skill required."),
    asset: str = typer.Option("payment_bypass", "--asset", help="Exploit asset type."),
) -> None:
    """Simulate quantitative exploit economics matrix via QuantDinger."""
    state = _state(ctx)
    args = {
        "vulnerability_id": vuln_id,
        "vulnerability_title": title,
        "severity": severity,
        "attacker_skill_required": skill,
        "exploit_asset_type": asset,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "exploit_payoff_simulate", args, profile="admin")
    )
    _emit(state, payload, title="QuantDinger Exploit Payoff Simulation")


@cognitive_app.command("exec-briefing")
def cognitive_exec_briefing_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    app_name: str = typer.Option("Target Mobile App", "--name", "-n", help="Application name."),
) -> None:
    """Synthesize board-level executive risk summary and compliance impact."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "app_name": app_name,
        "vulnerabilities": [
            {"severity": "critical", "title": "Client-Side Billing Bypass"},
            {"severity": "high", "title": "Hardcoded Cryptographic Master Key"},
        ],
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "exec_briefing_synthesize", args, profile="admin")
    )
    _emit(state, payload, title="Executive Cyber Risk Briefing")


@cognitive_app.command("whitepaper")
def cognitive_whitepaper_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    title: str = typer.Option(..., "--title", help="Research paper title."),
) -> None:
    """Synthesize academic-grade vulnerability research whitepaper via Dr. Claw."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "paper_title": title,
        "vulnerability_mechanisms": [
            "Control flow obfuscation flattening",
            "Weak IV reuse in CBC cipher",
        ],
    }
    payload = asyncio.run(
        _invoke(
            _runtime(state, "admin"), "sec_research_whitepaper_synthesize", args, profile="admin"
        )
    )
    _emit(state, payload, title="Academic Research Whitepaper & CVE Disclosure")


@cognitive_app.command("haystack")
def cognitive_haystack_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    query: str = typer.Option(..., "--query", "-q", help="Search query."),
) -> None:
    """Query decompiled code repositories using Haystack hybrid RAG search."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "query": query,
    }
    payload = asyncio.run(_invoke(_runtime(state), "rag_haystack_query", args))
    _emit(state, payload, title="Haystack Decompiled Code Search")


# --- Phase 17: Next-Gen Binary Decompilation, Advanced Apple Analysis & Hardware CLI Commands ---


@binary_app.command("kuna-decompile")
def binary_kuna_decompile_cmd(
    ctx: typer.Context,
    library: str = typer.Option(
        ..., "--lib", "-l", help="Native library filename (e.g. libcrypto.so)."
    ),
    arch: str = typer.Option("arm64-v8a", "--arch", "-a", help="Target architecture."),
    symbol: str | None = typer.Option(None, "--symbol", "-s", help="Symbol filter."),
) -> None:
    """Decompile native binary via Kuna fast Rust decompiler."""
    state = _state(ctx)
    args = {
        "library_name": library,
        "target_arch": arch,
    }
    if symbol:
        args["symbol_filter"] = symbol
    payload = asyncio.run(_invoke(_runtime(state), "kuna_rust_decompile", args))
    _emit(state, payload, title="Kuna Rust Native Decompilation")


@binary_app.command("retdec-decompile")
def binary_retdec_decompile_cmd(
    ctx: typer.Context,
    library: str = typer.Option(..., "--lib", "-l", help="Native library filename."),
    arch: str = typer.Option("arm64-v8a", "--arch", "-a", help="Target architecture."),
) -> None:
    """Decompile native binary via RetDec LLVM decompilation backend."""
    state = _state(ctx)
    args = {
        "library_name": library,
        "target_arch": arch,
    }
    payload = asyncio.run(_invoke(_runtime(state), "retdec_native_decompile", args))
    _emit(state, payload, title="RetDec LLVM Native Decompilation")


@binary_app.command("macho-demangle")
def binary_macho_demangle_cmd(
    ctx: typer.Context,
    path: str = typer.Option(..., "--path", "-p", help="Path to Mach-O binary in IPA Payload."),
) -> None:
    """Demangle Swift/ObjC symbols and parse Mach-O headers via Malimite."""
    state = _state(ctx)
    args = {"binary_path": path}
    payload = asyncio.run(_invoke(_runtime(state), "malimite_macho_demangle", args))
    _emit(state, payload, title="Malimite Mach-O Symbol Demangling & Header Inspection")


@binary_app.command("swift-sections")
def binary_swift_sections_cmd(
    ctx: typer.Context,
    path: str = typer.Option(..., "--path", "-p", help="Path to Mach-O binary."),
) -> None:
    """Parse Mach-O Swift reflection sections and metadata."""
    state = _state(ctx)
    args = {"binary_path": path}
    payload = asyncio.run(_invoke(_runtime(state), "macho_swift_section_parse", args))
    _emit(state, payload, title="Mach-O Swift Reflection Section Parsing")


@binary_app.command("objc-reconstruct")
def binary_objc_reconstruct_cmd(
    ctx: typer.Context,
    path: str = typer.Option(..., "--path", "-p", help="Path to Mach-O binary."),
) -> None:
    """Reconstruct Objective-C class interfaces and class-dump headers."""
    state = _state(ctx)
    args = {"binary_path": path}
    payload = asyncio.run(_invoke(_runtime(state), "objc_helper_macho_reconstruct", args))
    _emit(state, payload, title="Objective-C Interface Reconstruction")


@binary_app.command("gdb-session")
def binary_gdb_session_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "start", "--action", help="start, command, breakpoint, registers, stop."
    ),
    target: str = typer.Option(..., "--target", "-t", help="Path to target binary."),
    session_id: str | None = typer.Option(None, "--session-id", help="Active session ID."),
    command: str | None = typer.Option(None, "--command", "-c", help="GDB/MI command."),
    breakpoint: str | None = typer.Option(
        None, "--breakpoint", "-b", help="Symbol or hex address."
    ),
) -> None:
    """Automate native GDB/MI interactive debugging session."""
    state = _state(ctx)
    args: dict[str, Any] = {
        "action": action,
        "target_binary": target,
    }
    if session_id:
        args["session_id"] = session_id
    if command:
        args["command_str"] = command
    if breakpoint:
        args["breakpoint_location"] = breakpoint
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "native_gdb_mi_session", args, profile="dynamic")
    )
    _emit(state, payload, title="GDB/MI Debugger Session")


@binary_app.command("objdump-dwarf")
def binary_objdump_dwarf_cmd(
    ctx: typer.Context,
    target: str = typer.Option(..., "--target", "-t", help="Path to native ELF or Mach-O library."),
    symbol: str | None = typer.Option(None, "--symbol", "-s", help="Target symbol to disassemble."),
) -> None:
    """Inspect native disassembly and DWARF debug line numbers via llvm-objdump."""
    state = _state(ctx)
    args: dict[str, Any] = {"target_file": target}
    if symbol:
        args["target_symbol"] = symbol
    payload = asyncio.run(_invoke(_runtime(state), "native_objdump_dwarf_inspect", args))
    _emit(state, payload, title="Native Objdump & DWARF Inspection")


@binary_app.command("rizin-bridge")
def binary_rizin_bridge_cmd(
    ctx: typer.Context,
    target: str = typer.Option(..., "--target", "-t", help="Path to native library."),
) -> None:
    """Bridge Rizin / Cutter headless for CFG graph extraction and radare2 analysis."""
    state = _state(ctx)
    args = {"target_file": target}
    payload = asyncio.run(_invoke(_runtime(state), "engine_rizin_cutter_bridge", args))
    _emit(state, payload, title="Rizin / Cutter Headless Analysis Bridge")


@binary_app.command("ghidra-bridge")
def binary_ghidra_bridge_cmd(
    ctx: typer.Context,
    target: str = typer.Option(..., "--target", "-t", help="Path to native library."),
    script: str = typer.Option(
        "DecompileHeadless.java", "--script", "-s", help="Ghidra analysis script."
    ),
) -> None:
    """Run Ghidra headless decompiler bridge with Java analysis scripts."""
    state = _state(ctx)
    args = {"target_file": target, "analysis_script": script}
    payload = asyncio.run(_invoke(_runtime(state), "engine_ghidra_headless_bridge", args))
    _emit(state, payload, title="Ghidra Headless Decompiler Bridge")


@binary_app.command("iot-extract")
def binary_iot_extract_cmd(
    ctx: typer.Context,
    apk: str = typer.Option(..., "--apk", help="Path to companion APK."),
) -> None:
    """Extract embedded IoT firmware partitions, OTA blobs, and BLE keys from APK."""
    state = _state(ctx)
    args = {"apk_path": apk}
    payload = asyncio.run(_invoke(_runtime(state), "iot_firmware_partition_extract", args))
    _emit(state, payload, title="IoT Firmware Partition Extraction")


@binary_app.command("lock-bypass")
def binary_lock_bypass_cmd(
    ctx: typer.Context,
    device: str = typer.Option(..., "--device", "-d", help="ADB device serial."),
) -> None:
    """Bypass lockscreen via ADB gesture/keyguard clearing."""
    state = _state(ctx)
    args = {"device_id": device}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "device_lock_bypass_adb", args, profile="dynamic")
    )
    _emit(state, payload, title="ADB Lockscreen Keyguard Bypass")


@binary_app.command("lock-bruteforce")
def binary_lock_bruteforce_cmd(
    ctx: typer.Context,
    device: str = typer.Option(..., "--device", "-d", help="ADB device serial."),
    digits: int = typer.Option(4, "--digits", help="PIN length (4-6 digits)."),
) -> None:
    """Perform dictionary/brute-force ADB lockscreen PIN test."""
    state = _state(ctx)
    args = {"device_id": device, "max_digits": digits}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "device_lock_bruteforce_adb", args, profile="dynamic")
    )
    _emit(state, payload, title="ADB Lockscreen PIN Brute-force")


@binary_app.command("ducky-payload")
def binary_ducky_payload_cmd(
    ctx: typer.Context,
    pin: str = typer.Option("1234", "--pin", help="Target PIN for HID injection."),
) -> None:
    """Generate USB Rubber Ducky / BadUSB keystroke injection scripts for lockscreens."""
    state = _state(ctx)
    args = {"target_pin": pin}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "device_hid_ducky_payload_gen", args, profile="dynamic")
    )
    _emit(state, payload, title="USB Rubber Ducky HID Keystroke Payload")


@binary_app.command("gatekeeper-clear")
def binary_gatekeeper_clear_cmd(
    ctx: typer.Context,
    device: str = typer.Option(..., "--device", "-d", help="ADB device serial."),
) -> None:
    """Clear Android Gatekeeper/Locksettings credentials (root ADB required)."""
    state = _state(ctx)
    args = {"device_id": device}
    payload = asyncio.run(
        _invoke(
            _runtime(state, "dynamic"),
            "device_gatekeeper_credential_clear",
            args,
            profile="dynamic",
        )
    )
    _emit(state, payload, title="Gatekeeper Locksettings Credential Clear")


@binary_app.command("xposed-hook")
def binary_xposed_hook_cmd(
    ctx: typer.Context,
    device: str = typer.Option(..., "--device", "-d", help="ADB device serial."),
) -> None:
    """Inject LSPosed / Xposed runtime hook to bypass KeyguardManager isDeviceLocked."""
    state = _state(ctx)
    args = {"device_id": device}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "xposed_unlock_hook_inject", args, profile="dynamic")
    )
    _emit(state, payload, title="LSPosed/Xposed Keyguard Unlock Hook Injection")


@binary_app.command("nanobot-daemon")
def binary_nanobot_daemon_cmd(
    ctx: typer.Context,
    action: str = typer.Option("status", "--action", help="start, stop, status, schedule_cron."),
    cron: str | None = typer.Option(None, "--cron", help="Cron schedule expression."),
    job: str | None = typer.Option(None, "--job", help="Job identifier."),
) -> None:
    """Manage ultra-lightweight autonomous Nanobot background cron tasks."""
    state = _state(ctx)
    args: dict[str, Any] = {"action": action}
    if cron:
        args["cron_expression"] = cron
    if job:
        args["job_name"] = job
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "nanobot_daemon_ctl", args, profile="admin")
    )
    _emit(state, payload, title="Nanobot Autonomous Background Daemon")


@binary_app.command("nanobot-notify")
def binary_nanobot_notify_cmd(
    ctx: typer.Context,
    channel: str = typer.Option("telegram", "--channel", help="telegram, slack, discord."),
    title: str = typer.Option(..., "--title", help="Alert title."),
    message: str = typer.Option(..., "--message", "-m", help="Alert message body."),
    severity: str = typer.Option("HIGH", "--severity", help="Severity level."),
) -> None:
    """Dispatch real-time chat alert notifications via Nanobot integrations."""
    state = _state(ctx)
    args = {
        "channel": channel,
        "title": title,
        "message": message,
        "severity": severity,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "nanobot_notify_dispatch", args, profile="admin")
    )
    _emit(state, payload, title="Nanobot Real-Time Chat Alert Dispatch")


@binary_app.command("lastbook")
def binary_lastbook_cmd(
    ctx: typer.Context,
    query: str = typer.Option(..., "--query", "-q", help="Search query."),
    category: str = typer.Option(
        "mastg",
        "--category",
        "-c",
        help="mastg, permissions, opcodes_arm64, opcodes_dalvik, cve_dict.",
    ),
) -> None:
    """Query Lastbook air-gapped offline reversing cheat-sheets and specifications."""
    state = _state(ctx)
    args = {
        "query": query,
        "category": category,
    }
    payload = asyncio.run(_invoke(_runtime(state), "airgap_lastbook_query", args))
    _emit(state, payload, title="Lastbook Air-Gapped Offline Knowledge Base")


# --- Phase 18: Autonomous UI Reconstruction, Living Canvas & Cross-Platform Re-Engineering CLI Commands ---


@canvas_app.command("stitch-modernize")
def canvas_stitch_modernize_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    layout_xml: str = typer.Option(
        "<LinearLayout></LinearLayout>", "--layout", "-l", help="XML layout snippet."
    ),
    framework: str = typer.Option(
        "jetpack_compose", "--framework", "-f", help="jetpack_compose, react_native, flutter."
    ),
) -> None:
    """Modernize legacy Android XML layout into modern Compose/React Native via Google Stitch."""
    state = _state(ctx)
    args = {
        "project_id": project_id,
        "layout_xml": layout_xml,
        "target_framework": framework,
    }
    payload = asyncio.run(_invoke(_runtime(state), "stitch_ui_modernize", args))
    _emit(state, payload, title="Google Stitch UI Modernization")


@canvas_app.command("stitch-spec")
def canvas_stitch_spec_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    theme: str = typer.Option("MaterialTheme", "--theme", "-t", help="Theme name."),
) -> None:
    """Export DESIGN.md design token and component catalog specifications."""
    state = _state(ctx)
    args = {"project_id": project_id, "theme_name": theme}
    payload = asyncio.run(_invoke(_runtime(state), "stitch_design_spec_export", args))
    _emit(state, payload, title="Google Stitch DESIGN.md Token Specification")


@canvas_app.command("hig-audit")
def canvas_hig_audit_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    view: str = typer.Option(
        "MainScreen", "--view", "-v", help="Target view or screen identifier."
    ),
) -> None:
    """Audit mobile UI layout against Apple Human Interface Guidelines."""
    state = _state(ctx)
    args = {"project_id": project_id, "target_view": view}
    payload = asyncio.run(_invoke(_runtime(state), "hig_doctor_compliance_audit", args))
    _emit(state, payload, title="Apple HIG Doctor Compliance Audit")


@canvas_app.command("liquid-glass")
def canvas_liquid_glass_cmd(
    ctx: typer.Context,
    name: str = typer.Option("GlassCard", "--name", "-n", help="Widget name."),
    framework: str = typer.Option("flutter", "--framework", "-f", help="flutter or swiftui."),
) -> None:
    """Synthesize modern Liquid Glass widget with authentic fragment shader blurs."""
    state = _state(ctx)
    args = {"widget_name": name, "framework": framework}
    payload = asyncio.run(_invoke(_runtime(state), "ui_liquid_glass_widget_gen", args))
    _emit(state, payload, title="Liquid Glass Shader Widget Generator")


@canvas_app.command("bento-grid")
def canvas_bento_grid_cmd(
    ctx: typer.Context,
    title: str = typer.Option("App Audit Overview", "--title", "-t", help="Bento grid title."),
) -> None:
    """Render Apple-inspired Bento Grid presentation cards for audit metrics."""
    state = _state(ctx)
    args = {"grid_title": title, "metrics": {"security_score": "A", "exported_components": 3}}
    payload = asyncio.run(_invoke(_runtime(state), "ui_bento_grid_summary_render", args))
    _emit(state, payload, title="Apple Bento Grid Dashboard Presentation")


@canvas_app.command("clean-lint")
def canvas_clean_lint_cmd(
    ctx: typer.Context,
    file_path: str = typer.Option(..., "--file", "-f", help="Target file path."),
    code: str = typer.Option("class MainActivity {}", "--code", "-c", help="Source code snippet."),
) -> None:
    """Refactor and lint decompiled code against Clean Architecture & DDD principles."""
    state = _state(ctx)
    args = {"file_path": file_path, "source_code": code}
    payload = asyncio.run(_invoke(_runtime(state), "reconstruct_clean_arch_lint", args))
    _emit(state, payload, title="Clean Architecture & DDD Refactoring Linter")


@canvas_app.command("clean-spec")
def canvas_clean_spec_cmd(
    ctx: typer.Context,
    module: str = typer.Option(..., "--module", "-m", help="Module or component name."),
    context: str = typer.Option(
        "Auth subsystem context", "--context", "-c", help="Decompiled context."
    ),
) -> None:
    """Synthesize clean-room non-infringing functional specifications."""
    state = _state(ctx)
    args = {"module_name": module, "decompiled_context": context}
    payload = asyncio.run(_invoke(_runtime(state), "clean_room_spec_extract", args))
    _emit(state, payload, title="Clean-Room Functional Specification")


@canvas_app.command("viewport-match")
def canvas_viewport_match_cmd(
    ctx: typer.Context,
    screen: str = typer.Option(..., "--screen", "-s", help="Screen name to validate."),
) -> None:
    """Validate reconstructed layouts across phone, foldable, and tablet viewports."""
    state = _state(ctx)
    args = {"screen_name": screen}
    payload = asyncio.run(_invoke(_runtime(state), "ui_multi_viewport_match", args))
    _emit(state, payload, title="Multi-Viewport Semantic AST Layout Matcher")


@canvas_app.command("tokens-extract")
def canvas_tokens_extract_cmd(
    ctx: typer.Context,
    apk: str = typer.Option(..., "--apk", help="Path to APK file."),
) -> None:
    """Extract design palettes, typography scales, and spacing tokens into tokens.json."""
    state = _state(ctx)
    args = {"apk_path": apk}
    payload = asyncio.run(_invoke(_runtime(state), "assets_palette_typography_extract", args))
    _emit(state, payload, title="Design Token & Typography Extractor")


@canvas_app.command("unity-dump")
def canvas_unity_dump_cmd(
    ctx: typer.Context,
    package: str = typer.Option(..., "--package", "-p", help="Target package name."),
) -> None:
    """Extract Unity serialized assets, AssetBundles, and C# scripts from game APK."""
    state = _state(ctx)
    args = {"package_name": package}
    payload = asyncio.run(_invoke(_runtime(state), "game_unity_asset_dump", args))
    _emit(state, payload, title="Unity Game Asset & Script Dumper")


@canvas_app.command("godot-extract")
def canvas_godot_extract_cmd(
    ctx: typer.Context,
    package: str = typer.Option(..., "--package", "-p", help="Target package name."),
) -> None:
    """Unpack embedded Godot .pck archives and GDScript sources."""
    state = _state(ctx)
    args = {"package_name": package}
    payload = asyncio.run(_invoke(_runtime(state), "game_godot_pck_extract", args))
    _emit(state, payload, title="Godot PCK Archive Extractor")


@canvas_app.command("sqlite-forensics")
def canvas_sqlite_forensics_cmd(
    ctx: typer.Context,
    db: str = typer.Option(..., "--db", "-d", help="Path to SQLite database file."),
    key: str | None = typer.Option(None, "--key", "-k", help="Optional SQLCipher key."),
) -> None:
    """Forensically recover mobile SQLite tables, WAL journal records, and SQLCipher keys."""
    state = _state(ctx)
    args: dict[str, Any] = {"database_path": db}
    if key:
        args["encryption_key"] = key
    payload = asyncio.run(_invoke(_runtime(state), "db_sqlite_forensic_extract", args))
    _emit(state, payload, title="Mobile SQLite & SQLCipher Forensics")


@canvas_app.command("docmd-compile")
def canvas_docmd_compile_cmd(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", "-p", help="Target project ID."),
    title: str = typer.Option("RAA Intelligence Portal", "--title", "-t", help="Portal title."),
) -> None:
    """Compile workspace docs into single-source static portal and llms.txt context file."""
    state = _state(ctx)
    args = {"project_id": project_id, "title": title}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "docmd_llms_txt_compile", args, profile="admin")
    )
    _emit(state, payload, title="docmd Portal & llms.txt Context Compiler")


@canvas_app.command("skill-evolve")
def canvas_skill_evolve_cmd(
    ctx: typer.Context,
    skill: str = typer.Option(..., "--skill", "-s", help="Skill name to evolve."),
    feedback: list[str] = typer.Option(
        [], "--feedback", "-f", help="User corrections and feedback."
    ),
) -> None:
    """Analyze session corrections to propose automated self-evolution prompt diffs."""
    state = _state(ctx)
    args = {"skill_name": skill, "feedback_history": feedback}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "task_observer_skill_evolve", args, profile="admin")
    )
    _emit(state, payload, title="Task Observer Skill Self-Evolution Meta-Agent")


@canvas_app.command("coworker-dot")
def canvas_coworker_dot_cmd(
    ctx: typer.Context,
    action: str = typer.Option("connect", "--action", "-a", help="connect, status, disconnect."),
) -> None:
    """Manage WebRTC audio/video session with persistent reversing coworker (RAA Dot)."""
    state = _state(ctx)
    args = {"action": action}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "dot_coworker_webrtc_session", args, profile="dynamic")
    )
    _emit(state, payload, title="RAA Dot Persistent Reversing Coworker")


@canvas_app.command("ekko-pipeline")
def canvas_ekko_pipeline_cmd(
    ctx: typer.Context,
    graph: str = typer.Option(..., "--graph", "-g", help="Visual node graph name."),
) -> None:
    """Execute visual node-based reversing workflow graphs from Ekko Studio."""
    state = _state(ctx)
    args = {"graph_name": graph}
    payload = asyncio.run(_invoke(_runtime(state), "ekko_canvas_pipeline_run", args))
    _emit(state, payload, title="Ekko Studio Visual Node Pipeline Runner")


@canvas_app.command("tui-codewhale")
def canvas_tui_codewhale_cmd(
    ctx: typer.Context,
    action: str = typer.Option("launch", "--action", "-a", help="launch, status, detach."),
) -> None:
    """Manage Codewhale high-performance terminal TUI session with subagent monitoring."""
    state = _state(ctx)
    args = {"action": action}
    payload = asyncio.run(_invoke(_runtime(state), "tui_codewhale_session", args))
    _emit(state, payload, title="Codewhale Terminal TUI Session")


@canvas_app.command("receipt-sign")
def canvas_receipt_sign_cmd(
    ctx: typer.Context,
    tool: str = typer.Option(..., "--tool", "-t", help="Tool name."),
    input_data: str = typer.Option("{}", "--input", "-i", help="Input data string."),
    output_data: str = typer.Option("{}", "--output", "-o", help="Output data string."),
) -> None:
    """Generate SHA-256 HMAC cryptographic execution receipt for audit compliance."""
    state = _state(ctx)
    args = {
        "tool_name": tool,
        "input_data": input_data,
        "output_data": output_data,
    }
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "receipt_cryptographic_sign", args, profile="admin")
    )
    _emit(state, payload, title="Cryptographic Execution Receipt Signer")


@canvas_app.command("sodu-cicd")
def canvas_sodu_cicd_cmd(
    ctx: typer.Context,
    apk: str = typer.Option(..., "--apk", help="Target APK path."),
    recipe: str = typer.Option("patch_root_bypass", "--recipe", "-r", help="Patch recipe."),
) -> None:
    """Execute closed-loop decompile-patch-build-verify pipeline with automated rollback."""
    state = _state(ctx)
    args = {"target_apk": apk, "patch_recipe": recipe}
    payload = asyncio.run(_invoke(_runtime(state), "sodu_cicd_pipeline_run", args))
    _emit(state, payload, title="Sodu Closed-Loop Decompile-Patch-Build Pipeline")


@canvas_app.command("gh-actions-gen")
def canvas_gh_actions_gen_cmd(
    ctx: typer.Context,
    name: str = typer.Option("MobileApp", "--name", "-n", help="Application name."),
) -> None:
    """Generate GitHub Actions CI/CD workflow YAML for Android building and v2/v3 signing."""
    state = _state(ctx)
    args = {"app_name": name}
    payload = asyncio.run(_invoke(_runtime(state), "gh_actions_build_android", args))
    _emit(state, payload, title="GitHub Actions Rebuild & Sign Workflow Generator")


# --- Phase 19: Enterprise MCP & Multi-Harness CLI Ecosystem CLI Commands ---


@enterprise_app.command("postman-run")
def enterprise_postman_run_cmd(
    ctx: typer.Context,
    collection: str = typer.Option(
        ..., "--collection", "-c", help="Path to Postman collection JSON."
    ),
) -> None:
    """Execute Postman API collection and assertions via Postman MCP."""
    state = _state(ctx)
    args = {"collection_path": collection}
    payload = asyncio.run(_invoke(_runtime(state), "mcp_postman_collection_run", args))
    _emit(state, payload, title="Postman MCP API Test Collection Runner")


@enterprise_app.command("postman-assert")
def enterprise_postman_assert_cmd(
    ctx: typer.Context,
    endpoint: str = typer.Option(..., "--endpoint", "-e", help="Endpoint URL to test."),
    status: int = typer.Option(200, "--status", "-s", help="Expected HTTP status code."),
) -> None:
    """Validate API endpoint responses against expected security contracts."""
    state = _state(ctx)
    args = {"endpoint_url": endpoint, "expected_status": status}
    payload = asyncio.run(_invoke(_runtime(state), "mcp_postman_test_assert", args))
    _emit(state, payload, title="Postman Living Contract Assertion Tester")


@enterprise_app.command("github-pr")
def enterprise_github_pr_cmd(
    ctx: typer.Context,
    repo: str = typer.Option(..., "--repo", "-r", help="Repository (owner/repo)."),
    title: str = typer.Option(..., "--title", "-t", help="PR title."),
    head: str = typer.Option(..., "--head", "-h", help="Head feature branch."),
    base: str = typer.Option("main", "--base", "-b", help="Base branch."),
) -> None:
    """Manage Git repositories and open Pull Requests via GitHub MCP."""
    state = _state(ctx)
    args = {"repo": repo, "title": title, "head_branch": head, "base_branch": base}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "mcp_github_pr_manage", args, profile="admin")
    )
    _emit(state, payload, title="GitHub MCP Pull Request Manager")


@enterprise_app.command("playwright-webview")
def enterprise_playwright_webview_cmd(
    ctx: typer.Context,
    url: str = typer.Option(..., "--url", "-u", help="Target WebView or companion URL."),
) -> None:
    """Control in-app WebViews and intercept OAuth tokens via Playwright MCP."""
    state = _state(ctx)
    args = {"target_url": url, "capture_oauth": True}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "mcp_playwright_webview_test", args, profile="dynamic")
    )
    _emit(state, payload, title="Playwright MCP WebView & OAuth Tester")


@enterprise_app.command("apify-scrape")
def enterprise_apify_scrape_cmd(
    ctx: typer.Context,
    app_id: str = typer.Option(..., "--app-id", "-a", help="Target application package ID."),
    store: str = typer.Option(
        "google_play", "--store", "-s", help="google_play or apple_app_store."
    ),
) -> None:
    """Scrape Google Play and App Store intelligence via Apify MCP."""
    state = _state(ctx)
    args = {"app_id": app_id, "store": store}
    payload = asyncio.run(_invoke(_runtime(state), "mcp_apify_store_scrape", args))
    _emit(state, payload, title="Apify MCP App Store Intelligence Scraper")


@enterprise_app.command("cli-dispatch")
def enterprise_cli_dispatch_cmd(
    ctx: typer.Context,
    harness: str = typer.Option(
        "claude_code",
        "--harness",
        "-h",
        help="claude_code, codex, gemini_cli, antigravity, deepseek_cli, minimax_cli, grok_build.",
    ),
    task: str = typer.Option(..., "--task", "-t", help="Task instruction string."),
) -> None:
    """Dispatch tasks to external coding CLIs via unified 7-CLI gateway."""
    state = _state(ctx)
    args = {"harness": harness, "task_instruction": task}
    payload = asyncio.run(_invoke(_runtime(state), "cli_harness_dispatch", args))
    _emit(state, payload, title="Universal Multi-Harness 7-CLI Gateway")


@enterprise_app.command("omnigent-enforce")
def enterprise_omnigent_enforce_cmd(
    ctx: typer.Context,
    agent_id: str = typer.Option(..., "--agent-id", "-a", help="Agent identifier."),
    action: str = typer.Option(..., "--action", help="Action requested."),
) -> None:
    """Validate and enforce fail-closed security and budget policies via Omnigent."""
    state = _state(ctx)
    args = {"agent_id": agent_id, "requested_action": action}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "omnigent_meta_policy_enforce", args, profile="admin")
    )
    _emit(state, payload, title="Omnigent Meta-Policy & Boundary Enforcer")


@enterprise_app.command("nacos-register")
def enterprise_nacos_register_cmd(
    ctx: typer.Context,
    service: str = typer.Option("raa-mcp-service", "--service", "-s", help="Service name."),
    tools: int = typer.Option(312, "--tools", "-t", help="Number of registered tools."),
) -> None:
    """Register RAA MCP tool capabilities into enterprise Nacos service registries."""
    state = _state(ctx)
    args = {"service_name": service, "tools_count": tools}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "spring_ai_nacos_register", args, profile="admin")
    )
    _emit(state, payload, title="Spring AI Nacos Service Discovery Registry")


@enterprise_app.command("n8n-sync")
def enterprise_n8n_sync_cmd(
    ctx: typer.Context,
    workflow: str = typer.Option(..., "--workflow", "-w", help="n8n workflow name."),
    trigger: str = typer.Option(
        "vulnerability_found", "--trigger", "-t", help="Trigger event name."
    ),
) -> None:
    """Emit and synchronize n8n workflow definitions as code (n8nac)."""
    state = _state(ctx)
    args = {"workflow_name": workflow, "trigger_event": trigger}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "n8n_workflow_bridge_sync", args, profile="admin")
    )
    _emit(state, payload, title="Enterprise n8n Workflow Automation Bridge")


@enterprise_app.command("wasm-sandbox")
def enterprise_wasm_sandbox_cmd(
    ctx: typer.Context,
    plugin: str = typer.Option(..., "--plugin", "-p", help="WASM plugin name."),
    hex_bytes: str = typer.Option("0061736d", "--bytes", "-b", help="Hex-encoded WASM bytes."),
) -> None:
    """Execute third-party inspection plugins inside isolated WASM sandbox."""
    state = _state(ctx)
    args = {"plugin_name": plugin, "plugin_bytes_hex": hex_bytes}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "engine_wasm_plugin_sandbox", args, profile="admin")
    )
    _emit(state, payload, title="WebAssembly (WASM) Sandboxed Tool Runtime")


@enterprise_app.command("simd-entropy")
def enterprise_simd_entropy_cmd(
    ctx: typer.Context,
    target: str = typer.Option(..., "--target", "-t", help="Target binary path."),
) -> None:
    """Scan raw binary sections for Shannon entropy heatmaps and packing via SIMD."""
    state = _state(ctx)
    args = {"target_binary": target}
    payload = asyncio.run(_invoke(_runtime(state), "binary_byte_search_entropy", args))
    _emit(state, payload, title="SIMD Byte Search & Entropy Analysis Engine")


@enterprise_app.command("mutation-guard")
def enterprise_mutation_guard_cmd(
    ctx: typer.Context,
    file_path: str = typer.Option(..., "--file", "-f", help="Target file path."),
    pre_hex: str = typer.Option("414141", "--pre", help="Hex bytes before patch."),
    post_hex: str = typer.Option("424242", "--post", help="Hex bytes after patch."),
) -> None:
    """Enforce pre/post mutation verification SHA-256 guardrails."""
    state = _state(ctx)
    args = {"file_path": file_path, "pre_data_hex": pre_hex, "post_data_hex": post_hex}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "forensic_mutation_digest_guard", args, profile="admin")
    )
    _emit(state, payload, title="Forensic Mutation Digest Guardrail")


# --- Phase 20: Offensive Security Operations & Benchmarks CLI ---


@offensive_app.command("yak-run")
def offensive_yak_run_cmd(
    ctx: typer.Context,
    playbook: str = typer.Option(..., "--playbook", "-p", help="Yaklang playbook name."),
    endpoint: str = typer.Option(..., "--endpoint", "-e", help="Target API endpoint URL."),
) -> None:
    """Execute automated penetration testing playbooks via Yaklang HackSkills."""
    state = _state(ctx)
    args = {"playbook_name": playbook, "target_endpoint": endpoint}
    payload = asyncio.run(_invoke(_runtime(state), "hack_yak_skill_run", args))
    _emit(state, payload, title="Yaklang HackSkills Offensive Penetration Playbook")


@offensive_app.command("mutate-403")
def offensive_mutate_403_cmd(
    ctx: typer.Context,
    url: str = typer.Option(..., "--url", "-u", help="401/403 restricted URL to mutate."),
) -> None:
    """Perform deep HTTP 401/403 access control bypass mutations."""
    state = _state(ctx)
    args = {"target_url": url}
    payload = asyncio.run(_invoke(_runtime(state), "hack_403_deep_mutate", args))
    _emit(state, payload, title="Deep HTTP 401/403 Access Control Bypass Mutator")


@offensive_app.command("computer-use")
def offensive_computer_use_cmd(
    ctx: typer.Context,
    app: str = typer.Option(
        ..., "--app", "-a", help="Target application: ghidra, ida_pro, jadx_gui, burp_suite."
    ),
    task: str = typer.Option(..., "--task", "-t", help="Autonomous reversing task description."),
) -> None:
    """Operate desktop GUI reversing tools via autonomous OS computer-use."""
    state = _state(ctx)
    args = {"target_application": app, "task_description": task}
    payload = asyncio.run(
        _invoke(_runtime(state, "dynamic"), "computer_use_gui_execute", args, profile="dynamic")
    )
    _emit(state, payload, title="Autonomous Computer-Use GUI Reversing Operator")


@offensive_app.command("frontier-mode")
def offensive_frontier_mode_cmd(
    ctx: typer.Context,
    mode: str = typer.Option(..., "--mode", "-m", help="Desired mode: react_fast or swarm_deep."),
    reason: str = typer.Option(
        "CLI invocation", "--reason", "-r", help="Justification for mode switch."
    ),
) -> None:
    """Dynamically toggle between single-agent ReAct and multi-agent swarm paradigms."""
    state = _state(ctx)
    args = {"desired_mode": mode, "reason": reason}
    payload = asyncio.run(_invoke(_runtime(state), "frontier_mode_switch", args))
    _emit(state, payload, title="FrontierAgent Dual ReAct / Swarm Switcher")


@offensive_app.command("gatekeeper-prompt")
def offensive_gatekeeper_prompt_cmd(
    ctx: typer.Context,
    operation: str = typer.Option(..., "--operation", "-o", help="Operation name to inspect."),
    preview: str = typer.Option(..., "--preview", "-p", help="Payload preview or diff."),
) -> None:
    """Generate OpenMausBot human-in-the-loop impact review and diff preview."""
    state = _state(ctx)
    args = {"operation_name": operation, "payload_preview": preview}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "mausbot_gatekeeper_prompt", args, profile="admin")
    )
    _emit(state, payload, title="OpenMausBot Safe Execution Gatekeeper & Diff Prompt")


@offensive_app.command("exploit-verify")
def offensive_exploit_verify_cmd(
    ctx: typer.Context,
    vuln_id: str = typer.Option(..., "--vuln-id", "-v", help="Vulnerability identifier."),
    steps: list[str] = typer.Option([], "--step", "-s", help="Step in proposed exploit chain."),
) -> None:
    """Verify non-destructive exploit PoC chain and validate safety boundaries."""
    state = _state(ctx)
    args = {"vulnerability_id": vuln_id, "proposed_chain": steps}
    payload = asyncio.run(_invoke(_runtime(state), "exploit_chain_verify", args))
    _emit(state, payload, title="Non-Destructive Exploit PoC Chaining & Validator")


@offensive_app.command("skillnet-eval")
def offensive_skillnet_eval_cmd(
    ctx: typer.Context,
    suite: str = typer.Option(
        "full_reverse_gym", "--suite", "-s", help="Evaluation benchmark suite name."
    ),
) -> None:
    """Evaluate agent skill competencies across SkillNet benchmark gym."""
    state = _state(ctx)
    args = {"benchmark_suite": suite}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "skillnet_benchmark_eval", args, profile="admin")
    )
    _emit(state, payload, title="SkillNet Systematic Benchmark & Evaluation Gym")


@offensive_app.command("skillpack")
def offensive_skillpack_cmd(
    ctx: typer.Context,
    action: str = typer.Option(
        "list", "--action", "-a", help="Action: package, validate, install, list."
    ),
    name: str = typer.Option("mobile_exploit_pack", "--name", "-n", help="SkillPack bundle name."),
) -> None:
    """Manage portable reverse engineering SkillPack distribution bundles."""
    state = _state(ctx)
    args = {"action": action, "skillpack_name": name}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "skillpack_bundle_manage", args, profile="admin")
    )
    _emit(state, payload, title="Portable Reversing SkillPack Packaging & Distribution")


@offensive_app.command("tamper-seal")
def offensive_tamper_seal_cmd(
    ctx: typer.Context,
    report: str = typer.Option(
        ..., "--report", "-r", help="Audit report markdown or JSON content."
    ),
) -> None:
    """Generate SHA-256 tamper seal and CycloneDX 1.5 SBOM manifest for audit report."""
    state = _state(ctx)
    args = {"report_content": report}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "audit_tamper_seal_v3", args, profile="admin")
    )
    _emit(state, payload, title="v3.0 Tamper-Evident Report Seal & Final Manifest")


@offensive_app.command("benchmark-v3")
def offensive_benchmark_v3_cmd(
    ctx: typer.Context,
    env: str = typer.Option("production", "--env", "-e", help="Target verification environment."),
) -> None:
    """Execute v3.0 production quality benchmark across all 322 tools."""
    state = _state(ctx)
    args = {"target_environment": env}
    payload = asyncio.run(
        _invoke(_runtime(state, "admin"), "v3_full_system_benchmark", args, profile="admin")
    )
    _emit(state, payload, title="v3.0 Full-System Benchmark & Production Quality Gate")


async def _run_stdio(runtime: Runtime, profile: ProfileName) -> None:
    from raa.mcp.server import run_stdio

    await run_stdio(runtime, profile)


async def _invoke(
    runtime: Runtime,
    name: str,
    arguments: dict[str, Any],
    profile: ProfileName | str | None = None,
) -> dict[str, Any]:
    try:
        envelope = await runtime.invoke(name, arguments, surface="cli", profile=profile)
        return envelope.model_dump(mode="json")
    except RAAError as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc


def _runtime(state: CliState, default_profile: str | None = None) -> Runtime:
    overrides: dict[str, Any] = {}
    if state.workspace is not None:
        overrides["workspace"] = state.workspace
    if state.profile is not None:
        overrides["profile"] = state.profile
    elif default_profile is not None:
        overrides["profile"] = default_profile
    settings = Settings(**overrides)
    configure_logging(settings.log_level, settings.log_json)
    return Runtime(settings)


def _state(ctx: typer.Context) -> CliState:
    if isinstance(ctx.obj, CliState):
        return ctx.obj
    return CliState()


def _profile(value: str) -> ProfileName:
    if value not in ALL_PROFILES:
        raise typer.BadParameter(f"Unknown profile '{value}'. Valid: {', '.join(ALL_PROFILES)}")
    return value


def _emit(state: CliState, payload: dict[str, Any], *, title: str | None = None) -> None:
    if state.json_output:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return
    if title:
        console.print(f"[bold]{title}[/bold]")
    data = payload.get("data", payload)
    console.print(Pretty(data))


def _print_error(exc: RAAError) -> None:
    console.print(f"[bold red]{exc.code}[/bold red]: {exc.message}")
    if exc.hint:
        console.print(f"[dim]{exc.hint}[/dim]")


def _raise_not_found(name: str) -> None:
    console.print(f"[bold red]not_found[/bold red]: Unknown tool '{name}'")
    raise typer.Exit(code=1)


def _client_config(agent: str, command: str, args: list[str]) -> str:
    if agent == "codex":
        rendered = ", ".join(json.dumps(item) for item in args)
        return f'[mcp_servers.raa]\ncommand = "raa"\nargs = [{rendered}]'
    if agent == "claude-code":
        return f"claude mcp add raa -- {command}"
    if agent == "vscode":
        payload = {
            "servers": {
                "raa": {"type": "stdio", "command": "raa", "args": args},
            }
        }
        return json.dumps(payload, indent=2)
    if agent in {"cursor", "claude-desktop", "gemini", "generic"}:
        payload = {"mcpServers": {"raa": {"command": "raa", "args": args}}}
        return json.dumps(payload, indent=2)
    raise typer.BadParameter(f"Unknown agent '{agent}'.")


# --- Phase 21 (v4.0.0) CLI Commands ---


@tools_app.command("install")
def tools_install_cli(
    ctx: typer.Context,
    tool_name: str = typer.Argument(
        ..., help="Tool ID: jadx, apktool, platform-tools, ghidra, frida, uber-apk-signer, or all."
    ),
    force: bool = typer.Option(False, "--force", help="Force re-download."),
) -> None:
    """Download, verify, and auto-configure tool path."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.tool_manager.download_tool(tool_name, force=force)
    _emit(state, res)


@tools_app.command("delete")
def tools_delete_cli(
    ctx: typer.Context,
    tool_name: str = typer.Argument(..., help="Tool ID to uninstall."),
) -> None:
    """Uninstall tool and reclaim disk space."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.tool_manager.delete_tool(tool_name)
    _emit(state, res)


# Channels CLI
@channel_app.command("test")
def channel_test_cli(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Target channel: telegram or whatsapp."),
    target: str = typer.Option("test_target", "--target", help="Chat ID or phone number."),
) -> None:
    """Send verification ping to configured Telegram or WhatsApp."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.channels.test_ping(channel, target)
    _emit(state, res)


@channel_app.command("pair")
def channel_pair_cli(
    ctx: typer.Context,
    channel: str = typer.Argument("whatsapp", help="Channel name (default: whatsapp)."),
) -> None:
    """Display terminal QR code for local WhatsApp Web pairing."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.channels.whatsapp.generate_pairing_qr()
    if not state.json_output:
        console.print(f"[bold green]WhatsApp QR Code Pairing[/bold green]\n{res['qr_ascii']}")
        console.print(f"[cyan]Pairing Code:[/cyan] [bold]{res['pairing_code']}[/bold]")
        console.print(f"[dim]{res['instructions']}[/dim]")
    else:
        _emit(state, res)


intensity_app = typer.Typer(
    help="Manage notification cadence and message intensity.", no_args_is_help=True
)
channel_app.add_typer(intensity_app, name="intensity")


@intensity_app.command("set")
def channel_intensity_set_cli(
    ctx: typer.Context,
    interval: str = typer.Option(
        "5m", "--interval", "-i", help="Interval string (e.g. 1m, 2m, 5m, 10m)."
    ),
    mode: str = typer.Option(
        "interval", "--mode", "-m", help="Cadence mode: start_end, interval, milestone, adaptive."
    ),
) -> None:
    """Set cadence: start/end, 1m, 2m, 5m, 10m, or custom."""
    state = _state(ctx)
    runtime = _runtime(state)
    digits = "".join(c for c in interval if c.isdigit())
    mins = int(digits) if digits else 5
    res = runtime.cadence.configure(mode=mode, interval_minutes=mins)
    _emit(state, res)


@intensity_app.command("status")
def channel_intensity_status_cli(ctx: typer.Context) -> None:
    """Display active notification cadence and stats."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.cadence.get_status()
    _emit(state, res)


# Skills Evolved CLI
@skill_app.command("list-evolved")
def skill_list_evolved_cli(ctx: typer.Context) -> None:
    """List dynamically learned recipes and patches."""
    state = _state(ctx)
    runtime = _runtime(state)
    recipes = runtime.self_evolution.list_procedures()
    _emit(state, {"evolved_recipes": recipes, "count": len(recipes)})


@skill_app.command("inspect")
def skill_inspect_cli(
    ctx: typer.Context,
    recipe_name: str = typer.Argument(..., help="Name of evolved recipe to inspect."),
) -> None:
    """View verified steps, selectors, and patch history."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.self_evolution.read_procedure(recipe_name)
    _emit(state, res)


# External MCP Mesh CLI
@mcp_mesh_app.command("list")
def mcp_mesh_list_cli(ctx: typer.Context) -> None:
    """List connected external MCP servers and tools."""
    state = _state(ctx)
    runtime = _runtime(state)
    servers = runtime.mcp_mesh.list_connectors()
    _emit(state, {"mcp_servers": servers, "count": len(servers)})


@mcp_mesh_app.command("connect")
def mcp_mesh_connect_cli(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Identifier for external MCP server."),
    transport: str = typer.Option(
        "stdio", "--transport", "-t", help="Transport: stdio, sse, streamable-http."
    ),
    command: str | None = typer.Option(None, "--command", "-c", help="Command for stdio."),
    url: str | None = typer.Option(None, "--url", "-u", help="URL for sse."),
) -> None:
    """Connect new external MCP server."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.mcp_mesh.connect(name=name, transport=transport, command=command, url=url)
    _emit(state, res)


@mcp_mesh_app.command("inspect")
def mcp_mesh_inspect_cli(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of MCP server to inspect."),
) -> None:
    """Inspect tools, schemas and status of an MCP server."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.mcp_mesh.inspect_server(name)
    _emit(state, res)


@mcp_mesh_app.command("test")
def mcp_mesh_test_cli(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of MCP server to test ping."),
) -> None:
    """Test JSON-RPC handshake and latency probe."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.mcp_mesh.test_ping(name)
    _emit(state, res)


@mcp_mesh_app.command("disconnect")
def mcp_mesh_disconnect_cli(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of MCP server to disconnect."),
) -> None:
    """Disconnect and unregister external MCP tools."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.mcp_mesh.disconnect(name)
    _emit(state, res)


@mcp_mesh_app.command("list-tools")
def mcp_mesh_list_tools_cli(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Connected MCP server name (e.g. rea, craft-anything)."),
    timeout_seconds: float = typer.Option(30.0, "--timeout", min=1.0, max=300.0),
) -> None:
    """Query live tools/list from a connected external MCP server."""
    state = _state(ctx)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "mcp_mesh_list_tools",
            {"name": name, "timeout_seconds": timeout_seconds},
        )
    )
    _emit(state, payload)


@mcp_mesh_app.command("call")
def mcp_mesh_call_cli(
    ctx: typer.Context,
    server_name: str = typer.Argument(
        ..., help="Connected MCP server name (e.g. rea, craft-anything)."
    ),
    tool_name: str = typer.Argument(..., help="Tool name on the external MCP server."),
    arguments_json: str = typer.Option("{}", "--args", help="JSON object of tool arguments."),
    timeout_seconds: float = typer.Option(60.0, "--timeout", min=1.0, max=600.0),
) -> None:
    """Invoke a tool on a connected external MCP server through RAA."""
    state = _state(ctx)
    parsed_args = json.loads(arguments_json)
    payload = asyncio.run(
        _invoke(
            _runtime(state),
            "mcp_mesh_call",
            {
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": parsed_args,
                "timeout_seconds": timeout_seconds,
            },
        )
    )
    _emit(state, payload)


# Device Wireless CLI
@device_app.command("pair")
def device_pair_cli(
    ctx: typer.Context,
    endpoint: str = typer.Argument(..., help="Host:port (e.g. 192.168.1.100:38291)."),
    code: str = typer.Argument(..., help="Pairing code."),
) -> None:
    """Pair Android device/TV over Wi-Fi (Android 11+ TLS)."""
    state = _state(ctx)
    runtime = _runtime(state)
    if ":" in endpoint:
        host, port_str = endpoint.split(":", 1)
        port = int(port_str)
    else:
        host, port = endpoint, 5555
    res = runtime.wireless_gateway.pair_device(host=host, pairing_port=port, pairing_code=code)
    _emit(state, res)


@device_app.command("connect")
def device_connect_cli(
    ctx: typer.Context,
    endpoint: str = typer.Argument(..., help="Host[:port] (e.g. 192.168.1.100)."),
) -> None:
    """Connect to Android device/TV over Wi-Fi (zero-binary)."""
    state = _state(ctx)
    runtime = _runtime(state)
    if ":" in endpoint:
        host, port_str = endpoint.split(":", 1)
        port = int(port_str)
    else:
        host, port = endpoint, 5555
    res = runtime.wireless_gateway.connect_device(host=host, port=port)
    _emit(state, res)


@device_app.command("status")
def device_status_cli(
    ctx: typer.Context,
    endpoint: str | None = typer.Argument(None, help="Optional device endpoint."),
) -> None:
    """Check wireless device connection, battery and port state."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.wireless_gateway.get_device_status(device_id=endpoint)
    _emit(state, res)


@device_app.command("push-apk")
def device_push_apk_cli(
    ctx: typer.Context,
    apk_path: str = typer.Argument(..., help="Path to APK binary file."),
    endpoint: str | None = typer.Option(None, "--device", "-d", help="Target device endpoint."),
) -> None:
    """Install APK over Wi-Fi using resilient chunking."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.wireless_gateway.push_apk_resilient(apk_path=apk_path, target_device=endpoint)
    _emit(state, res)


# TV Studio CLI
@tv_app.command("redesign")
def tv_redesign_cli(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="APK path or package name."),
    framework: str = typer.Option(
        "androidx.tv.material3", "--framework", "-f", help="Target TV UI framework."
    ),
) -> None:
    """Redesign Android TV app into Compose for TV M3."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.tv_studio.redesign_tv_ui(target_input=target, target_framework=framework)
    _emit(state, res)


@tv_app.command("diff")
def tv_diff_cli(
    ctx: typer.Context,
    before: str = typer.Argument(..., help="Original screenshot image path."),
    after: str = typer.Argument(..., help="Compose TV screenshot image path."),
    mask: bool = typer.Option(True, "--mask/--no-mask", help="Mask dynamic topbar."),
) -> None:
    """Compare original vs redesigned TV screens with masking."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.tv_studio.verify_screendiff(
        before_image=before, after_image=after, mask_topbar=mask
    )
    _emit(state, res)


@tv_app.command("bench")
def tv_bench_cli(
    ctx: typer.Context,
    package: str = typer.Option("com.tv.app", "--package", "-p", help="Target TV app package."),
) -> None:
    """Run wireless cold start and memory PSS benchmark."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.tv_studio.benchmark_performance(package_name=package)
    _emit(state, res)


# Rootless UAD-Backed Android Debloat CLI
@debloat_app.command("inspect")
def debloat_inspect_cli(
    ctx: typer.Context,
    device_id: str = typer.Option("", "--device", "-d", help="ADB device serial or IP:Port."),
    tier: str | None = typer.Option(
        None,
        "--tier",
        "-t",
        help="Filter by UAD safety tier (recommended, advanced, expert, unsafe, protected_system).",
    ),
) -> None:
    """Inspect Android packages and classify them with UAD safety tiers."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.debloat.inspect_packages(device_id=device_id, tier_filter=tier)
    _emit(state, res)


@debloat_app.command("apply")
def debloat_apply_cli(
    ctx: typer.Context,
    packages: list[str] = typer.Argument(
        ..., help="One or more package names to disable or restore."
    ),
    device_id: str = typer.Option("", "--device", "-d", help="ADB device serial or IP:Port."),
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes before applying."
    ),
    allow_expert: bool = typer.Option(
        False, "--allow-expert", help="Allow disabling 'expert' tier packages."
    ),
    restore: bool = typer.Option(
        False, "--restore", help="Re-enable packages instead of disabling."
    ),
) -> None:
    """Preview or apply rootless ADB debloating with automatic backup and undo scripts."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.debloat.apply_debloat(
        packages=packages,
        device_id=device_id,
        dry_run=dry_run,
        allow_expert=allow_expert,
        restore=restore,
    )
    _emit(state, res)


@debloat_app.command("restore")
def debloat_restore_cli(
    ctx: typer.Context,
    backup_file: str = typer.Argument(
        ..., help="Path to backup_*.json generated by debloat apply."
    ),
    device_id: str = typer.Option(
        "", "--device", "-d", help="Override target ADB device serial or IP:Port."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview restore commands without executing."
    ),
) -> None:
    """Restore previously debloated packages from a JSON backup file."""
    state = _state(ctx)
    runtime = _runtime(state)
    res = runtime.debloat.restore_from_backup(
        backup_file=backup_file,
        device_id=device_id,
        dry_run=dry_run,
    )
    _emit(state, res)


if __name__ == "__main__":  # pragma: no cover
    app()
