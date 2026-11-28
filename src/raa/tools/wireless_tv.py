"""Wireless Device Gateway & Android TV Studio MCP tools."""

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


class WirelessDeviceConnectInput(BaseModel):
    """Parameters to connect or pair with an Android device over Wi-Fi."""

    host: str = Field(description="Target device IP address.")
    port: int = Field(default=5555, ge=1, le=65535, description="ADB connection port.")
    pairing_code: str | None = Field(
        default=None, description="Android 11+ TLS pairing code if pairing."
    )
    pairing_port: int | None = Field(
        default=None, ge=1, le=65535, description="Pairing port if pairing."
    )


class WirelessDeviceStatusInput(BaseModel):
    """Parameters to check wireless device connection and port state."""

    device_id: str | None = Field(
        default=None, description="Target device endpoint (e.g. 192.168.1.100:5555)."
    )


class WirelessApkPushInput(BaseModel):
    """Parameters to push and install an APK over Wi-Fi with resilient chunking."""

    apk_path: str = Field(description="Local path to .apk binary file.")
    device_id: str | None = Field(default=None, description="Target device endpoint.")
    remote_dest: str = Field(
        default="/data/local/tmp/target_app.apk", description="Device destination path."
    )
    chunk_size: int = Field(
        default=32768, ge=1024, le=1048576, description="Chunk transfer size in bytes."
    )


class TvUiRedesignInput(BaseModel):
    """Parameters to deconstruct TV UI and synthesize modern Android TV Compose Material 3."""

    target_input: str = Field(
        description="Path to APK, XML layout file, or decompiled package name."
    )
    target_framework: str = Field(
        default="androidx.tv.material3", description="Target UI framework."
    )
    enable_dpad_graph: bool = Field(
        default=True, description="Generate spatial D-pad directional navigation graph."
    )


class VisualScreendiffVerifyInput(BaseModel):
    """Parameters to execute pixel-level visual regression between original and redesigned screens."""

    before_image: str = Field(description="Path to original screenshot image.")
    after_image: str = Field(description="Path to redesigned Compose UI screenshot image.")
    mask_topbar: bool = Field(default=True, description="Mask dynamic clock and Wi-Fi bounds.")
    blur_pii: bool = Field(default=False, description="Blur recognized PII/user text areas.")


class WirelessPerfBenchmarkInput(BaseModel):
    """Parameters to run wireless cold start and memory PSS benchmark."""

    package_name: str = Field(default="com.tv.app", description="Target application package name.")


class AndroidDebloatInspectInput(BaseModel):
    """Parameters to inspect installed Android packages and classify UAD safety tiers."""

    device_id: str = Field(
        default="",
        description="Target ADB device serial or IP:Port (empty for offline UAD catalog).",
    )
    tier_filter: str | None = Field(
        default=None,
        description="Optional UAD tier filter (recommended, advanced, expert, unsafe, protected_system).",
    )


class AndroidDebloatApplyInput(BaseModel):
    """Parameters to preview or apply rootless ADB debloating/restoration with undo scripts."""

    packages: list[str] = Field(description="Package names to disable or restore.")
    device_id: str = Field(default="", description="Target ADB device serial or IP:Port.")
    dry_run: bool = Field(
        default=True, description="Preview planned actions and impact before mutating device."
    )
    allow_expert: bool = Field(default=False, description="Allow disabling 'expert' tier packages.")
    restore: bool = Field(
        default=False, description="Restore (pm enable) instead of disabling packages."
    )


async def _wireless_device_connect(
    ctx: ToolContext, args: WirelessDeviceConnectInput
) -> ToolOutcome:
    if args.pairing_code and args.pairing_port:
        res = ctx.runtime.wireless_gateway.pair_device(
            host=args.host,
            pairing_port=args.pairing_port,
            pairing_code=args.pairing_code,
        )
    else:
        res = ctx.runtime.wireless_gateway.connect_device(host=args.host, port=args.port)
    return ToolOutcome(data=res)


async def _wireless_device_status(ctx: ToolContext, args: WirelessDeviceStatusInput) -> ToolOutcome:
    res = ctx.runtime.wireless_gateway.get_device_status(device_id=args.device_id)
    return ToolOutcome(data=res)


