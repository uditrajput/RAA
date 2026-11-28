"""Self-Evolving Skills and Procedural Learning MCP tools."""

from __future__ import annotations

from pydantic import BaseModel, Field

from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import CORE


class SkillsProcedureSaveInput(BaseModel):
    """Parameters to persist a newly discovered reverse engineering procedure."""

    name: str = Field(min_length=1, description="Unique recipe name.")
    category: str = Field(
        description="Procedure category (e.g. unpacking, bypass, hooking, obfuscation)."
    )
    steps: list[str] = Field(min_length=1, description="Sequential actionable steps.")
    target_fingerprint: str = Field(
        default="", description="Target package or framework signature."
    )
    description: str = Field(default="", description="Procedure overview and context.")


class SkillsProcedurePatchInput(BaseModel):
    """Parameters to surgically patch an existing procedural skill."""

    name: str = Field(description="Name of the recipe to patch.")
    updated_steps: list[str] = Field(min_length=1, description="Updated complete step sequence.")
    patch_reason: str = Field(default="Target structure drift", description="Reason for patching.")


class SkillsProcedureReadInput(BaseModel):
    """Parameters to read a procedural task recipe."""

    name: str = Field(description="Name of the recipe to read.")


class RecipeSelfEvolveInput(BaseModel):
    """Parameters to synthesize an automated bypass recipe for uncatalogued packers."""

    problem_description: str = Field(
        description="Description of the reversing obstacle or packing mechanism."
    )
    observed_anomaly: str = Field(
        description="Specific anomaly observed (e.g. anti-Frida signal, encrypted dex)."
    )
    target_app: str = Field(default="", description="Optional target app or package name.")


class MemoryLessonLearnInput(BaseModel):
    """Parameters to record permanent user policies or operational lessons."""

    rule_title: str = Field(min_length=1, description="Short title of the rule or lesson.")
    instruction: str = Field(min_length=1, description="Specific constraint or guidance.")
    category: str = Field(
        default="operational", description="Category (e.g. safety, target_constraint, preference)."
    )


class MemoryLessonQueryInput(BaseModel):
    """Parameters to query persistent lessons and anti-patterns."""

    query: str = Field(default="", description="Search query or keyword.")


async def _skills_procedure_save(ctx: ToolContext, args: SkillsProcedureSaveInput) -> ToolOutcome:
    res = ctx.runtime.self_evolution.save_procedure(
        name=args.name,
        category=args.category,
        steps=args.steps,
        target_fingerprint=args.target_fingerprint,
        description=args.description,
    )
    return ToolOutcome(data=res)


async def _skills_procedure_patch(ctx: ToolContext, args: SkillsProcedurePatchInput) -> ToolOutcome:
    res = ctx.runtime.self_evolution.patch_procedure(
        name=args.name,
        updated_steps=args.updated_steps,
        patch_reason=args.patch_reason,
    )
    return ToolOutcome(data=res)


async def _skills_procedure_read(ctx: ToolContext, args: SkillsProcedureReadInput) -> ToolOutcome:
    res = ctx.runtime.self_evolution.read_procedure(name=args.name)
    return ToolOutcome(data=res)


async def _recipe_self_evolve(ctx: ToolContext, args: RecipeSelfEvolveInput) -> ToolOutcome:
    res = ctx.runtime.self_evolution.evolve_recipe(
        problem_description=args.problem_description,
        observed_anomaly=args.observed_anomaly,
        target_app=args.target_app,
    )
    return ToolOutcome(data=res)


async def _memory_lesson_learn(ctx: ToolContext, args: MemoryLessonLearnInput) -> ToolOutcome:
    res = ctx.runtime.self_evolution.learn_lesson(
        rule_title=args.rule_title,
        instruction=args.instruction,
        category=args.category,
    )
    return ToolOutcome(data=res)


async def _memory_lesson_query(ctx: ToolContext, args: MemoryLessonQueryInput) -> ToolOutcome:
    res = ctx.runtime.self_evolution.query_lessons(query=args.query)
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="skills_procedure_save",
            title="Save Procedural Skill",
            description="Dynamically compile and persist newly discovered reverse engineering procedures to MEMORY.md.",
            input_model=SkillsProcedureSaveInput,
            handler=_skills_procedure_save,
            family="evolution",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="skills_procedure_patch",
            title="Patch Procedural Skill",
            description="Surgically patch existing procedural skills when target app structures or obfuscation drifts.",
            input_model=SkillsProcedurePatchInput,
            handler=_skills_procedure_patch,
            family="evolution",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="skills_procedure_read",
            title="Read Procedural Skill",
            description="Read full procedural task guides dynamically on progressive disclosure.",
            input_model=SkillsProcedureReadInput,
            handler=_skills_procedure_read,
            family="evolution",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="recipe_self_evolve",
            title="Self-Evolve Bypass Recipe",
            description="Synthesize automated bypass recipes for uncatalogued packers and hybrid frameworks.",
            input_model=RecipeSelfEvolveInput,
            handler=_recipe_self_evolve,
            family="evolution",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="memory_lesson_learn",
            title="Learn Permanent Lesson",
            description="Ingest explicit user operational corrections and permanent policy instructions.",
            input_model=MemoryLessonLearnInput,
            handler=_memory_lesson_learn,
            family="evolution",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="memory_lesson_query",
            title="Query Memory Lessons",
            description="Query curated memory lessons and anti-patterns during planning.",
            input_model=MemoryLessonQueryInput,
            handler=_memory_lesson_query,
            family="evolution",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
