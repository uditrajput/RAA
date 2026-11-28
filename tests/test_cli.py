"""CLI tests. The CLI must use the same registry and runtime as MCP and REST."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from raa.cli.main import app
from raa.version import __version__
from tests.conftest import make_apk

runner = CliRunner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(
        app,
        ["--workspace", str(tmp_path / "workspace"), *args],
    )


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"raa {__version__}" in result.stdout
    assert "protocol 2026-07-28" in result.stdout


def test_project_create_and_list(tmp_path: Path) -> None:
    created = _invoke(tmp_path, "--json", "project", "create", "CLI project")
    assert created.exit_code == 0
    payload = json.loads(created.stdout)
    project_id = payload["data"]["id"]
    assert project_id.startswith("prj_")

    listed = _invoke(tmp_path, "--json", "project", "list")
    assert listed.exit_code == 0
    assert json.loads(listed.stdout)["data"]["count"] == 1

    shown = _invoke(tmp_path, "--json", "project", "show", project_id)
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["data"]["id"] == project_id


def test_tools_list_and_show(tmp_path: Path) -> None:
    listed = _invoke(tmp_path, "--json", "tools", "list")
    assert listed.exit_code == 0
    payload = json.loads(listed.stdout)
    assert payload["profile"] == "core"
    assert payload["count"] >= 135

    minimal = _invoke(tmp_path, "--profile", "minimal", "--json", "tools", "list")
    assert minimal.exit_code == 0
    assert json.loads(minimal.stdout)["count"] == 12

    shown = _invoke(tmp_path, "--json", "tools", "show", "artifact_ingest")
    assert shown.exit_code == 0
    schema = json.loads(shown.stdout)
    assert schema["name"] == "artifact_ingest"
    assert "project_id" in schema["input_schema"]["properties"]


def test_tools_call(tmp_path: Path) -> None:
    result = _invoke(
        tmp_path,
        "--json",
        "tools",
        "call",
        "project_create",
        "--args-json",
        '{"name": "Call project"}',
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["data"]["name"] == "Call project"


def test_unknown_tool_fails(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "tools", "show", "not_a_tool")
    assert result.exit_code == 1


def test_unknown_profile_fails(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--profile", "turbo", "version"])
    assert result.exit_code != 0


def test_setup_outputs_client_config(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "setup", "--agent", "generic")
    assert result.exit_code == 0
    config = json.loads(result.stdout)
    server = config["mcpServers"]["raa"]
    assert server["command"] == "raa"
    assert server["args"][0] == "--profile"
    assert "serve" in server["args"]
    assert "mcp" in server["args"]


def test_setup_writes_file(tmp_path: Path) -> None:
    output = tmp_path / "mcp.json"
    result = _invoke(tmp_path, "--json", "setup", "--agent", "codex", "--output", str(output))
    assert result.exit_code == 0
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert "[mcp_servers.raa]" in text
    assert 'command = "raa"' in text


def test_doctor_json(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "--json", "doctor")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["ok"] is True
    assert payload["data"]["implemented_tools"] >= 244


def test_manifest_commands(tmp_path: Path) -> None:
    apk = make_apk(tmp_path / "sample.apk")
    created = _invoke(tmp_path, "--json", "project", "create", "Manifest CLI")
    project_id = json.loads(created.stdout)["data"]["id"]
    ingested = _invoke(
        tmp_path,
        "--json",
        "artifact",
        "ingest",
        project_id,
        str(apk),
    )
    artifact_id = json.loads(ingested.stdout)["data"]["id"]
    analyzed = _invoke(tmp_path, "--json", "analyze", project_id, artifact_id)
    assert analyzed.exit_code == 0
    job_id = json.loads(analyzed.stdout)["job"]["id"]

    manifest = _invoke(tmp_path, "--json", "manifest", project_id, job_id)
    assert manifest.exit_code == 0
    assert json.loads(manifest.stdout)["data"]["package"] == "com.example.demo"

    components = _invoke(
        tmp_path,
        "--json",
        "components",
        project_id,
        job_id,
        "--exported-only",
    )
    assert components.exit_code == 0
    payload = json.loads(components.stdout)["data"]
    assert payload["total"] == 4
    assert all(item["effective_exported"] for item in payload["components"])

    permissions = _invoke(tmp_path, "--json", "permissions", project_id, job_id)
    assert permissions.exit_code == 0
    permission_payload = json.loads(permissions.stdout)["data"]
    assert permission_payload["requested_count"] == 2
    assert permission_payload["declared_count"] == 1


def test_resource_commands(tmp_path: Path) -> None:
    apk = make_apk(tmp_path / "sample.apk")
    created = _invoke(tmp_path, "--json", "project", "create", "Resource CLI")
    project_id = json.loads(created.stdout)["data"]["id"]
    ingested = _invoke(
        tmp_path,
        "--json",
        "artifact",
        "ingest",
        project_id,
        str(apk),
    )
    artifact_id = json.loads(ingested.stdout)["data"]["id"]
    analyzed = _invoke(tmp_path, "--json", "analyze", project_id, artifact_id)
    assert analyzed.exit_code == 0
    job_id = json.loads(analyzed.stdout)["job"]["id"]

    resources = _invoke(
        tmp_path,
        "--json",
        "resources",
        project_id,
        job_id,
        "--type",
        "string",
    )
    assert resources.exit_code == 0
    payload = json.loads(resources.stdout)["data"]
    assert payload["total"] == 4
    assert payload["summary"]["entry_count"] == 10

    resource = _invoke(
        tmp_path,
        "--json",
        "resource",
        project_id,
        job_id,
        "app_name",
    )
    assert resource.exit_code == 0
    detail = json.loads(resource.stdout)["data"]
    assert detail["variant_count"] == 3
    assert detail["type"] == "string"

    by_id = _invoke(
        tmp_path,
        "--json",
        "resource",
        project_id,
        job_id,
        "0x7f020000",
    )
    assert by_id.exit_code == 0
    assert json.loads(by_id.stdout)["data"]["type"] == "layout"

    human = _invoke(tmp_path, "resources", project_id, job_id, "--type", "string")
    assert human.exit_code == 0
    assert "app_name" in human.stdout
    assert "Demo App" in human.stdout

    human_detail = _invoke(tmp_path, "resource", project_id, job_id, "AppTheme")
    assert human_detail.exit_code == 0
    assert "complex" in human_detail.stdout


def test_source_commands(tmp_path: Path) -> None:
    apk = make_apk(tmp_path / "sample.apk")
    created = _invoke(tmp_path, "--json", "project", "create", "Source CLI")
    project_id = json.loads(created.stdout)["data"]["id"]
    ingested = _invoke(
        tmp_path,
        "--json",
        "artifact",
        "ingest",
        project_id,
        str(apk),
    )
    artifact_id = json.loads(ingested.stdout)["data"]["id"]
    analyzed = _invoke(tmp_path, "--json", "analyze", project_id, artifact_id)
    assert analyzed.exit_code == 0
    job_id = json.loads(analyzed.stdout)["job"]["id"]

    search = _invoke(
        tmp_path,
        "--json",
        "source",
        "search",
        project_id,
        job_id,
        "ApiClient",
        "--kind",
        "class",
    )
    assert search.exit_code == 0
    payload = json.loads(search.stdout)["data"]
    assert payload["total"] == 1
    assert payload["results"][0]["class"] == "com.example.demo.network.ApiClient"

    detail = _invoke(
        tmp_path,
        "--json",
        "source",
        "class",
        project_id,
        job_id,
        "com.example.demo.MainActivity",
    )
    assert detail.exit_code == 0
    klass = json.loads(detail.stdout)["data"]
    assert klass["method_total"] == 3
    assert klass["field_total"] == 2

    method = _invoke(
        tmp_path,
        "--json",
        "source",
        "method",
        project_id,
        job_id,
        "com.example.demo.MainActivity",
        "helper",
    )
    assert method.exit_code == 0
    payload = json.loads(method.stdout)["data"]
    assert payload["outgoing_count"] == 2
    assert payload["incoming_count"] == 1

    human = _invoke(
        tmp_path,
        "source",
        "search",
        project_id,
        job_id,
        "onCreate",
        "--kind",
        "method",
    )
    assert human.exit_code == 0
    assert "onCreate" in human.stdout

    human_detail = _invoke(
        tmp_path,
        "source",
        "class",
        project_id,
        job_id,
        "com.example.demo.MainActivity",
    )
    assert human_detail.exit_code == 0
    assert "MainActivity" in human_detail.stdout
    assert "onCreate" in human_detail.stdout

    refs = _invoke(
        tmp_path,
        "--json",
        "source",
        "refs",
        project_id,
        job_id,
        "helper",
        "--kind",
        "method_call",
    )
    assert refs.exit_code == 0
    assert json.loads(refs.stdout)["data"]["total"] == 1

    callers = _invoke(
        tmp_path,
        "source",
        "callers",
        project_id,
        job_id,
        "com.example.demo.MainActivity",
        "helper",
    )
    assert callers.exit_code == 0
    assert "<init>" in callers.stdout

    callees = _invoke(
        tmp_path,
        "--json",
        "source",
        "callees",
        project_id,
        job_id,
        "com.example.demo.MainActivity",
        "<init>",
    )
    assert callees.exit_code == 0
    assert json.loads(callees.stdout)["data"]["total"] == 1


def test_skill_list_and_show(tmp_path: Path) -> None:
    listed = _invoke(tmp_path, "--json", "skill", "list")
    assert listed.exit_code == 0
    payload = json.loads(listed.stdout)
    assert payload["count"] >= 11
    assert {"android-triage", "platform-check", "report-and-export"} <= {
        skill["id"] for skill in payload["skills"]
    }

    shown = _invoke(tmp_path, "skill", "show", "android-triage")
    assert shown.exit_code == 0
    assert "# Android triage" in shown.stdout
    assert "artifact_ingest" in shown.stdout


def test_skill_install(tmp_path: Path) -> None:
    result = _invoke(
        tmp_path,
        "--json",
        "skill",
        "install",
        "android-triage",
        "--target",
        "claude-code",
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["skills"] == ["android-triage"]
    destination = Path(payload["data"]["destination"])
    assert (destination / "android-triage" / "SKILL.md").is_file()
    assert (destination / "android-triage" / "references" / "evidence-checklist.md").is_file()


def test_skill_install_all_with_directory(tmp_path: Path) -> None:
    output = tmp_path / "all-skills"
    result = _invoke(
        tmp_path,
        "--json",
        "skill",
        "install",
        "--all",
        "--target",
        "generic",
        "--dir",
        str(output),
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["data"]["skills"]) >= 11
    assert (output / "platform-check" / "SKILL.md").is_file()


def test_skill_install_requires_selector(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "skill", "install", "--target", "generic")
    assert result.exit_code != 0


def test_ui_cli_commands(tmp_path: Path) -> None:
    apk = make_apk(tmp_path / "ui_cli.apk")
    created = _invoke(tmp_path, "--json", "project", "create", "UI CLI")
    project_id = json.loads(created.stdout)["data"]["id"]
    ingested = _invoke(tmp_path, "--json", "artifact", "ingest", project_id, str(apk))
    artifact_id = json.loads(ingested.stdout)["data"]["id"]

    analyzed = _invoke(tmp_path, "--json", "analyze", project_id, artifact_id)
    assert analyzed.exit_code == 0
    job_id = json.loads(analyzed.stdout)["job"]["id"]

    # ui screens
    screens = _invoke(tmp_path, "--json", "--profile", "ui", "ui", "screens", project_id, job_id)
    assert screens.exit_code == 0
    screens_data = json.loads(screens.stdout)["data"]
    assert screens_data["total"] >= 1
    screen_id = screens_data["items"][0]["screen_id"]

    # ui screen
    screen = _invoke(
        tmp_path, "--json", "--profile", "ui", "ui", "screen", project_id, job_id, screen_id
    )
    assert screen.exit_code == 0
    assert json.loads(screen.stdout)["data"]["screen_id"] == screen_id

    # ui assets
    assets = _invoke(tmp_path, "--json", "--profile", "ui", "ui", "assets", project_id, job_id)
    assert assets.exit_code == 0

    # ui coverage
    cov = _invoke(tmp_path, "--json", "--profile", "ui", "ui", "coverage", project_id, job_id)
    assert cov.exit_code == 0
    assert "discovered_screens" in json.loads(cov.stdout)["data"]


def test_init_first_run_and_setup_ui_launch(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    launched: list[dict[str, Any]] = []

    def fake_launch(
        runtime: Any,
        *,
        host: str | None = None,
        port: int | None = None,
        open_browser: bool = True,
    ) -> None:
        launched.append({"host": host, "port": port, "open_browser": open_browser})

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr("raa.cli.main._serve_ui_and_open_browser", fake_launch)

    # First-time init automatically launches the Setup UI server
    res1 = _invoke(tmp_path, "init")
    assert res1.exit_code == 0
    assert len(launched) == 1

    # Second init on the same workspace does NOT auto-launch UI unless --ui is passed
    res2 = _invoke(tmp_path, "init")
    assert res2.exit_code == 0
    assert len(launched) == 1

    # Explicit setup-ui command launches the UI server
    res3 = _invoke(tmp_path, "setup-ui", "--port", "8770", "--no-browser")
    assert res3.exit_code == 0
    assert launched[-1] == {"host": None, "port": 8770, "open_browser": False}
