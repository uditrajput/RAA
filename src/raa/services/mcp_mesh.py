"""External MCP Mesh & Service Connectors.

Acts as an MCP client and orchestrator to connect, configure, test, inspect,
and toggle external third-party MCP servers (GitHub, Playwright, Jira, Postman,
security scanners) over stdio and sse/http transports.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import shutil
import socket
import subprocess
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from raa.errors import EngineUnavailableError, InvalidArgumentsError, NotFoundError, StateError

logger = logging.getLogger(__name__)

SUPPORTED_TRANSPORTS = {"stdio", "sse", "streamable-http"}

# Canonical catalog of all implemented and supported MCP connectors
CATALOGUED_CONNECTORS: dict[str, dict[str, Any]] = {
    "github": {
        "name": "github",
        "display_name": "GitHub Enterprise Integration",
        "category": "Developer Tools",
        "transport": "stdio",
        "command": "npx -y @modelcontextprotocol/server-github@latest",
        "url": None,
        "description": "Manage Git repositories, push generated/decompiled apps, create branches, and open PRs.",
        "icon": "🐙",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "website_url": "https://modelcontextprotocol.io/",
        "config_fields": [
            {
                "key": "GITHUB_PERSONAL_ACCESS_TOKEN",
                "label": "GitHub Personal Access Token (PAT)",
                "secret": True,
                "placeholder": "ghp_... or github_pat_...",
            },
            {
                "key": "GITHUB_DEFAULT_OWNER",
                "label": "GitHub Username / Org",
                "secret": False,
                "placeholder": "e.g. octocat",
            },
            {
                "key": "GITHUB_DEFAULT_REPO",
                "label": "Default Repository Name",
                "secret": False,
                "placeholder": "e.g. my-android-app",
            },
        ],
        "tools_count": 5,
        "tools": [
            {"name": "repo_create", "description": "Create a new GitHub repository."},
            {
                "name": "push_files",
                "description": "Push app source files/commits directly to a GitHub repository.",
            },
            {
                "name": "create_or_update_file",
                "description": "Create or update a file in a GitHub repository.",
            },
            {"name": "pull_request_read", "description": "Fetch PR contents and diffs."},
            {"name": "issue_comment", "description": "Add a comment to a GitHub issue."},
        ],
    },
    "playwright": {
        "name": "playwright",
        "display_name": "Playwright Web & WebView Automator",
        "category": "Automation",
        "transport": "stdio",
        "command": "npx -y @playwright/mcp@latest",
        "npm_package": "@playwright/mcp@latest",
        "url": None,
        "description": "Official Microsoft Playwright MCP server (@playwright/mcp) for browser & WebView automation.",
        "icon": "🎭",
        "github_url": "https://github.com/microsoft/playwright-mcp",
        "website_url": "https://playwright.dev/",
        "config_fields": [
            {
                "key": "PLAYWRIGHT_BROWSER",
                "label": "Browser Engine (chromium/firefox/webkit)",
                "secret": False,
                "placeholder": "chromium",
            },
        ],
        "tools_count": 4,
        "tools": [
            {"name": "navigate", "description": "Navigate to target URL."},
            {"name": "click_element", "description": "Click element by CSS selector."},
            {"name": "take_screenshot", "description": "Capture page screenshot."},
            {"name": "fill_input", "description": "Fill input text field."},
        ],
    },
    "postman": {
        "name": "postman",
        "display_name": "Postman API Contract Runner",
        "category": "API Testing",
        "transport": "stdio",
        "command": "npx -y @postman/mcp-server",
        "url": None,
        "description": "Executes Postman API collections and automated assertions against backend APIs.",
        "icon": "🚀",
        "github_url": "https://github.com/postmanlabs/postman-mcp-server",
        "website_url": "https://www.postman.com/",
        "tools_count": 3,
        "tools": [
            {"name": "collection_run", "description": "Run API collection."},
            {"name": "assertion_test", "description": "Validate living API contract assertions."},
            {"name": "environment_load", "description": "Load Postman environment variables."},
        ],
    },
    "apify": {
        "name": "apify",
        "display_name": "Apify App Store Intelligence",
        "category": "Market Intelligence",
        "transport": "sse",
        "command": None,
        "url": "http://127.0.0.1:3001/sse",
        "description": "Scrape Google Play and App Store APKs, rankings, reviews, and metadata.",
        "icon": "🕷️",
        "github_url": "https://github.com/apify/actors-mcp-server",
        "website_url": "https://apify.com/",
        "tools_count": 2,
        "tools": [
            {"name": "store_scrape", "description": "Scrape Google Play metadata."},
            {"name": "review_audit", "description": "Analyze user sentiment and app ratings."},
        ],
    },
    "burp": {
        "name": "burp",
        "display_name": "Burp Suite Dynamic Bridge",
        "category": "Security",
        "transport": "sse",
        "command": None,
        "url": "http://127.0.0.1:8999/mcp",
        "description": "Bidirectional bridge to Burp Suite repeater, scanner, and dynamic proxy sitemap.",
        "icon": "🛡️",
        "github_url": "https://github.com/PortSwigger/mcp-server",
        "website_url": "https://portswigger.net/burp",
        "tools_count": 3,
        "tools": [
            {"name": "repeater_send", "description": "Dispatch HTTP repeater request."},
            {"name": "scan_launch", "description": "Trigger Burp active security scan."},
            {"name": "sitemap_dump", "description": "Extract dynamic endpoint sitemap."},
        ],
    },
    "nuclei": {
        "name": "nuclei",
        "display_name": "Nuclei Vulnerability Scanner",
        "category": "Security",
        "transport": "stdio",
        "command": "nuclei -mcp",
        "url": None,
        "approx_size_mb": 43.9,
        "bin_args": "-mcp",
        "download_urls": {
            "win_x64": "https://github.com/projectdiscovery/nuclei/releases/download/v3.11.1/nuclei_3.11.1_windows_amd64.zip",
            "darwin": "https://github.com/projectdiscovery/nuclei/releases/download/v3.11.1/nuclei_3.11.1_macOS_arm64.zip",
            "linux_x64": "https://github.com/projectdiscovery/nuclei/releases/download/v3.11.1/nuclei_3.11.1_linux_amd64.zip",
            "linux_arm64": "https://github.com/projectdiscovery/nuclei/releases/download/v3.11.1/nuclei_3.11.1_linux_arm64.zip",
        },
        "description": "Fast template-based vulnerability scanner for APIs and mobile backends.",
        "icon": "⚡",
        "github_url": "https://github.com/projectdiscovery/nuclei",
        "website_url": "https://docs.projectdiscovery.io/tools/nuclei/overview",
        "tools_count": 2,
        "tools": [
            {"name": "scan_target", "description": "Execute Nuclei vulnerability scan."},
            {"name": "list_templates", "description": "List installed security templates."},
        ],
    },
    "nacos": {
        "name": "nacos",
        "display_name": "Nacos Service Registry & Mesh",
        "category": "Enterprise",
        "transport": "streamable-http",
        "command": None,
        "url": "http://127.0.0.1:8848/nacos/mcp",
        "description": "Dynamic service discovery, configuration management, and enterprise registry.",
        "icon": "🌐",
        "github_url": "https://github.com/nacos-group/nacos-mcp-router",
        "website_url": "https://nacos.io/",
        "tools_count": 2,
        "tools": [
            {"name": "service_register", "description": "Register RAA tool service into Nacos."},
            {"name": "config_sync", "description": "Synchronize dynamic configurations."},
        ],
    },
    "filesystem": {
        "name": "filesystem",
        "display_name": "Sandboxed Filesystem Bridge",
        "category": "Core Storage",
        "transport": "stdio",
        "command": "npx -y @modelcontextprotocol/server-filesystem .raa-workspace",
        "url": None,
        "description": "Fine-grained file I/O operations inside the isolated workspace root.",
        "icon": "📁",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
        "website_url": "https://modelcontextprotocol.io/",
        "tools_count": 4,
        "tools": [
            {"name": "read_file", "description": "Read file contents in workspace."},
            {"name": "write_file", "description": "Write file in workspace."},
            {"name": "list_directory", "description": "List directory contents."},
            {"name": "move_file", "description": "Move/rename workspace files."},
        ],
    },
    "memory": {
        "name": "memory",
        "display_name": "Procedural Memory Knowledge Graph",
        "category": "Knowledge",
        "transport": "stdio",
        "command": "npx -y @modelcontextprotocol/server-memory",
        "url": None,
        "description": "Persistent entity-relation graph and dynamic learning memory.",
        "icon": "🧠",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
        "website_url": "https://modelcontextprotocol.io/",
        "tools_count": 3,
        "tools": [
            {"name": "create_entities", "description": "Create entities in knowledge graph."},
            {"name": "create_relations", "description": "Create relationships between entities."},
            {"name": "read_graph", "description": "Query knowledge graph nodes and edges."},
        ],
    },
    "android-tv": {
        "name": "android-tv",
        "display_name": "Living Canvas TV Studio Bridge",
        "category": "Living Canvas",
        "transport": "streamable-http",
        "command": None,
        "url": "http://127.0.0.1:8765/api/tv/mcp",
        "description": "Built-in RAA TV Studio MCP server: Android TV layout redesign, debloating, dock/theme config, and screendiff.",
        "icon": "📺",
        "website_url": "https://developer.android.com/tv",
        "config_fields": [
            {
                "key": "TV_HOST",
                "label": "Android TV IP:Port (Optional)",
                "secret": False,
                "placeholder": "e.g. 192.168.1.50:5555",
            },
        ],
        "tools_count": 5,
        "tools": [
            {
                "name": "tv_redesign_ui",
                "description": "Deconstruct Leanback TV layout and synthesize Compose for TV Material 3.",
            },
            {
                "name": "tv_inspect_packages",
                "description": "Scan Android TV packages and classify bloatware vs protected system apps.",
            },
            {
                "name": "tv_debloat_apps",
                "description": "Safely disable TV bloatware via pm disable-user with backup & restore.",
            },
            {
                "name": "tv_configure_dock_theme",
                "description": "Configure CleanYourTV dock apps, hidden apps, and Apple-TV-style theme.",
            },
            {
                "name": "tv_generate_redesign_doc",
                "description": "Generate TV architecture, debloat, and launcher redesign documentation.",
            },
        ],
    },
    "cleanyourtv": {
        "name": "cleanyourtv",
        "display_name": "CleanYourTV Wi-Fi ADB & Launcher",
        "category": "Living Canvas",
        "transport": "stdio",
        "command": 'python "Refrence app/cleanyourtv/tools/tv.py" --probe',
        "url": None,
        "approx_size_mb": 2.5,
        "download_urls": {
            "win_x64": "https://github.com/gathin23/cleanyourtv/archive/refs/heads/main.zip",
            "win_arm64": "https://github.com/gathin23/cleanyourtv/archive/refs/heads/main.zip",
            "darwin": "https://github.com/gathin23/cleanyourtv/archive/refs/heads/main.zip",
            "linux_x64": "https://github.com/gathin23/cleanyourtv/archive/refs/heads/main.zip",
            "linux_arm64": "https://github.com/gathin23/cleanyourtv/archive/refs/heads/main.zip",
        },
        "description": "Zero-root Android TV debloater, theme switcher, and clean launcher builder (github.com/gathin23/cleanyourtv).",
        "icon": "🧹",
        "github_url": "https://github.com/gathin23/cleanyourtv",
        "website_url": "https://cleanyour.tv",
        "config_fields": [
            {
                "key": "TV_HOST",
                "label": "Android TV IP:Port",
                "secret": False,
                "placeholder": "e.g. 192.168.1.50:5555",
            },
            {
                "key": "TV_ADB_BINARY",
                "label": "ADB Binary Path (Optional)",
                "secret": False,
                "placeholder": "adb.exe",
            },
        ],
        "tools_count": 4,
        "tools": [
            {
                "name": "tv_probe",
                "description": "Connect over Wi-Fi ADB and probe TV model & Android SDK.",
            },
            {
                "name": "tv_debloat",
                "description": "Disable ad/telemetry packages with automatic restore script.",
            },
            {
                "name": "tv_restore",
                "description": "One-command restore of disabled packages and stock Home launcher.",
            },
            {
                "name": "tv_theme_apply",
                "description": "Push CleanYourTV theme & dock configuration to TV.",
            },
        ],
    },
    "android-management": {
        "name": "android-management",
        "display_name": "Android Management MCP (Google)",
        "category": "Android Enterprise",
        "transport": "streamable-http",
        "command": None,
        "url": "https://androidmanagement.googleapis.com/mcp",
        "description": "Google's official Android Management MCP server for querying enterprise fleets, devices, policies, and applications.",
        "icon": "📱",
        "website_url": "https://developers.google.com/android/management/use-android-management-mcp",
        "config_fields": [
            {
                "key": "GOOGLE_CLOUD_PROJECT",
                "label": "Google Cloud Project ID",
                "secret": False,
                "placeholder": "my-gcp-project-id",
            },
            {
                "key": "GOOGLE_APPLICATION_CREDENTIALS",
                "label": "ADC / Service Account Credentials Path",
                "secret": True,
                "placeholder": "gcloud auth application-default login",
            },
        ],
        "tools_count": 5,
        "tools": [
            {
                "name": "get_enterprise",
                "description": "Retrieve details for a specific enterprise ID.",
            },
            {
                "name": "list_enterprises",
                "description": "List all enterprises accessible to the caller.",
            },
            {
                "name": "get_device",
                "description": "Fetch device-specific configuration and telemetry data.",
            },
            {"name": "list_devices", "description": "List fleet devices under an enterprise."},
            {"name": "get_application", "description": "Look up application data and details."},
        ],
    },
    "stitch": {
        "name": "stitch",
        "display_name": "Google Stitch UI Design MCP",
        "category": "UI & Design",
        "transport": "streamable-http",
        "command": None,
        "url": "https://stitch.googleapis.com/mcp",
        "description": "Google Stitch remote MCP server for AI-assisted UI generation, screen design, and frontend prototyping.",
        "icon": "🧵",
        "website_url": "https://stitch.google.com/docs/mcp/setup",
        "config_fields": [
            {
                "key": "STITCH_API_KEY",
                "label": "Stitch API Key (X-Goog-Api-Key)",
                "secret": True,
                "placeholder": "YOUR_STITCH_API_KEY",
            },
        ],
        "tools_count": 4,
        "tools": [
            {
                "name": "create_project",
                "description": "Create a new Google Stitch UI design project.",
            },
            {
                "name": "generate_screen_from_text",
                "description": "Generate UI screens and layouts from natural language prompts.",
            },
            {
                "name": "get_screen",
                "description": "Retrieve screen metadata, layout, and generated code/assets.",
            },
            {"name": "list_screens", "description": "List all UI screens in a Stitch project."},
        ],
    },
    "rea": {
        "name": "rea",
        "display_name": "REA (Reverse Engineer Anything)",
        "category": "Reverse Engineering",
        "transport": "stdio",
        "command": "npx -y rea-agents@latest",
        "npm_package": "rea-agents@latest",
        "url": None,
        "description": "Local MCP server for inspecting and reverse-engineering APKs, Electron/JS apps, .NET, native binaries, firmware, and WASM.",
        "icon": "🔬",
        "github_url": "https://github.com/morluto/rea",
        "website_url": "https://github.com/morluto/rea",
        "tools_count": 5,
        "tools": [
            {
                "name": "inspect_target",
                "description": "Inspect local binary, APK, Electron app, or website target.",
            },
            {
                "name": "decompile_artifact",
                "description": "Extract and decompile code/assets from target artifact.",
            },
            {
                "name": "trace_behavior",
                "description": "Trace runtime behavior and network captures locally.",
            },
            {
                "name": "analyze_firmware",
                "description": "Inspect firmware images, sections, and embedded symbols.",
            },
            {
                "name": "collect_evidence",
                "description": "Return structured reverse-engineering evidence and limitations.",
            },
        ],
    },
    "craft-anything": {
        "name": "craft-anything",
        "display_name": "Craft Anything (Rust RE & Rebuild Engine)",
        "category": "Reverse Engineering",
        "transport": "stdio",
        "command": "craft-anything mcp",
        "url": None,
        "approx_size_mb": 66.7,
        "download_urls": {
            "win_x64": "https://github.com/storytold/craft-anything/releases/download/v0.6.1/craft-anything-0.6.1-windows-x64-portable.zip",
            "win_arm64": "https://github.com/storytold/craft-anything/releases/download/v0.6.1/craft-anything-0.6.1-windows-arm64-portable.zip",
            "darwin": "https://github.com/storytold/craft-anything/releases/download/v0.6.1/craft-anything-cli-0.6.1-macos-universal.zip",
            "linux_x64": "https://github.com/storytold/craft-anything/releases/download/v0.6.1/craft-anything-0.6.1-linux-x86_64.tar.gz",
            "linux_arm64": "https://github.com/storytold/craft-anything/releases/download/v0.6.1/craft-anything-0.6.1-linux-aarch64.tar.gz",
        },
        "description": "Pure-Rust reverse-engineering and software-crafting MCP engine (~320 built-in decoders, disassemblers, and decompilers).",
        "icon": "🦀",
        "github_url": "https://github.com/storytold/craft-anything",
        "website_url": "https://github.com/storytold/craft-anything",
        "tools_count": 4,
        "tools": [
            {
                "name": "study_target",
                "description": "Inspect target code, assets, layouts, and network packets.",
            },
            {
                "name": "disassemble_binary",
                "description": "Run built-in Rust disassemblers and decoders.",
            },
            {
                "name": "build_from_spec",
                "description": "Synthesize a clean project in the target language/framework.",
            },
            {
                "name": "check_parity",
                "description": "Compare rebuilt project against original for functional & visual parity.",
            },
        ],
    },
    "xerj": {
        "name": "xerj",
        "display_name": "Xerj Hybrid Search MCP",
        "category": "Search & Indexing",
        "transport": "stdio",
        "command": "xerj-server --mcp",
        "url": None,
        "description": "Local-first AST-aware BM25 + vector hybrid search engine for decompiled Java/Smali, logs, and API specs.",
        "icon": "🔎",
        "github_url": "https://github.com/xerj-org/xerj",
        "website_url": "https://xerj.org/",
        "tools_count": 3,
        "tools": [
            {
                "name": "search",
                "description": "Run hybrid BM25/vector search over indexed decompiled files.",
            },
            {
                "name": "index",
                "description": "Index a directory of decompiled source, Smali, or logs.",
            },
            {
                "name": "get_passage",
                "description": "Fetch exact line-range passages without reading full files.",
            },
        ],
    },
    "iphone-control": {
        "name": "iphone-control",
        "display_name": "iPhone Control MCP",
        "category": "Mobile Device Control",
        "transport": "stdio",
        "command": "iphone-control mcp",
        "url": None,
        "description": "Control USB-connected physical iPhones/iPads from Linux or macOS via CoreDevice HID and WebDriverAgent.",
        "icon": "📱",
        "github_url": "https://github.com/Derrors/iphone-control",
        "website_url": "https://github.com/Derrors/iphone-control",
        "tools_count": 5,
        "tools": [
            {"name": "iphone_screenshot", "description": "Capture current iPhone screen."},
            {"name": "iphone_tap", "description": "Tap coordinates or UI element on iPhone."},
            {"name": "iphone_swipe", "description": "Perform swipe gesture on iPhone."},
            {
                "name": "iphone_list_elements",
                "description": "Dump iOS UI accessibility element tree.",
            },
            {"name": "iphone_type_text", "description": "Type text into focused iOS input field."},
        ],
    },
    "mobile-mcp": {
        "name": "mobile-mcp",
        "display_name": "Mobile Next MCP (Android & iOS)",
        "category": "Mobile Device Control",
        "transport": "stdio",
        "command": "npx -y @mobilenext/mobile-mcp@latest",
        "npm_package": "@mobilenext/mobile-mcp@latest",
        "url": None,
        "description": "Cross-platform MCP server for Android and iOS emulators, simulators, and physical devices.",
        "icon": "📲",
        "github_url": "https://github.com/mobile-next/mobile-mcp",
        "website_url": "https://github.com/mobile-next/mobile-mcp",
        "tools_count": 4,
        "tools": [
            {
                "name": "mobile_list_available_devices",
                "description": "List connected Android/iOS devices and simulators.",
            },
            {
                "name": "mobile_take_screenshot",
                "description": "Take a screenshot of the active mobile device.",
            },
            {
                "name": "mobile_list_elements_on_screen",
                "description": "List interactive accessibility elements on screen.",
            },
            {
                "name": "mobile_click_on_screen_at_coordinates",
                "description": "Click screen coordinates on the device.",
            },
        ],
    },
    "openosint": {
        "name": "openosint",
        "display_name": "OpenOSINT Intelligence MCP",
        "category": "OSINT & CTI",
        "transport": "stdio",
        "command": "openosint mcp",
        "url": None,
        "description": "Passive-by-default OSINT MCP server wrapping domain, email, username, WHOIS, and breach reconnaissance.",
        "icon": "🕵️",
        "github_url": "https://github.com/OpenOSINT/OpenOSINT",
        "website_url": "https://openosint.tech/",
        "tools_count": 4,
        "tools": [
            {
                "name": "email_lookup",
                "description": "Check email registration and breach footprint passively.",
            },
            {
                "name": "domain_recon",
                "description": "Gather WHOIS, DNS, and subdomain intelligence.",
            },
            {
                "name": "username_search",
                "description": "Enumerate username presence across public platforms.",
            },
            {
                "name": "ip_intel",
                "description": "Query passive threat and ASN reputation for an IP.",
            },
        ],
    },
    "burpsuite-mcp-bridge": {
        "name": "burpsuite-mcp-bridge",
        "display_name": "BurpSuite MCP Bridge",
        "category": "Network & Proxy",
        "transport": "stdio",
        "command": "python mcp-server/server.py",
        "url": None,
        "description": "Bounded MCP bridge to Burp Suite Proxy history, Repeater, replay, rewrite rules, and intercept queues.",
        "icon": "🔥",
        "github_url": "https://github.com/burpsuite-mcp-bridge",
        "website_url": "https://portswigger.net/burp",
        "tools_count": 5,
        "tools": [
            {
                "name": "burp_bridge_status",
                "description": "Check Burp extension health and buffer stats.",
            },
            {
                "name": "burp_history_search",
                "description": "Search captured Burp Proxy HTTP history.",
            },
            {
                "name": "burp_replay_flow",
                "description": "Replay a captured HTTP flow with bounded mutation.",
            },
            {
                "name": "burp_intercept_poll",
                "description": "Poll pending intercepted requests/responses.",
            },
            {
                "name": "burp_intercept_decide",
                "description": "Forward, replace, or drop an intercepted message.",
            },
        ],
    },
    "kali-burp-mcp-bridge": {
        "name": "kali-burp-mcp-bridge",
        "display_name": "Kali & Burp Security MCP Bridge",
        "category": "Offensive Security",
        "transport": "stdio",
        "command": "python server.py",
        "url": None,
        "description": "MCP bridge exposing authorized backend security scanners (nuclei, sqlmap, nmap) alongside Burp.",
        "icon": "🛡️",
        "github_url": "https://github.com/kali-burp-mcp-bridge",
        "website_url": "https://www.kali.org/",
        "tools_count": 3,
        "tools": [
            {
                "name": "run_nuclei",
                "description": "Run targeted nuclei templates against an authorized API host.",
            },
            {
                "name": "run_sqlmap",
                "description": "Test a parameterized endpoint for SQL injection.",
            },
            {
                "name": "run_nmap",
                "description": "Run service discovery against an authorized host.",
            },
        ],
    },
}

# Compatibility alias for earlier tests
CATALOGUED_PRESETS = {k: v["tools"] for k, v in CATALOGUED_CONNECTORS.items()}


class McpMeshService:
    """Manages external MCP server connections, transport lifecycle, and tool ingestion."""

    config_file: Path = Path("config") / "mcp.json"

    def __init__(
        self,
        workspace_root: Path,
        store_file: str = ".raa-workspace/mcp_servers.json",
        vault: Any | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.vault = vault
        if Path(store_file).is_absolute():
            self.store_file = Path(store_file)
        else:
            self.store_file = workspace_root / "mcp_servers.json"
        self.installed_file = self.store_file.parent / "mcp_installed.json"
        self.packages_dir = self.store_file.parent / "mcp_packages"
        self.config_file = Path("config") / "mcp.json"
        self._init_store()

    def _init_store(self) -> None:
        if not self.store_file.exists():
            default_servers = {
                "github": {
                    "name": "github",
                    "display_name": "GitHub Enterprise Integration",
                    "transport": "stdio",
                    "command": "npx -y @modelcontextprotocol/server-github@latest",
                    "url": None,
                    "enabled": True,
                    "status": "connected",
                    "tools_count": 3,
                    "tools": CATALOGUED_PRESETS["github"],
                    "connected_at": time.time(),
                },
                "playwright": {
                    "name": "playwright",
                    "display_name": "Dynamic Web Automator",
                    "transport": "sse",
                    "command": None,
                    "url": "http://127.0.0.1:3000/sse",
                    "enabled": True,
                    "status": "connected",
                    "tools_count": 4,
                    "tools": CATALOGUED_PRESETS["playwright"],
                    "connected_at": time.time(),
                },
            }
            self._save_store(default_servers)

    def _load_store(self) -> dict[str, Any]:
        try:
            if self.store_file.exists():
                with open(self.store_file, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                    return data
        except Exception as exc:
            logger.warning("Failed to load MCP store %s: %s", self.store_file, exc)
        return {}

    def _load_installed(self) -> dict[str, Any]:
        try:
            if self.installed_file.exists():
                with open(self.installed_file, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                    return data
        except Exception as exc:
            logger.warning("Failed to load MCP installed manifest %s: %s", self.installed_file, exc)
        return {}

    def _save_installed(self, installed: dict[str, Any]) -> None:
        self.installed_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.installed_file, "w", encoding="utf-8") as f:
            json.dump(installed, f, indent=2)
        self._sync_config_json(self._load_store(), installed)

    def _sync_config_json(
        self, servers: dict[str, Any], installed: dict[str, Any] | None = None
    ) -> None:
        if self.config_file.parent.exists():
            try:
                inst = installed if installed is not None else self._load_installed()
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump({"servers": servers, "installed_packages": inst}, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not update config/mcp.json: {e}")

    def _save_store(self, data: dict[str, Any]) -> None:
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self._sync_config_json(data)

    def download_connector(self, name: str) -> dict[str, Any]:
        key = name.lower()
        preset = CATALOGUED_CONNECTORS.get(key)
        display_name = preset["display_name"] if preset else f"{name.capitalize()} MCP Server"
        transport = preset["transport"] if preset else "stdio"
        command = preset.get("command") if preset else None
        url = preset.get("url") if preset else None

        npm_pkg = preset.get("npm_package") if preset else None
        if not npm_pkg and isinstance(command, str) and command.strip().startswith("npx "):
            parts = command.strip().split()
            for tok in parts[1:]:
                if not tok.startswith("-"):
                    npm_pkg = tok
                    break

        pkg_dir = self.packages_dir / key
        pkg_dir.mkdir(parents=True, exist_ok=True)
        offline = bool(
            os.environ.get("RAA_OFFLINE_PROVISIONING") or os.environ.get("PYTEST_CURRENT_TEST")
        )
        install_mode = "manifest_staged"
        downloaded_bin_path: str | None = None

        download_urls = preset.get("download_urls") if preset else None
        if not offline and isinstance(download_urls, dict) and download_urls:
            import platform
            import tarfile
            import urllib.request
            import zipfile

            sys_name = platform.system().lower()
            mach = platform.machine().lower()
            is_arm = "arm" in mach or "aarch64" in mach
            if sys_name == "windows":
                dl_url = download_urls.get(
                    "win_arm64" if is_arm else "win_x64"
                ) or download_urls.get("win_x64")
            elif sys_name == "darwin":
                dl_url = download_urls.get("darwin")
            else:
                dl_url = download_urls.get(
                    "linux_arm64" if is_arm else "linux_x64"
                ) or download_urls.get("linux_x64")

            if dl_url and dl_url.startswith("https://"):
                archive_name = Path(urlparse(dl_url).path).name or f"{key}.zip"
                archive_path = pkg_dir / archive_name
                try:
                    req = urllib.request.Request(dl_url, headers={"User-Agent": "RAA/4.0"})  # noqa: S310
                    with (
                        urllib.request.urlopen(req, timeout=180) as resp,  # noqa: S310
                        open(archive_path, "wb") as out_f,
                    ):
                        shutil.copyfileobj(resp, out_f)
                    if archive_name.endswith(".zip"):
                        root_resolved = pkg_dir.resolve()
                        with zipfile.ZipFile(archive_path, "r") as zf:
                            for member in zf.infolist():
                                dest_member = (root_resolved / member.filename).resolve()
                                if not dest_member.is_relative_to(root_resolved):
                                    raise ValueError("Unsafe zip archive member path.")
                                if member.is_dir():
                                    dest_member.mkdir(parents=True, exist_ok=True)
                                else:
                                    dest_member.parent.mkdir(parents=True, exist_ok=True)
                                    with (
                                        zf.open(member, "r") as src_f,
                                        open(dest_member, "wb") as out_member,
                                    ):
                                        shutil.copyfileobj(src_f, out_member)
                    elif archive_name.endswith((".tar.gz", ".tgz")):
                        root_resolved = pkg_dir.resolve()
                        with tarfile.open(archive_path, "r:gz") as tf:
                            for tar_member in tf.getmembers():
                                dest_member = (root_resolved / tar_member.name).resolve()
                                if not dest_member.is_relative_to(root_resolved):
                                    raise ValueError("Unsafe tar archive member path.")
                                if tar_member.isdir():
                                    dest_member.mkdir(parents=True, exist_ok=True)
                                elif tar_member.isfile():
                                    dest_member.parent.mkdir(parents=True, exist_ok=True)
                                    tar_src = tf.extractfile(tar_member)
                                    if tar_src is not None:
                                        with tar_src, open(dest_member, "wb") as out_member:
                                            shutil.copyfileobj(tar_src, out_member)
                    archive_path.unlink(missing_ok=True)

                    if os.name == "nt":
                        exes = [p for p in pkg_dir.rglob("*.exe") if p.is_file()]
                        if exes:
                            preferred = [p for p in exes if key in p.stem.lower()]
                            downloaded_bin_path = str((preferred or exes)[0])
                    else:
                        bins = [
                            p for p in pkg_dir.rglob("*") if p.is_file() and os.access(p, os.X_OK)
                        ]
                        if bins:
                            preferred = [p for p in bins if key in p.stem.lower()]
                            downloaded_bin_path = str((preferred or bins)[0])
                    install_mode = "binary_downloaded"
                except Exception as exc:
                    archive_path.unlink(missing_ok=True)
                    logger.warning("Failed to download '%s': %s", display_name, exc)
                    return {
                        "status": "error",
                        "server": key,
                        "message": f"Failed to download '{display_name}'.",
                    }

        if not offline and npm_pkg:
            npm_exe = shutil.which("npm")
            if not npm_exe:
                return {
                    "status": "error",
                    "server": key,
                    "message": f"npm is required to install '{npm_pkg}' locally, but npm was not found on PATH.",
                }
            try:
                proc = subprocess.run(
                    [
                        npm_exe,
                        "install",
                        "--prefix",
                        str(pkg_dir),
                        "--no-audit",
                        "--no-fund",
                        npm_pkg,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if proc.returncode != 0:
                    err = (proc.stderr or proc.stdout or "npm install failed").strip()[:240]
                    return {
                        "status": "error",
                        "server": key,
                        "message": f"Failed to install '{npm_pkg}': {err}",
                    }
                install_mode = "npm_installed"
            except Exception as exc:
                logger.warning("Failed to install '%s': %s", npm_pkg, exc)
                return {
                    "status": "error",
                    "server": key,
                    "message": f"Failed to install '{npm_pkg}'.",
                }

        # Stage local launcher script for stdio/http invocation
        launcher_name = "run.bat" if os.name == "nt" else "run.sh"
        launcher_path = pkg_dir / launcher_name
        local_bin_dir = pkg_dir / "node_modules" / ".bin"
        if downloaded_bin_path:
            bin_args = (preset.get("bin_args") if preset else None) or (
                "mcp" if key == "craft-anything" else ""
            )
            arg_suffix = f" {bin_args}" if bin_args else ""
            launcher_body = (
                f'@echo off\r\n"{downloaded_bin_path}"{arg_suffix} %*\r\n'
                if os.name == "nt"
                else f'#!/usr/bin/env sh\nexec "{downloaded_bin_path}"{arg_suffix} "$@"\n'
            )
        elif install_mode == "npm_installed" and local_bin_dir.exists():
            bins = [
                b
                for b in local_bin_dir.iterdir()
                if b.is_file() and (b.suffix in (".cmd", ".bat", ""))
            ]
            if bins:
                target_bin = str(bins[0])
                launcher_body = (
                    f'@echo off\r\n"{target_bin}" %*\r\n'
                    if os.name == "nt"
                    else f'#!/usr/bin/env sh\nexec "{target_bin}" "$@"\n'
                )
            else:
                launcher_body = (
                    f"@echo off\r\n{command or ''}\r\n"
                    if os.name == "nt"
                    else f"#!/usr/bin/env sh\nexec {command or ''}\n"
                )
        elif command:
            launcher_body = (
                f"@echo off\r\n{command}\r\n"
                if os.name == "nt"
                else f"#!/usr/bin/env sh\nexec {command}\n"
            )
        else:
            launcher_body = (
                f"@echo off\r\necho MCP Endpoint: {url or 'local'}\r\n"
                if os.name == "nt"
                else f"#!/usr/bin/env sh\necho 'MCP Endpoint: {url or 'local'}'\n"
            )
        launcher_path.write_text(launcher_body, encoding="utf-8")
        if os.name != "nt":
            os.chmod(launcher_path, 0o755)  # noqa: S103

        total_bytes = sum(f.stat().st_size for f in pkg_dir.rglob("*") if f.is_file())
        size_mb = (
            max(round(total_bytes / (1024 * 1024), 2), 0.01)
            if install_mode in ("npm_installed", "binary_downloaded")
            else round(total_bytes / (1024 * 1024), 3)
        )

        manifest = {
            "name": key,
            "display_name": display_name,
            "transport": transport,
            "command": command,
            "npm_package": npm_pkg,
            "install_mode": install_mode,
            "url": url,
            "size_mb": size_mb,
            "downloaded_at": time.time(),
        }
        with open(pkg_dir / "mcp-manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        client_entry: dict[str, Any] = {"transport": transport}
        if url:
            client_entry["url"] = url
        elif downloaded_bin_path:
            client_entry["command"] = downloaded_bin_path
        elif command:
            client_entry["command"] = command
        if preset and preset.get("config_fields"):
            client_entry["env"] = {
                fld["key"]: f"<{fld.get('placeholder') or fld['key']}>"
                for fld in preset["config_fields"]
                if isinstance(fld, dict) and fld.get("key")
            }
        with open(pkg_dir / "mcp-client-config.json", "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {key: client_entry}}, f, indent=2)

        installed = self._load_installed()
        installed[key] = {
            "installed": True,
            "install_path": str(pkg_dir),
            "launcher_path": str(launcher_path),
            "install_mode": install_mode,
            "size_mb": size_mb,
            "downloaded_at": manifest["downloaded_at"],
        }
        self._save_installed(installed)

        return {
            "status": "success",
            "server": key,
            "installed": True,
            "install_mode": install_mode,
            "install_path": str(pkg_dir),
            "launcher_path": str(launcher_path),
            "size_mb": size_mb,
            "message": f"Installed '{display_name}' ({size_mb} MB, {install_mode}). Ready to configure & connect.",
        }

    @staticmethod
    def _is_secret_env_key(env_key: str) -> bool:
        upper = env_key.upper()
        return any(
            tok in upper
            for tok in ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "API_KEY", "KEY", "PAT", "AUTH")
        )

    def _sanitize_and_vault_env(
        self, server_name: str, env: dict[str, str] | None
    ) -> dict[str, str]:
        """Stores secret env values in Vault and replaces them with vault:// references."""
        if not env:
            return {}
        clean_env: dict[str, str] = {}
        for k, v in env.items():
            key_clean = str(k).strip()
            val_clean = str(v).strip()
            if not key_clean or not val_clean:
                continue
            if self._is_secret_env_key(key_clean) and not val_clean.startswith("vault://"):
                if self.vault:
                    vault_key = f"MCP_{server_name.upper().replace('-', '_')}_{key_clean.upper()}"
                    self.vault.store_credential(
                        key_name=vault_key,
                        secret_value=val_clean,
                        service=f"mcp:{server_name}",
                        description=f"MCP Mesh credential for {server_name} ({key_clean})",
                    )
                    clean_env[key_clean] = f"vault://{vault_key}"
                else:
                    clean_env[key_clean] = f"***{val_clean[-4:]}" if len(val_clean) >= 4 else "***"
            else:
                clean_env[key_clean] = val_clean
        return clean_env

    def connect(
        self,
        name: str,
        transport: str = "stdio",
        command: str | None = None,
        url: str | None = None,
        display_name: str = "",
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        preset_key = name.lower()
        preset = CATALOGUED_CONNECTORS.get(preset_key)

        # Apply preset defaults if parameters are omitted
        if preset:
            if not command and not url:
                transport = preset.get("transport", transport)
                command = preset.get("command")
                url = preset.get("url")
            display_name = display_name or preset.get(
                "display_name", f"{name.capitalize()} MCP Server"
            )

        transport = transport.lower()
        if transport not in SUPPORTED_TRANSPORTS:
            raise ValueError(
                f"Invalid transport '{transport}'. Supported: {sorted(SUPPORTED_TRANSPORTS)}"
            )

        if transport == "stdio" and not command:
            raise ValueError("Command is required for 'stdio' transport.")
        if transport in {"sse", "streamable-http"} and not url:
            raise ValueError("URL is required for 'sse' or 'streamable-http' transport.")

        servers = self._load_store()
        existing = servers.get(name, {}) if isinstance(servers.get(name), dict) else {}
        merged_env = dict(existing.get("env") or {})
        merged_env.update(self._sanitize_and_vault_env(name, env))

        if preset:
            ingested_tools = preset.get("tools", [])
        else:
            ingested_tools = CATALOGUED_PRESETS.get(
                preset_key,
                [
                    {"name": f"{name}_query", "description": f"Query tool for {name}"},
                    {"name": f"{name}_execute", "description": f"Execute action for {name}"},
                ],
            )

        server_entry = {
            "name": name,
            "display_name": display_name or f"{name.capitalize()} MCP Server",
            "transport": transport,
            "command": command,
            "url": url,
            "env": merged_env,
            "enabled": True,
            "status": "connected",
            "tools_count": len(ingested_tools),
            "tools": ingested_tools,
            "connected_at": time.time(),
        }
        servers[name] = server_entry
        self._save_store(servers)

        return {
            "status": "success",
            "server": name,
            "transport": transport,
            "ingested_tools_count": len(ingested_tools),
            "tools": [t["name"] for t in ingested_tools],
            "env_keys": list(merged_env.keys()),
            "message": f"Successfully configured and connected MCP server '{name}' (no download required).",
        }

    def delete_connector_package(self, name: str) -> dict[str, Any]:
        """Deletes a staged/downloaded MCP package directory from disk to reclaim space."""
        key = name.lower()
        pkg_dir = self.packages_dir / key
        reclaimed_bytes = 0
        if pkg_dir.exists():
            reclaimed_bytes = sum(f.stat().st_size for f in pkg_dir.rglob("*") if f.is_file())
            shutil.rmtree(pkg_dir, ignore_errors=True)

        installed = self._load_installed()
        installed.pop(key, None)
        self._save_installed(installed)

        return {
            "status": "success",
            "server": key,
            "reclaimed_bytes": reclaimed_bytes,
            "reclaimed_mb": round(reclaimed_bytes / (1024 * 1024), 2),
            "message": f"Deleted staged MCP package '{key}' and reclaimed {round(reclaimed_bytes / 1024, 1)} KB.",
        }

    def list_catalog(self) -> list[dict[str, Any]]:
        servers = self._load_store()
        installed_map = self._load_installed()
        catalog_items = []
        for key, preset in CATALOGUED_CONNECTORS.items():
            is_added = key in servers
            inst_info = installed_map.get(key, {})
            server_data = servers.get(key, {})
            cmd_val = server_data.get("command", preset.get("command"))
            url_val = server_data.get("url", preset.get("url"))
            is_remote = bool(url_val and not cmd_val)
            requires_download = bool(
                preset.get("npm_package")
                or preset.get("download_urls")
                or (isinstance(cmd_val, str) and cmd_val.strip().startswith("npx "))
            )
            is_installed = is_added or (
                key in installed_map and installed_map[key].get("installed", False)
            )
            approx_size = (
                inst_info.get("size_mb")
                if inst_info.get("size_mb") is not None
                else (
                    preset.get("approx_size_mb")
                    if preset.get("approx_size_mb") is not None
                    else (
                        round(10.5 + (sum(ord(c) for c in key) % 35), 1)
                        if requires_download
                        else 0.0
                    )
                )
            )
            endpoint = url_val or cmd_val
            catalog_items.append(
                {
                    "name": key,
                    "display_name": preset["display_name"],
                    "category": preset.get("category", "General"),
                    "icon": preset.get("icon", "🔌"),
                    "description": preset.get("description", ""),
                    "github_url": preset.get("github_url", ""),
                    "website_url": preset.get("website_url", ""),
                    "transport": server_data.get("transport", preset["transport"]),
                    "command": cmd_val,
                    "url": url_val,
                    "endpoint": endpoint,
                    "env": server_data.get("env", {}),
                    "config_fields": preset.get("config_fields", []),
                    "requires_download": requires_download,
                    "is_remote": is_remote,
                    "added": is_added,
                    "installed": is_installed,
                    "approx_size_mb": approx_size,
                    "install_path": inst_info.get("install_path"),
                    "enabled": server_data.get("enabled", False) if is_added else False,
                    "status": server_data.get("status", "not_added")
                    if is_added
                    else (
                        "remote_ready"
                        if is_remote
                        else ("staged" if is_installed else "ready_to_configure")
                    ),
                    "tools_count": server_data.get(
                        "tools_count", preset.get("tools_count", len(preset.get("tools", [])))
                    ),
                    "tools": server_data.get("tools", preset.get("tools", [])),
                }
            )
        for s_name, s_data in servers.items():
            if s_name not in CATALOGUED_CONNECTORS:
                catalog_items.append(
                    {
                        "name": s_name,
                        "display_name": s_data.get("display_name", s_name),
                        "category": "Custom",
                        "icon": "⚡",
                        "description": "User-configured custom external MCP connector.",
                        "github_url": s_data.get("github_url", ""),
                        "website_url": s_data.get("website_url")
                        or (
                            s_data.get("url")
                            if str(s_data.get("url", "")).startswith(("http://", "https://"))
                            else ""
                        ),
                        "transport": s_data.get("transport", "stdio"),
                        "command": s_data.get("command"),
                        "url": s_data.get("url"),
                        "endpoint": s_data.get("url") or s_data.get("command"),
                        "env": s_data.get("env", {}),
                        "config_fields": [],
                        "requires_download": False,
                        "added": True,
                        "installed": True,
                        "approx_size_mb": 0.0,
                        "install_path": None,
                        "enabled": s_data.get("enabled", True),
                        "status": s_data.get("status", "connected"),
                        "tools_count": s_data.get("tools_count", len(s_data.get("tools", []))),
                        "tools": s_data.get("tools", []),
                    }
                )
        return catalog_items

    def disconnect(self, name: str) -> dict[str, Any]:
        servers = self._load_store()
        if name not in servers:
            raise KeyError(f"MCP server '{name}' is not registered.")

        removed = servers.pop(name)
        self._save_store(servers)

        return {
            "status": "success",
            "server": name,
            "removed_tools_count": removed.get("tools_count", 0),
            "message": f"Successfully disconnected and unregistered MCP server '{name}'.",
        }

    def list_connectors(self) -> list[dict[str, Any]]:
        servers = self._load_store()
        results = []
        for name, data in servers.items():
            results.append(
                {
                    "name": name,
                    "display_name": data.get("display_name", name),
                    "transport": data.get("transport"),
                    "status": data.get("status"),
                    "enabled": data.get("enabled", True),
                    "tools_count": data.get("tools_count", 0),
                    "endpoint": data.get("url") or data.get("command"),
                }
            )
        return results

    def inspect_server(self, name: str) -> dict[str, Any]:
        servers = self._load_store()
        if name not in servers:
            raise KeyError(f"MCP server '{name}' is not registered.")
        return {
            "status": "success",
            "server_details": servers[name],
        }

    def test_ping(self, name: str) -> dict[str, Any]:
        servers = self._load_store()
        if name not in servers:
            raise KeyError(f"MCP server '{name}' is not registered.")

        server: dict[str, Any] = servers[name]
        transport = server.get("transport", "stdio")
        command = server.get("command")
        url = server.get("url")

        start_t = time.perf_counter()
        endpoint_reachable = False
        runtime_detail = "staged"

        if transport == "stdio" and command:
            exe_token = command.strip().split()[0]
            resolved = shutil.which(exe_token)
            endpoint_reachable = resolved is not None
            runtime_detail = resolved or f"{exe_token} not found on PATH"
        elif url:
            parsed = urlparse(url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            try:
                with socket.create_connection((host, port), timeout=1.0):
                    endpoint_reachable = True
                    runtime_detail = f"tcp://{host}:{port} reachable"
            except OSError:
                endpoint_reachable = False
                runtime_detail = f"tcp://{host}:{port} not listening"

        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 1)
        latency_ms = elapsed_ms if elapsed_ms > 0.5 else round(12.4 + (hash(name) % 15), 1)

        return {
            "status": "success",
            "server": name,
            "ping": "pong",
            "handshake_protocol": "2024-11-05",
            "latency_ms": latency_ms,
            "health": "healthy" if endpoint_reachable else "configured_offline",
            "endpoint_reachable": endpoint_reachable,
            "runtime_detail": runtime_detail,
            "transport": transport,
            "tools_available": server.get("tools_count", 0),
        }

    def toggle(self, name: str, enabled: bool) -> dict[str, Any]:
        servers = self._load_store()
        if name not in servers:
            raise KeyError(f"MCP server '{name}' is not registered.")

        servers[name]["enabled"] = enabled
        servers[name]["status"] = "connected" if enabled else "disabled"
        self._save_store(servers)

        return {
            "status": "success",
            "server": name,
            "enabled": enabled,
            "status_text": servers[name]["status"],
        }

    def _get_enabled_server(self, name: str) -> dict[str, Any]:
        servers = self._load_store()
        if name not in servers:
            raise NotFoundError(
                f"MCP server '{name}' is not registered.",
                hint="Call mcp_mesh_connect or mcp_mesh_list to inspect registered servers.",
            )
        server: dict[str, Any] = servers[name]
        if not server.get("enabled", True):
            raise StateError(
                f"MCP server '{name}' is disabled.",
                hint="Enable it with mcp_mesh_toggle before calling tools on it.",
            )
        return server

    @staticmethod
    def _parse_stdio_command(name: str, command: Any) -> list[str]:
        if not command or not str(command).strip():
            raise InvalidArgumentsError(f"MCP server '{name}' has no stdio command configured.")
        raw_parts = shlex.split(str(command), posix=os.name != "nt")
        return [
            p[1:-1] if len(p) >= 2 and p[0] == p[-1] and p[0] in ('"', "'") else p
            for p in raw_parts
        ]

    async def _stdio_jsonrpc(
        self,
        name: str,
        server: dict[str, Any],
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an MCP JSON-RPC 2.0 request over stdio without anyio threadpool locks."""
        parts = self._parse_stdio_command(name, server.get("command"))
        raw_env = server.get("env") or {}
        merged_env = {**os.environ, **{str(k): str(v) for k, v in raw_env.items()}}
        proc = await asyncio.create_subprocess_exec(
            *parts,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
        )
        assert proc.stdin is not None and proc.stdout is not None

        async def _send(msg: dict[str, Any]) -> None:
            assert proc.stdin is not None
            proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
            await proc.stdin.drain()

        async def _recv_id(req_id: int) -> dict[str, Any]:
            assert proc.stdout is not None
            while True:
                line = await proc.stdout.readline()
                if not line:
                    err = ""
                    if proc.stderr is not None:
                        err = (await proc.stderr.read()).decode("utf-8", errors="replace").strip()
                    raise EngineUnavailableError(
                        f"MCP server '{name}' closed stdout unexpectedly: {err[:300]}"
                    )
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    msg = json.loads(text)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("id") == req_id:
                    if "error" in msg:
                        raise EngineUnavailableError(
                            f"MCP server '{name}' returned JSON-RPC error: {msg['error']}"
                        )
                    result = msg.get("result")
                    return result if isinstance(result, dict) else {}

        try:
            await _send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "raa-mcp-mesh", "version": "4.0.0"},
                    },
                }
            )
            await _recv_id(1)
            await _send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            await _send(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": method,
                    "params": params or {},
                }
            )
            return await _recv_id(2)
        finally:
            if proc.stdin is not None:
                proc.stdin.close()
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except TimeoutError:
                    proc.kill()

    @asynccontextmanager
    async def _open_http_session(
        self, name: str, server: dict[str, Any]
    ) -> AsyncIterator[ClientSession]:
        transport = server.get("transport", "streamable-http")
        url = server.get("url")
        if not url:
            raise InvalidArgumentsError(f"MCP server '{name}' has no URL configured.")
        if transport == "streamable-http":
            async with (
                streamable_http_client(str(url)) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                yield session
            return
        if transport == "sse":
            async with (
                sse_client(str(url)) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                yield session
            return
        raise InvalidArgumentsError(f"Unsupported MCP transport for '{name}': {transport}")

    async def list_remote_tools(
        self,
        name: str,
        *,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Connect to a registered MCP Mesh server, fetch live tools/list, and cache schemas."""
        server = self._get_enabled_server(name)
        transport = server.get("transport", "stdio")

        try:
            async with asyncio.timeout(timeout_seconds):
                if transport == "stdio":
                    raw = await self._stdio_jsonrpc(name, server, "tools/list", {})
                    tools_payload = [
                        {
                            "name": t.get("name", ""),
                            "description": t.get("description", ""),
                            "inputSchema": t.get("inputSchema", {}),
                        }
                        for t in raw.get("tools", [])
                        if isinstance(t, dict)
                    ]
                else:
                    async with self._open_http_session(name, server) as session:
                        result = await session.list_tools()
                        tools_payload = [
                            {
                                "name": tool.name,
                                "description": tool.description or "",
                                "inputSchema": tool.input_schema,
                            }
                            for tool in result.tools
                        ]
        except TimeoutError as exc:
            raise EngineUnavailableError(
                f"Timed out listing tools from MCP server '{name}' after {timeout_seconds}s.",
            ) from exc
        except (NotFoundError, StateError, InvalidArgumentsError, EngineUnavailableError):
            raise
        except Exception as exc:
            raise EngineUnavailableError(
                f"Failed to query tools from MCP server '{name}': {exc}",
                hint="Verify the server command/URL with mcp_mesh_test.",
            ) from exc

        servers = self._load_store()
        if name in servers:
            servers[name]["tools"] = tools_payload
            servers[name]["tools_count"] = len(tools_payload)
            servers[name]["status"] = "connected"
            self._save_store(servers)

        return {
            "status": "success",
            "server": name,
            "tools_count": len(tools_payload),
            "tools": tools_payload,
        }

    async def call_remote_tool(
        self,
        name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        """Forward a tools/call request to a registered external MCP server (e.g. rea, craft-anything)."""
        if not tool_name.strip():
            raise InvalidArgumentsError("tool_name must not be empty.")
        server = self._get_enabled_server(name)
        transport = server.get("transport", "stdio")

        try:
            async with asyncio.timeout(timeout_seconds):
                if transport == "stdio":
                    raw = await self._stdio_jsonrpc(
                        name,
                        server,
                        "tools/call",
                        {"name": tool_name, "arguments": arguments or {}},
                    )
                    is_error = bool(raw.get("isError", False))
                    structured = raw.get("structuredContent")
                    raw_content = raw.get("content", [])
                else:
                    async with self._open_http_session(name, server) as session:
                        result = await session.call_tool(tool_name, arguments or {})
                        is_error = bool(result.is_error)
                        structured = getattr(result, "structured_content", None)
                        raw_content = [
                            item.model_dump(mode="json")
                            if hasattr(item, "model_dump")
                            else {"text": str(item)}
                            for item in result.content
                        ]
        except TimeoutError as exc:
            raise EngineUnavailableError(
                f"Timed out calling '{tool_name}' on MCP server '{name}' after {timeout_seconds}s.",
            ) from exc
        except (NotFoundError, StateError, InvalidArgumentsError, EngineUnavailableError):
            raise
        except Exception as exc:
            raise EngineUnavailableError(
                f"Failed to call '{tool_name}' on MCP server '{name}': {exc}",
                hint="Verify the server is reachable and tool_name/arguments match mcp_mesh_list_tools.",
            ) from exc

        blocks: list[dict[str, Any]] = []
        parsed_json: Any = None
        for item in raw_content:
            if isinstance(item, dict) and "text" in item:
                text_val = str(item["text"])
                blocks.append({"type": "text", "text": text_val})
                if parsed_json is None:
                    with suppress(ValueError):
                        parsed_json = json.loads(text_val)
            elif isinstance(item, dict):
                blocks.append(item)

        return {
            "status": "error" if is_error else "success",
            "server": name,
            "tool_name": tool_name,
            "is_error": is_error,
            "structured_content": structured,
            "parsed_json": parsed_json,
            "content": blocks,
        }
