"""Agent Skills discovery and installation.

Skills are plain ``SKILL.md`` directories. They are deliberately parsed with a
small frontmatter reader instead of a YAML dependency: the format is simple,
and a malformed skill must fail with a clear error rather than import a parser.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from raa.errors import InvalidArgumentsError, NotFoundError

_SKILL_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_FRONTMATTER_LIST = re.compile(r"^\[(.*)]$")


@dataclass(frozen=True, slots=True)
class Skill:
    id: str
    name: str
    description: str
    version: str
    tools: tuple[str, ...]
    path: Path
    content: str

    def files(self) -> list[str]:
        return sorted(
            item.relative_to(self.path).as_posix()
            for item in self.path.rglob("*")
            if item.is_file()
        )

    def summary(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tools": list(self.tools),
            "files": self.files(),
        }


class SkillService:
    """Find, describe and copy skills without touching host internals."""

    def __init__(self, extra_roots: Iterable[Path] = ()) -> None:
        modules_root = Path(__file__).resolve().parents[1]
        repository_root = Path(__file__).resolve().parents[3]
        candidates = [
            modules_root / "resources" / "skills",
            repository_root / "skills",
            Path.cwd() / "skills",
            *extra_roots,
        ]
        self.roots = tuple(
            dict.fromkeys(
                root.expanduser().resolve()
                for root in candidates
                if root.expanduser().resolve().is_dir()
            )
        )

    def discover(self) -> list[Skill]:
        skills: dict[str, Skill] = {}
        for root in self.roots:
            for directory in sorted(root.iterdir()):
                if not directory.is_dir() or directory.name in skills:
                    continue
                manifest = directory / "SKILL.md"
                if not manifest.is_file():
                    continue
                skill = _load_skill(directory)
                skills[skill.id] = skill
        return sorted(skills.values(), key=lambda skill: skill.id)

    def get(self, skill_id: str) -> Skill:
        if not _SKILL_ID.match(skill_id):
            raise InvalidArgumentsError(
                f"Invalid skill identifier: {skill_id}",
                hint="Skill identifiers use lowercase letters, digits and hyphens.",
            )
        for skill in self.discover():
            if skill.id == skill_id:
                return skill
        raise NotFoundError(
            f"Skill not found: {skill_id}",
            hint="Run 'raa skill list' to discover installed skills.",
        )

    def install(self, skill_id: str, destination: Path) -> list[Path]:
        skill = self.get(skill_id)
        base_dest = destination.expanduser().resolve()
        target = (base_dest / skill.id).resolve()
        if not target.is_relative_to(base_dest):
            raise InvalidArgumentsError("Invalid skill install path.")
        target.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for source in sorted(skill.path.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(skill.path)
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)
            written.append(output)
        return written


def _load_skill(directory: Path) -> Skill:
    manifest = directory / "SKILL.md"
    text = manifest.read_text(encoding="utf-8")
    metadata, _ = _parse_frontmatter(text)
    skill_id = directory.name
    if not _SKILL_ID.match(skill_id):
        raise InvalidArgumentsError(
            f"Skill directory has an invalid name: {skill_id}",
            hint="Use lowercase letters, digits and hyphens for the directory name.",
        )
    name = str(metadata.get("name") or skill_id)
    description = str(metadata.get("description") or "").strip()
    if not description:
        raise InvalidArgumentsError(
            f"Skill {skill_id} has no description.",
            hint="Add a 'description' field to the SKILL.md frontmatter.",
        )
    tools = metadata.get("tools", [])
    if isinstance(tools, str):
        tool_names = [tools]
    elif isinstance(tools, (list, tuple)):
        tool_names = [str(tool) for tool in tools]
    else:
        tool_names = []
    return Skill(
        id=skill_id,
        name=name,
        description=description,
        version=str(metadata.get("version") or "0.0.0"),
        tools=tuple(tool_names),
        path=directory,
        content=text,
    )


def _parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if end is None:
        raise InvalidArgumentsError(
            "SKILL.md frontmatter is not terminated.",
            hint="Close the YAML frontmatter with a line containing '---'.",
        )
    metadata: dict[str, object] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, raw_value = stripped.partition(":")
        if not separator:
            continue
        key = key.strip()
        if not key:
            continue
        metadata[key] = _parse_value(raw_value.strip())
    return metadata, "\n".join(lines[end + 1 :]).lstrip("\n")


def _parse_value(value: str) -> object:
    if not value:
        return ""
    match = _FRONTMATTER_LIST.match(value)
    if match:
        inner = match.group(1).strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
