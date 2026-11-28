"""Mobile Channels and Conversational Agent MCP tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import CORE


class ChannelPromptReceiveInput(BaseModel):
    """Parameters to ingest and validate an inbound mobile prompt."""

    channel: Literal["telegram", "whatsapp"] = Field(description="Origin channel.")
    sender_id: str = Field(description="Sender phone number or chat identifier.")
    prompt: str = Field(min_length=1, description="Natural language prompt.")


class ChannelMessageDispatchInput(BaseModel):
    """Parameters to dispatch a formatted message to a mobile user."""

    channel: Literal["telegram", "whatsapp"] = Field(description="Destination channel.")
    recipient: str = Field(description="Recipient chat ID or phone number.")
    text: str = Field(min_length=1, description="Message text (Markdown or plain).")


class ChannelApkDeliverInput(BaseModel):
    """Parameters to upload and deliver a binary APK to a mobile user."""

    channel: Literal["telegram", "whatsapp"] = Field(description="Destination channel.")
    recipient: str = Field(description="Recipient chat ID or phone number.")
    apk_path: str = Field(description="Local path to .apk binary file.")
    caption: str = Field(default="", description="Optional file caption.")


class ChannelIntensityConfigureInput(BaseModel):
    """Parameters to configure notification cadence."""

    mode: Literal["start_end", "interval", "milestone", "adaptive"] | None = Field(
        default=None, description="Cadence mode."
    )
    interval_minutes: int | None = Field(
        default=None, ge=1, le=1440, description="Interval in minutes (1, 2, 5, 10, or custom)."
    )
    urgent_cve_breakin: bool | None = Field(
        default=None, description="Instantly break cadence on critical CVEs/findings."
    )


class ChannelIntensityGetInput(BaseModel):
    """Parameters to query active cadence mode and stats."""

    pass


class ChannelPairWhatsappInput(BaseModel):
    """Parameters to generate WhatsApp Web QR pairing code."""

    pass


class ChannelTestPingInput(BaseModel):
    """Parameters to send a test ping over a mobile channel."""

    channel: Literal["telegram", "whatsapp"] = Field(description="Target channel.")
    target: str = Field(description="Chat ID or phone number.")


class ChannelWhitelistManageInput(BaseModel):
    """Parameters to register or revoke authorized mobile users."""

    action: Literal["add", "remove", "list"] = Field(description="Action to perform.")
    channel: Literal["telegram", "whatsapp"] = Field(description="Target channel.")
    identifier: str = Field(default="", description="Phone number or chat ID (for add/remove).")


class ChannelFileDeliverInput(BaseModel):
    """Parameters to deliver any file (APK, screenshot image, or Markdown/JSON/HTML report) over mobile channels."""

    channel: Literal["telegram", "whatsapp"] = Field(description="Destination channel.")
    recipient: str = Field(description="Recipient chat ID or phone number.")
    file_path: str = Field(description="Local path to APK, image, or report file.")
    caption: str = Field(default="", description="Optional caption.")


class ChannelProgressReportInput(BaseModel):
    """Parameters to push a structured progress report (and optional attachment) over WhatsApp/Telegram."""

    stage: str = Field(min_length=1, description="Current workflow stage.")
    progress_pct: int = Field(ge=0, le=100, description="Completion percentage.")
    summary: str = Field(min_length=1, description="Progress summary.")
    channel: Literal["telegram", "whatsapp"] | None = Field(
        default=None, description="Optional target channel."
    )
    recipient: str | None = Field(default=None, description="Optional recipient chat ID or phone.")
    project_id: str | None = Field(default=None, description="Optional RAA project ID.")
    attachment_path: str | None = Field(
        default=None, description="Optional APK, image, or report path."
    )


async def _channel_prompt_receive(ctx: ToolContext, args: ChannelPromptReceiveInput) -> ToolOutcome:
    res = ctx.runtime.channels.receive_prompt(
        channel=args.channel, sender_id=args.sender_id, prompt=args.prompt
    )
    return ToolOutcome(data=res)


async def _channel_message_dispatch(
    ctx: ToolContext, args: ChannelMessageDispatchInput
) -> ToolOutcome:
    res = ctx.runtime.channels.dispatch_message(
        channel=args.channel, recipient=args.recipient, text=args.text
    )
    return ToolOutcome(data=res)


async def _channel_apk_deliver(ctx: ToolContext, args: ChannelApkDeliverInput) -> ToolOutcome:
    res = ctx.runtime.channels.deliver_apk(
        channel=args.channel, recipient=args.recipient, apk_path=args.apk_path, caption=args.caption
    )
    return ToolOutcome(data=res)


async def _channel_intensity_configure(
    ctx: ToolContext, args: ChannelIntensityConfigureInput
) -> ToolOutcome:
    res = ctx.runtime.cadence.configure(
        mode=args.mode,
        interval_minutes=args.interval_minutes,
        urgent_cve_breakin=args.urgent_cve_breakin,
    )
    return ToolOutcome(data=res)


async def _channel_intensity_get(ctx: ToolContext, args: ChannelIntensityGetInput) -> ToolOutcome:
    res = ctx.runtime.cadence.get_status()
    return ToolOutcome(data=res)


async def _channel_pair_whatsapp(ctx: ToolContext, args: ChannelPairWhatsappInput) -> ToolOutcome:
    res = ctx.runtime.channels.whatsapp.generate_pairing_qr()
    return ToolOutcome(data=res)


async def _channel_test_ping(ctx: ToolContext, args: ChannelTestPingInput) -> ToolOutcome:
    res = ctx.runtime.channels.test_ping(channel=args.channel, target=args.target)
    return ToolOutcome(data=res)


async def _channel_whitelist_manage(
    ctx: ToolContext, args: ChannelWhitelistManageInput
) -> ToolOutcome:
    res = ctx.runtime.channels.manage_whitelist(
        action=args.action, channel=args.channel, identifier=args.identifier
    )
    return ToolOutcome(data=res)


async def _channel_file_deliver(ctx: ToolContext, args: ChannelFileDeliverInput) -> ToolOutcome:
    res = ctx.runtime.channels.deliver_file(
        channel=args.channel,
        recipient=args.recipient,
        file_path=args.file_path,
        caption=args.caption,
    )
    return ToolOutcome(data=res)


async def _channel_progress_report(
    ctx: ToolContext, args: ChannelProgressReportInput
) -> ToolOutcome:
    res = ctx.runtime.channels.broadcast_progress(
        stage=args.stage,
        progress_pct=args.progress_pct,
        summary=args.summary,
        channel=args.channel,
        recipient=args.recipient,
        project_id=args.project_id,
        attachment_path=args.attachment_path,
    )
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="channel_prompt_receive",
            title="Ingest Mobile Inbound Prompt",
            description="Ingest and validate inbound mobile natural language prompts from Telegram and WhatsApp.",
            input_model=ChannelPromptReceiveInput,
            handler=_channel_prompt_receive,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_message_dispatch",
            title="Dispatch Mobile Message",
            description="Send formatted Markdown/HTML status notifications, summaries, and alerts to mobile users.",
            input_model=ChannelMessageDispatchInput,
            handler=_channel_message_dispatch,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_apk_deliver",
            title="Deliver APK to Mobile Chat",
            description="Upload and deliver compiled, patched, and signed .apk binaries directly into mobile chat.",
            input_model=ChannelApkDeliverInput,
            handler=_channel_apk_deliver,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_intensity_configure",
            title="Configure Notification Cadence",
            description="Configure notification cadence (start/end, 1m, 2m, 5m, 10m intervals, or custom minutes).",
            input_model=ChannelIntensityConfigureInput,
            handler=_channel_intensity_configure,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_intensity_get",
            title="Get Notification Cadence",
            description="Query active message cadence mode, last ping timestamp, and throttle metrics.",
            input_model=ChannelIntensityGetInput,
            handler=_channel_intensity_get,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_pair_whatsapp",
            title="Generate WhatsApp QR Code",
            description="Initialize and render QR code pairing for local WhatsApp Web Baileys bridge.",
            input_model=ChannelPairWhatsappInput,
            handler=_channel_pair_whatsapp,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_test_ping",
            title="Test Mobile Channel Ping",
            description="Transmit an end-to-end verification ping to configured Telegram and WhatsApp channels.",
            input_model=ChannelTestPingInput,
            handler=_channel_test_ping,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_whitelist_manage",
            title="Manage Mobile Whitelist",
            description="Register and revoke authorized mobile sender IDs and phone numbers.",
            input_model=ChannelWhitelistManageInput,
            handler=_channel_whitelist_manage,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_file_deliver",
            title="Deliver File/Image/Report Over Mobile Channel",
            description="Deliver an APK, UI design screenshot/image, or report document to Telegram or WhatsApp.",
            input_model=ChannelFileDeliverInput,
            handler=_channel_file_deliver,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="channel_progress_report",
            title="Broadcast Progress Report to Mobile Channels",
            description="Send a structured live progress report (with optional APK, screenshot, or report attachment) over WhatsApp/Telegram.",
            input_model=ChannelProgressReportInput,
            handler=_channel_progress_report,
            family="channels",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
