---
name: raa-self-evolving-recipes
description: Dynamically compiles, self-heals, and patches reverse engineering recipes and stores persistent procedural lessons to MEMORY.md.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [skills_procedure_save, skills_procedure_patch, skills_procedure_read, recipe_self_evolve, memory_lesson_learn, memory_lesson_query]
---

# RAA Self-Evolving Recipes Skill

Modeled after Nod's dynamic skills and self-healing systems.

## Key Capabilities
- Synthesizes bypass recipes for uncatalogued packers
- Surgically patches existing procedures when app structures drift
- Dual-tier memory preservation in `MEMORY.md`

## Verification & Discipline Rules
- Only persist a procedure via `skills_procedure_save` or `skills_procedure_patch` after it has been verified against a target artifact.
- Record negative constraints and failure modes in `memory_lesson_learn` so agents do not repeat failing approaches.
