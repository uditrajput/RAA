"""Untrusted Content Shield and Zero-Knowledge Vault MCP tools."""

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


class UntrustedContentShieldInput(BaseModel):
    """Parameters to shield and quarantine untrusted decompiled code or manifest data."""

    raw_content: str = Field(description="Raw decompiled code, manifest XML, or network payload.")
    source_type: str = Field(default="decompiled_code", description="Content source category.")
    max_preview_len: int = Field(
        default=500, description="Max safe characters to display in surrogate."
    )


class VaultSecretStoreInput(BaseModel):
    """Parameters to store a sensitive credential in the local zero-knowledge vault."""

    key_name: str = Field(min_length=1, description="Identifier for the secret.")
    secret_value: str = Field(min_length=1, description="Secret value (token, API key, password).")
    description: str = Field(
        default="", description="Optional note describing the secret's purpose."
    )


class VaultSecretInjectInput(BaseModel):
    """Parameters to inject a vaulted secret into a payload or template without LLM exposure."""

    key_name: str = Field(description="Secret identifier in vault.")
    target_template: str = Field(
        description="Target template containing '{{KEY_NAME}}' placeholder."
    )


class BrowserHandoffTriggerInput(BaseModel):
    """Parameters to trigger human-in-the-loop browser handoff for OAuth/CAPTCHA."""

    target_url: str = Field(description="Destination authentication or challenge URL.")
    reason: str = Field(default="oauth_2fa_captcha", description="Reason for handoff.")
    timeout_seconds: int = Field(default=300, ge=30, le=1800, description="Session timeout.")


async def _untrusted_content_shield(
    ctx: ToolContext, args: UntrustedContentShieldInput
) -> ToolOutcome:
    res = ctx.runtime.vault.shield_untrusted_content(
        raw_content=args.raw_content,
        source_type=args.source_type,
        max_preview_len=args.max_preview_len,
    )
    return ToolOutcome(data=res)


async def _vault_secret_store(ctx: ToolContext, args: VaultSecretStoreInput) -> ToolOutcome:
    res = ctx.runtime.vault.store_secret(
        key_name=args.key_name,
        secret_value=args.secret_value,
        description=args.description,
    )
    return ToolOutcome(data=res)


async def _vault_secret_inject(ctx: ToolContext, args: VaultSecretInjectInput) -> ToolOutcome:
    res = ctx.runtime.vault.inject_secret(
        key_name=args.key_name,
        target_template=args.target_template,
    )
    return ToolOutcome(data=res)


async def _browser_handoff_trigger(
    ctx: ToolContext, args: BrowserHandoffTriggerInput
) -> ToolOutcome:
    res = ctx.runtime.vault.trigger_browser_handoff(
        target_url=args.target_url,
        reason=args.reason,
        timeout_seconds=args.timeout_seconds,
    )
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="untrusted_content_shield",
            title="Shield Untrusted Content",
            description="Wrap untrusted decompiled code, manifest attributes, and network payloads in quarantine blocks.",
            input_model=UntrustedContentShieldInput,
            handler=_untrusted_content_shield,
            family="vault_shield",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="vault_secret_store",
            title="Store Secret in Zero-Knowledge Vault",
            description="Securely store API keys, tokens, and keystore passwords in local encrypted vault.",
            input_model=VaultSecretStoreInput,
            handler=_vault_secret_store,
            family="vault_shield",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="vault_secret_inject",
            title="Inject Secret into Target",
            description="Inject secrets directly into target endpoints or WebViews without exposing plaintext to LLM context.",
            input_model=VaultSecretInjectInput,
            handler=_vault_secret_inject,
            family="vault_shield",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="browser_handoff_trigger",
            title="Trigger Interactive Browser Handoff",
            description="Initiate interactive human-in-the-loop browser handoff for CAPTCHAs, MFA, and OAuth webviews.",
            input_model=BrowserHandoffTriggerInput,
            handler=_browser_handoff_trigger,
            family="vault_shield",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
