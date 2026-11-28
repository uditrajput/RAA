import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import typer

from raa.cli.main import app
from raa.runtime import build_registry
from raa.version import PROTOCOL_VERSION, __version__


def _introspect_cli() -> list[dict[str, str]]:
    cmds: list[dict[str, str]] = []

    def walk(cmd: typer.Typer, prefix: str = "raa") -> None:
        for c in cmd.registered_commands:
            name = c.name or (c.callback.__name__.replace("_", "-") if c.callback else "unknown")
            raw_help = c.help or (c.callback.__doc__ if c.callback else "") or ""
            help_line = " ".join(line.strip() for line in raw_help.strip().splitlines() if line.strip())
            cmds.append({"command": f"{prefix} {name}", "help": help_line})
        for g in cmd.registered_groups:
            grp_name = g.name or (g.typer_instance.info.name if g.typer_instance else "group")
            if g.typer_instance is not None:
                walk(g.typer_instance, f"{prefix} {grp_name}")

    walk(app)
    return cmds


dump_path = ROOT / "cli_dump.json"
if dump_path.exists():
    with dump_path.open(encoding="utf-8") as f:
        cmds = json.load(f)
else:
    cmds = _introspect_cli()

tool_count = build_registry().count()

# Group by category
groups: dict[str, list[dict[str, str]]] = {}
for c in cmds:
    parts = c["command"].split()
    grp = parts[1] if len(parts) > 2 else "global"
    groups.setdefault(grp, []).append(c)

out_path = ROOT / "docs" / "CLI_REFERENCE.md"
with out_path.open("w", encoding="utf-8") as out:
    out.write("# RAA (Reverse Android Anything) — Complete CLI Reference Guide\n\n")
    out.write(f"> **Platform:** Reverse Android Anything (RAA) v{__version__} Production  \n")
    out.write(f"> **Total Available CLI Commands:** {len(cmds)} commands  \n")
    out.write(
        f"> **Protocol Version:** {PROTOCOL_VERSION} | **Tool Equivalents:** {tool_count} Tools\n\n"
    )
    out.write(
        f"This document provides an exhaustive, production-grade reference for all {len(cmds)} command-line commands across all {len(groups)} sub-apps in RAA.\n\n"
    )
    out.write(
        "Every CLI command is backed by the exact same capability registry and runtime models that power RAA's MCP, REST, and Python SDK surfaces.\n\n"
    )
    out.write("## Table of Subcommand Groups\n\n")
    out.write("| Subcommand Group | Commands Count | Purpose & Domain |\n")
    out.write("|---|:---:|---|\n")

    group_descriptions = {
        "global": "Core CLI bootstrap, status, doctor, setup wizard, report, manifest & permissions",
        "project": "Workspace project creation, lifecycle and scope inspection",
        "artifact": "Artifact ingestion, cataloguing, and binary file enumeration",
        "tools": "Tool discovery, schema inspection, toolchain management, and raw profile-scoped invocation",
        "recipe": "Multi-stage automated analysis and workflow macro execution",
        "source": "DEX decompiler dispatch, class searching, and source recovery",
        "skill": "Antigravity Agent Skills catalogue, install and execution",
        "skills": "Self-evolving dynamic procedural skill saving, patching, and memory updates",
        "serve": "MCP stdio / SSE and REST API daemon servers",
        "framework": "Framework detection and application capability querying",
        "flutter": "Flutter asset, symbol, BoringSSL pinning, and engine inspection",
        "react-native": "React Native Hermes bytecode, bundle, and module inspection",
        "unity": "Unity il2cpp, metadata, and asset bundle extraction",
        "dotnet": "Xamarin / .NET MAUI DLL assembly inspection",
        "native": "ELF shared library symbol extraction and ARM64 disassembly",
        "ui": "View hierarchies, Jetpack Compose, Apple HIG, and shaders",
        "graph": "AAIR dependency and cross-reference call graph querying",
        "device": "ADB device management, USB hardware, and screen mirrors",
        "dynamic": "Frida hooks, memory dumps, network tracing, and dynamic fuzzer",
        "api": "API endpoint discovery, OpenAPI schemas, and traffic capturing",
        "unpack": "APK/AAB/XAPK/APKM unpacking, extraction, and rebuilding",
        "diff": "Binary, manifest, DEX, and permission differential comparison",
        "security": "MASTG audits, Play Protect pre-flight, and vulnerability triage",
        "test": "Automated UI and unit testing harness runs",
        "rebuild": "Patching, re-alignment, and v2/v3 APK signing block synthesis",
        "admin": "Engine catalogs, ZTNA gateways, quotas, and audit trails",
        "ai": "On-device AI model extraction (TFLite, ONNX, PyTorch Mobile)",
        "platform": "Multi-OS cross-platform target inspection (iOS, HarmonyOS, Linux)",
        "swarm": "Multi-agent swarm governance, token budgeting, and blackboard",
        "cognitive": "Dual-context adversarial audit and exploit payoff simulation",
        "binary": "Next-gen decompilers (RetDec LLVM, Kuna Rust), GDB/MI, and Apple Mach-O",
        "canvas": "Autonomous UI screen reconstruction, shaders, and Sodu CI/CD",
        "enterprise": "Enterprise MCP mesh, universal 7-CLI dispatcher, Nacos, WASM",
        "offensive": "Offensive security operations, Yaklang playbooks, and benchmarks",
        "channel": "Two-way mobile channels (Telegram, WhatsApp), cadence, and APK delivery",
        "mcp-mesh": "Dynamic external MCP server connectors, health probes, and vault injection",
        "tv": "Android TV / Google TV 10-foot Living Canvas UI redesign and wireless Perfetto benchmarks",
    }

    for grp in sorted(groups.keys()):
        desc = group_descriptions.get(grp, "Subsystem commands")
        out.write(f"| [`raa {grp}`](#{grp}-commands) | {len(groups[grp])} | {desc} |\n")
    out.write("\n---\n\n")

    for grp in sorted(groups.keys()):
        commands = groups[grp]
        out.write(f"## {grp.capitalize()} Commands\n\n")
        out.write(f"**Group:** `raa {grp}` | **Total Commands:** {len(commands)}\n\n")
        out.write("| Command | Description |\n")
        out.write("|---|---|\n")
        for c in commands:
            cmd_code = f"`{c['command']}`"
            help_text = c["help"].replace("|", "\\|")
            out.write(f"| {cmd_code} | {help_text} |\n")
        out.write("\n")

print(f"Generated docs/CLI_REFERENCE.md successfully ({len(cmds)} commands across {len(groups)} groups).")