async def _wireless_apk_push(ctx: ToolContext, args: WirelessApkPushInput) -> ToolOutcome:
    res = ctx.runtime.wireless_gateway.push_apk_resilient(
        apk_path=args.apk_path,
        target_device=args.device_id,
        remote_dest=args.remote_dest,
        chunk_size=args.chunk_size,
    )
    return ToolOutcome(data=res)


async def _tv_ui_redesign(ctx: ToolContext, args: TvUiRedesignInput) -> ToolOutcome:
    res = ctx.runtime.tv_studio.redesign_tv_ui(
        target_input=args.target_input,
        target_framework=args.target_framework,
        enable_dpad_graph=args.enable_dpad_graph,
    )
    return ToolOutcome(data=res)


async def _visual_screendiff_verify(
    ctx: ToolContext, args: VisualScreendiffVerifyInput
) -> ToolOutcome:
    res = ctx.runtime.tv_studio.verify_screendiff(
        before_image=args.before_image,
        after_image=args.after_image,
        mask_topbar=args.mask_topbar,
        blur_pii=args.blur_pii,
    )
    return ToolOutcome(data=res)


async def _wireless_perf_benchmark(
    ctx: ToolContext, args: WirelessPerfBenchmarkInput
) -> ToolOutcome:
    res = ctx.runtime.tv_studio.benchmark_performance(package_name=args.package_name)
    return ToolOutcome(data=res)


async def _android_debloat_inspect(
    ctx: ToolContext, args: AndroidDebloatInspectInput
) -> ToolOutcome:
    res = ctx.runtime.debloat.inspect_packages(
        device_id=args.device_id,
        tier_filter=args.tier_filter,
    )
    return ToolOutcome(data=res)


async def _android_debloat_apply(ctx: ToolContext, args: AndroidDebloatApplyInput) -> ToolOutcome:
    res = ctx.runtime.debloat.apply_debloat(
        packages=args.packages,
        device_id=args.device_id,
        dry_run=args.dry_run,
        allow_expert=args.allow_expert,
        restore=args.restore,
    )
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="wireless_device_connect",
            title="Connect Wireless Android Device",
            description="Discover, pair, and connect to Android phones, tablets, and TVs over local Wi-Fi without USB cables.",
            input_model=WirelessDeviceConnectInput,
            handler=_wireless_device_connect,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="wireless_device_status",
            title="Check Wireless Device Status",
            description="Check connection state, IP, battery, model, and active Wi-Fi debugging port.",
            input_model=WirelessDeviceStatusInput,
            handler=_wireless_device_status,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="wireless_apk_push",
            title="Push APK over Wireless",
            description="Resilient base64-chunked transfer and installation of APKs over Wi-Fi with MD5 verification.",
            input_model=WirelessApkPushInput,
            handler=_wireless_apk_push,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="tv_ui_redesign",
            title="Redesign Android TV UI",
            description="Extract, deconstruct, and redesign Android TV/Google TV 10-foot interfaces into modern Android TV Compose Material 3 or React Native TV.",
            input_model=TvUiRedesignInput,
            handler=_tv_ui_redesign,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="visual_screendiff_verify",
            title="Verify Screen Parity Diff",
            description="Pixel-level visual diffing between original vs reconstructed screens with coordinate masking and PII blurring.",
            input_model=VisualScreendiffVerifyInput,
            handler=_visual_screendiff_verify,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="wireless_perf_benchmark",
            title="Benchmark Wireless TV Performance",
            description="Capture cold start time, memory PSS, and Perfetto trace slicing over Wi-Fi.",
            input_model=WirelessPerfBenchmarkInput,
            handler=_wireless_perf_benchmark,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="android_debloat_inspect",
            title="Inspect Android Packages (UAD Safety Tiers)",
            description="Inspect installed packages on Android phones, tablets, or TVs via rootless ADB and classify them with Universal Android Debloater (UAD) safety tiers and removal impact.",
            input_model=AndroidDebloatInspectInput,
            handler=_android_debloat_inspect,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="android_debloat_apply",
            title="Apply or Restore Rootless Android Debloat",
            description="Preview (dry_run) or safely disable bloatware via rootless ADB (pm disable-user --user 0) with automatic JSON backup and .sh/.ps1 undo scripts.",
            input_model=AndroidDebloatApplyInput,
            handler=_android_debloat_apply,
            family="wireless_tv",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
