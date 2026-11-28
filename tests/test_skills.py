"""Agent Skills discovery and installation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from raa.errors import InvalidArgumentsError, NotFoundError
from raa.runtime import Runtime
from raa.services.skills import SkillService


def test_discovers_repository_skills() -> None:
    service = SkillService()
    skills = service.discover()
    assert {"android-triage", "platform-check", "report-and-export"} <= {
        skill.id for skill in skills
    }
    assert len(skills) >= 11
    for skill in skills:
        assert skill.description
        assert skill.version
        assert skill.tools
        assert "SKILL.md" in skill.files()


def test_android_triage_metadata() -> None:
    skill = SkillService().get("android-triage")
    assert skill.name == "android-triage"
    assert "artifact_ingest" in skill.tools
    assert "analysis_start" in skill.tools
    assert skill.description.startswith("Use when")


def test_unknown_skill() -> None:
    with pytest.raises(NotFoundError):
        SkillService().get("missing-skill")


def test_invalid_skill_id() -> None:
    with pytest.raises(InvalidArgumentsError):
        SkillService().get("../escape")


def test_install_copies_manifest_and_references(tmp_path: Path) -> None:
    service = SkillService()
    written = service.install("android-triage", tmp_path / "installed")
    target = tmp_path / "installed" / "android-triage"
    assert (target / "SKILL.md").is_file()
    assert (target / "references" / "evidence-checklist.md").is_file()
    assert written
    assert all(path.is_file() for path in written)


def test_install_all(tmp_path: Path) -> None:
    service = SkillService()
    for skill in service.discover():
        service.install(skill.id, tmp_path / "all")
    assert {"android-triage", "platform-check", "report-and-export"} <= {
        path.name for path in (tmp_path / "all").iterdir()
    }
    assert len(list((tmp_path / "all").iterdir())) >= 11


def test_malformed_frontmatter_fails(tmp_path: Path) -> None:
    directory = tmp_path / "broken-skill"
    directory.mkdir()
    (directory / "SKILL.md").write_text(
        "---\nname: broken\ndescription: missing close\n",
        encoding="utf-8",
    )
    with pytest.raises(InvalidArgumentsError):
        SkillService(extra_roots=[tmp_path]).discover()


def test_missing_description_fails(tmp_path: Path) -> None:
    directory = tmp_path / "no-description"
    directory.mkdir()
    (directory / "SKILL.md").write_text(
        "---\nname: no-description\nversion: 1.0.0\n---\n\n# Empty\n",
        encoding="utf-8",
    )
    with pytest.raises(InvalidArgumentsError):
        SkillService(extra_roots=[tmp_path]).discover()


def test_runtime_reports_skill_count(runtime: Runtime) -> None:
    summary = runtime.info()["skills"]
    assert isinstance(summary, dict)
    assert summary["count"] >= 11
    assert summary["error"] is None
