"""Self-Evolving Reverse Engineering Engine & Dynamic Procedural Memory.

Modeled after Nod's dynamic skills system, this engine captures successful reverse
engineering workflows, unpacker patterns, and bypass recipes, persisting them to
MEMORY.md and enabling surgical patching when target app structures drift.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SelfEvolutionService:
    """Manages dynamic procedural recipes, self-healing patches, and persistent lessons."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.memory_dir = workspace_root / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.recipes_file = self.memory_dir / "recipes.json"
        self._init_memory()

    def _init_memory(self) -> None:
        if not self.memory_file.exists():
            header = (
                "# RAA Persistent Procedural Memory & Self-Evolved Lessons\n\n"
                "This document records verified dynamic reverse engineering procedures, "
                "custom packer unpackers, root/SSL bypass heuristics, and operational guardrails.\n\n"
                "## 1. Verified Dynamic Recipes\n\n"
                "## 2. Lessons & Policy Constraints\n\n"
            )
            with open(self.memory_file, "w", encoding="utf-8") as f:
                f.write(header)

        if not self.recipes_file.exists():
            with open(self.recipes_file, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def _load_recipes(self) -> dict[str, Any]:
        try:
            if self.recipes_file.exists():
                with open(self.recipes_file, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                    return data
        except Exception as exc:
            logger.warning("Failed to load recipes from %s: %s", self.recipes_file, exc)
        return {}

    def _save_recipes(self, data: dict[str, Any]) -> None:
        with open(self.recipes_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_procedure(
        self,
        name: str,
        category: str,
        steps: list[str],
        target_fingerprint: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        recipes = self._load_recipes()
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()

        recipe_entry = {
            "name": name,
            "category": category,
            "steps": steps,
            "target_fingerprint": target_fingerprint,
            "description": description,
            "created_at": timestamp,
            "updated_at": timestamp,
            "version": 1,
            "patch_history": [],
        }
        recipes[name] = recipe_entry
        self._save_recipes(recipes)

        # Append to MEMORY.md
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(f"\n### Recipe: {name} (Category: {category})\n")
            if description:
                f.write(f"*{description}*\n\n")
            if target_fingerprint:
                f.write(f"- **Target Fingerprint:** `{target_fingerprint}`\n")
            f.write(f"- **Created:** {timestamp}\n")
            f.write("- **Execution Steps:**\n")
            for idx, s in enumerate(steps, 1):
                f.write(f"  {idx}. {s}\n")

        return {
            "status": "success",
            "recipe_name": name,
            "version": 1,
            "total_steps": len(steps),
            "memory_file": str(self.memory_file),
        }

    def patch_procedure(
        self,
        name: str,
        updated_steps: list[str],
        patch_reason: str = "Drift adaptation",
    ) -> dict[str, Any]:
        recipes = self._load_recipes()
        if name not in recipes:
            raise KeyError(f"Recipe '{name}' not found. Cannot patch.")

        recipe = recipes[name]
        old_version = recipe.get("version", 1)
        new_version = old_version + 1
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()

        recipe["patch_history"].append(
            {
                "previous_version": old_version,
                "timestamp": timestamp,
                "reason": patch_reason,
                "previous_steps": recipe["steps"],
            }
        )
        recipe["steps"] = updated_steps
        recipe["version"] = new_version
        recipe["updated_at"] = timestamp
        recipes[name] = recipe
        self._save_recipes(recipes)

        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(f"\n#### [Patch v{new_version}] {name} ({timestamp})\n")
            f.write(f"- **Reason:** {patch_reason}\n")
            f.write("- **Updated Steps:**\n")
            for idx, s in enumerate(updated_steps, 1):
                f.write(f"  {idx}. {s}\n")

        return {
            "status": "success",
            "recipe_name": name,
            "new_version": new_version,
            "patch_reason": patch_reason,
            "total_steps": len(updated_steps),
        }

    def read_procedure(self, name: str) -> dict[str, Any]:
        recipes = self._load_recipes()
        if name not in recipes:
            raise KeyError(f"Recipe '{name}' not found.")
        return {
            "status": "success",
            "recipe": recipes[name],
        }

    def list_procedures(self) -> list[dict[str, Any]]:
        recipes = self._load_recipes()
        return list(recipes.values())

    def evolve_recipe(
        self,
        problem_description: str,
        observed_anomaly: str,
        target_app: str = "",
    ) -> dict[str, Any]:
        """Synthesizes an automated bypass recipe for uncatalogued packers or hybrid frameworks."""
        recipe_name = f"evolved_bypass_{target_app.replace('.', '_') or 'generic'}_{len(self.list_procedures()) + 1}"
        steps = [
            f"Analyze anomaly '{observed_anomaly}' with memory mapping dump.",
            "Identify candidate decryption stub or BoringSSL hook offset.",
            "Apply zero-trace smali patch or Frida trampoline.",
            "Verify process continues execution without crash or integrity exit.",
        ]
        res = self.save_procedure(
            name=recipe_name,
            category="autonomous_evolution",
            steps=steps,
            target_fingerprint=target_app,
            description=f"Auto-evolved resolution for {problem_description}",
        )
        res["anomaly"] = observed_anomaly
        res["strategy"] = "adaptive_hook_synthesis"
        return res

    def learn_lesson(
        self, rule_title: str, instruction: str, category: str = "general"
    ) -> dict[str, Any]:
        """Ingests explicit user operational corrections and permanent policy rules."""
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(f"\n- **[{category.upper()}] {rule_title}** ({timestamp}): {instruction}\n")

        return {
            "status": "success",
            "rule_title": rule_title,
            "category": category,
            "instruction": instruction,
            "persisted_to": str(self.memory_file),
        }

    def query_lessons(self, query: str = "") -> dict[str, Any]:
        """Queries curated memory lessons and anti-patterns."""
        if not self.memory_file.exists():
            return {"lessons": [], "total": 0}

        with open(self.memory_file, encoding="utf-8") as f:
            content = f.read()

        lessons = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- **[") and (not query or query.lower() in line.lower()):
                lessons.append(line)

        return {
            "status": "success",
            "query": query,
            "matched_lessons": lessons,
            "total_matches": len(lessons),
        }
