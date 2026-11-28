"""UI reconstruction, screen graph, asset inventory, and runtime capture tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import DYNAMIC, UI
from raa.services.asset_studio import (
    generate_adaptive_icon_suite,
    generate_notification_silhouette,
    generate_play_store_banner,
)
from raa.services.ax_tree_pruner import fuse_ui_tree_and_screenshot, prune_ax_tree
from raa.services.semantic_compose import diff_compose_parity, modernize_xml_to_compose


# Input schemas
class UIJobInput(BaseModel):
    project_id: str = Field(min_length=1, description="Target project ID.")
    job_id: str = Field(min_length=1, description="Completed analysis job ID.")


class UIListScreensInput(UIJobInput):
    limit: int = Field(default=50, ge=1, le=500, description="Page limit.")
    offset: int = Field(default=0, ge=0, description="Offset index.")
    filter_runtime: bool | None = Field(
        default=None, description="Filter by runtime vs static screens."
    )


class UIGetScreenInput(UIJobInput):
    screen_id: str = Field(min_length=1, description="Target screen identifier.")


class UIListAssetsInput(UIJobInput):
    kind: str | None = Field(
        default=None,
        description="Filter by kind: layout, drawable, font, string, color, theme, navigation.",
    )
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class UIGetHierarchyInput(UIJobInput):
    screen_id: str | None = Field(default=None, description="Screen ID to retrieve hierarchy for.")
    capture_id: str | None = Field(default=None, description="Direct capture ID.")


class UIGetOCRInput(UIJobInput):
    screen_id: str | None = Field(default=None, description="Screen ID to retrieve OCR for.")
    capture_id: str | None = Field(default=None, description="Direct capture ID.")


class UIGetSourceCorrelationsInput(UIJobInput):
    screen_id: str | None = Field(default=None, description="Filter correlations for screen.")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class UIStartCaptureSessionInput(BaseModel):
    project_id: str = Field(min_length=1, description="Target project ID.")
    device_id: str = Field(default="emulator-5554", description="ADB device or emulator ID.")
    model: str = Field(default="Pixel_7", description="Device model name.")
    package_name: str | None = Field(default=None, description="Target package name.")


class UICaptureScreenshotInput(UIJobInput):
    session_id: str | None = Field(default=None, description="Optional active session ID.")
    device_id: str = Field(default="emulator-5554", description="Connected ADB device ID.")
    custom_hierarchy: str | None = Field(
        default=None, description="Optional custom or mock hierarchy XML."
    )


class UIRecordTransitionInput(BaseModel):
    project_id: str = Field(min_length=1, description="Target project ID.")
    source_screen_id: str = Field(min_length=1, description="Source screen ID.")
    target_screen_id: str = Field(min_length=1, description="Target screen ID.")
    trigger: str = Field(default="tap", description="Trigger type: tap, gesture, intent, back.")
    guard: str | None = Field(default=None, description="Optional state guard: auth, flag.")
    action_script: str | None = Field(default=None, description="Scriptable action description.")


class UICompareScreensInput(UIJobInput):
    screen_a_id: str = Field(min_length=1, description="First screen ID.")
    screen_b_id: str = Field(min_length=1, description="Second screen ID.")


class UIGetCoverageInput(UIJobInput):
    pass


class UIToCodeInput(UIJobInput):
    screen_id: str = Field(min_length=1, description="Screen ID to export.")
    target: Literal["compose", "flutter", "react_native", "html"] = Field(
        default="compose", description="Target framework export."
    )


class UIRuntimeCaptureInput(BaseModel):
    project_id: str = Field(min_length=1, description="Target project identifier.")
    artifact_id: str | None = Field(
        default=None, description="Optional target artifact identifier."
    )
    device_id: str | None = Field(default=None, description="Optional target device ID.")
    activity_name: str | None = Field(default=None, description="Optional activity name to launch.")
    screen_name: str | None = Field(default=None, description="Optional screen name.")


class UIWebviewInspectInput(BaseModel):
    project_id: str = Field(min_length=1, description="Target project identifier.")
    device_id: str | None = Field(default=None, description="Optional target device ID.")
    cdp_port: int = Field(default=9222, description="CDP remote debugging port.")
    target_filter: str | None = Field(default=None, description="Optional URL or title filter.")


class UIRedesignGenerateInput(BaseModel):
    project_id: str = Field(min_length=1, description="Target project identifier.")
    screen_id: str = Field(min_length=1, description="Target screen identifier.")
    target_framework: Literal["compose", "react-native", "tailwind"] = Field(
        default="compose", description="Target framework: compose, react-native, tailwind."
    )
    theme_mode: Literal["light", "dark", "system"] = Field(
        default="system", description="Theme mode: light, dark, system."
    )
    design_system: dict[str, Any] | None = Field(
        default=None, description="Optional design token overrides."
    )


class UIVisualCompareInput(BaseModel):
    project_id: str = Field(min_length=1, description="Target project identifier.")
    original_screenshot_path: str | None = Field(
        default=None, description="Original screenshot path."
    )
    redesigned_screenshot_path: str | None = Field(
        default=None, description="Redesigned screenshot path."
    )
    original_screen_id: str | None = Field(default=None, description="Original screen ID.")
    redesigned_screen_id: str | None = Field(default=None, description="Redesigned screen ID.")
    tolerance: float = Field(default=0.1, ge=0.0, le=1.0, description="Visual diff tolerance.")


class UiAxTreePruneInput(BaseModel):
    """Parameters to prune and compress Android Accessibility / layout tree."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    hierarchy_xml: str | None = Field(
        default=None, description="Raw UIAutomator or layout hierarchy XML."
    )
    raw_xml: str | None = Field(default=None, description="Alias for raw hierarchy XML.")
    min_text_len: int = Field(default=1, ge=0, description="Minimum text length for inclusion.")


class UiIconGenerateInput(BaseModel):
    """Parameters to generate full Android 8+ Adaptive Icon suite and monochrome tint layers."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    icon_name: str = Field(default="ic_launcher", description="Base icon file name.")
    background_color: str = Field(
        default="#1A73E8", description="Background hex color code for adaptive icon."
    )
    foreground_vector_xml: str | None = Field(
        default=None, description="Optional Android Vector Drawable XML string for foreground."
    )
    output_dir: str | None = Field(
        default=None, description="Optional destination directory to save generated XMLs."
    )


class UiBannerGenerateInput(BaseModel):
    """Parameters to generate 1024x500 Play Store feature graphic banner."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    app_title: str = Field(default="My App", description="Primary application title.")
    tagline: str = Field(default="Modern Mobile Experience", description="Subheading tagline.")
    primary_color: str = Field(default="#0D47A1", description="Primary gradient start hex color.")
    secondary_color: str = Field(default="#1976D2", description="Secondary gradient end hex color.")
    accent_color: str = Field(default="#00E676", description="Accent brand hex color.")
    output_path: str | None = Field(
        default=None, description="Optional destination path for generated SVG banner."
    )


class UiNotificationIconGenerateInput(BaseModel):
    """Parameters to generate Android 13+ status bar monochrome notification silhouette."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    name: str = Field(
        default="ic_stat_notification", description="Notification icon drawable name."
    )
    source_vector_path: str | None = Field(
        default=None, description="Optional SVG path data string for notification silhouette."
    )
    output_dir: str | None = Field(
        default=None, description="Optional destination directory to save generated XML."
    )


class UiXmlSemanticModernizeInput(BaseModel):
    """Parameters to modernize legacy Android XML layout into Material 3 Jetpack Compose."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    xml_content: str = Field(min_length=1, description="Raw Android layout XML content.")
    target_package: str = Field(default="com.example.ui", description="Kotlin package name.")
    screen_name: str = Field(default="ModernizedScreen", description="Composable function name.")
    enable_edge_to_edge: bool = Field(
        default=True, description="Inject WindowInsets safeDrawingPadding for Android 15/16."
    )


class UiParityDiffInput(BaseModel):
    """Parameters to evaluate structural and semantic parity between XML and Compose."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    xml_element_count: int = Field(default=5, ge=1, description="Count of original XML views.")
    compose_element_count: int = Field(default=5, ge=1, description="Count of Compose elements.")
    has_text_parity: bool = Field(default=True, description="Whether text labels match.")
    has_click_parity: bool = Field(default=True, description="Whether interaction targets match.")


class UiVisualGroundingNavigateInput(BaseModel):
    """Parameters to resolve natural language query to bounding box and touch coordinates."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    target_query: str = Field(
        min_length=1, description="Natural language target (e.g., 'login button', 'skip')."
    )
    screen_width: int = Field(default=1080, ge=320, le=4096, description="Screen width in pixels.")
    screen_height: int = Field(
        default=2400, ge=480, le=4096, description="Screen height in pixels."
    )
    action_type: str = Field(
        default="tap", description="Touch action type: tap, swipe, long_press."
    )


class UiNotificationIconAuditInput(BaseModel):
    """Parameters to audit notification bar icon compliance, contrast, and metadata."""

    apk_path: str | None = Field(default=None, description="Optional path to target APK file.")
    res_dir: str | None = Field(default=None, description="Optional path to app res/ directory.")
    manifest_xml: str | None = Field(
        default=None, description="Optional AndroidManifest.xml raw content."
    )


# Handlers
def _get_archive_bytes(ctx: ToolContext, project_id: str, artifact_id: str) -> bytes | None:
    try:
        artifact = ctx.runtime.artifacts.get_or_raise(project_id, artifact_id)
        path = ctx.runtime.artifacts.path_for(artifact)
        data: bytes = path.read_bytes()
        return data
    except Exception:
        return None


async def _ui_list_screens(ctx: ToolContext, input_data: UIListScreensInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    screens, _ = ctx.runtime.ui.get_all_screens(input_data.project_id, report, archive_bytes)

    if input_data.filter_runtime is not None:
        screens = [s for s in screens if s.is_runtime == input_data.filter_runtime]

    total = len(screens)
    paged = screens[input_data.offset : input_data.offset + input_data.limit]
    next_offset = (
        input_data.offset + input_data.limit
        if input_data.offset + input_data.limit < total
        else None
    )

    return ToolOutcome(
        data={
            "project_id": input_data.project_id,
            "job_id": input_data.job_id,
            "total": total,
            "offset": input_data.offset,
            "limit": input_data.limit,
            "next_offset": next_offset,
            "items": [s.model_dump() for s in paged],
        },
        evidence_ids=report.evidence_ids,
    )


async def _ui_get_screen(ctx: ToolContext, input_data: UIGetScreenInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    screen = ctx.runtime.ui.get_screen(
        input_data.project_id, report, input_data.screen_id, archive_bytes
    )
    return ToolOutcome(
        data=screen.model_dump(), evidence_ids=screen.evidence_ids or report.evidence_ids
    )


async def _ui_list_assets(ctx: ToolContext, input_data: UIListAssetsInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    inventory = ctx.runtime.ui.list_assets(report, kind_filter=input_data.kind)

    total = inventory.total_count
    paged = inventory.assets[input_data.offset : input_data.offset + input_data.limit]
    next_offset = (
        input_data.offset + input_data.limit
        if input_data.offset + input_data.limit < total
        else None
    )

    return ToolOutcome(
        data={
            "project_id": input_data.project_id,
            "total_count": total,
            "counts_by_kind": inventory.counts_by_kind,
            "offset": input_data.offset,
            "limit": input_data.limit,
            "next_offset": next_offset,
            "assets": [a.model_dump() for a in paged],
        },
        evidence_ids=report.evidence_ids,
    )


async def _ui_get_hierarchy(ctx: ToolContext, input_data: UIGetHierarchyInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    screen_id = input_data.screen_id or "screen-static-root"
    tree = ctx.runtime.ui.get_hierarchy_for_screen(
        input_data.project_id,
        report,
        screen_id=screen_id,
        capture_id=input_data.capture_id,
        archive_bytes=archive_bytes,
    )
    return ToolOutcome(data=tree.model_dump(), evidence_ids=report.evidence_ids)


async def _ui_get_ocr(ctx: ToolContext, input_data: UIGetOCRInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    screen_id = input_data.screen_id or "screen-static-root"
    ocr = ctx.runtime.ui.get_ocr_for_screen(
        input_data.project_id,
        report,
        screen_id=screen_id,
        capture_id=input_data.capture_id,
        archive_bytes=archive_bytes,
    )
    return ToolOutcome(data=ocr.model_dump(), evidence_ids=report.evidence_ids)


async def _ui_get_source_correlations(
    ctx: ToolContext, input_data: UIGetSourceCorrelationsInput
) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    correlations = ctx.runtime.ui.get_source_correlations(
        input_data.project_id, report, screen_id=input_data.screen_id, archive_bytes=archive_bytes
    )

    total = len(correlations)
    paged = correlations[input_data.offset : input_data.offset + input_data.limit]
    next_offset = (
        input_data.offset + input_data.limit
        if input_data.offset + input_data.limit < total
        else None
    )

    return ToolOutcome(
        data={
            "project_id": input_data.project_id,
            "total": total,
            "offset": input_data.offset,
            "limit": input_data.limit,
            "next_offset": next_offset,
            "correlations": [c.model_dump() for c in paged],
        },
        evidence_ids=report.evidence_ids,
    )


async def _ui_start_capture_session(
    ctx: ToolContext, input_data: UIStartCaptureSessionInput
) -> ToolOutcome:
    session = ctx.runtime.ui.start_capture_session(
        project_id=input_data.project_id,
        device_id=input_data.device_id,
        model=input_data.model,
        package_name=input_data.package_name,
    )
    return ToolOutcome(data=session)


async def _ui_capture_screenshot(
    ctx: ToolContext, input_data: UICaptureScreenshotInput
) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    capture = ctx.runtime.ui.capture_screenshot(
        project_id=input_data.project_id,
        artifact_id=report.artifact_id,
        session_id=input_data.session_id,
        device_id=input_data.device_id,
        custom_hierarchy=input_data.custom_hierarchy,
    )
    return ToolOutcome(data=capture.model_dump(), evidence_ids=report.evidence_ids)


async def _ui_record_transition(
    ctx: ToolContext, input_data: UIRecordTransitionInput
) -> ToolOutcome:
    trans = ctx.runtime.ui.record_transition(
        project_id=input_data.project_id,
        source_screen_id=input_data.source_screen_id,
        target_screen_id=input_data.target_screen_id,
        trigger=input_data.trigger,
        guard=input_data.guard,
        action_script=input_data.action_script,
    )
    return ToolOutcome(data=trans.model_dump(), evidence_ids=trans.evidence_ids)


async def _ui_compare_screens(ctx: ToolContext, input_data: UICompareScreensInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    comparison = ctx.runtime.ui.compare(
        input_data.project_id,
        report,
        input_data.screen_a_id,
        input_data.screen_b_id,
        archive_bytes=archive_bytes,
    )
    return ToolOutcome(data=comparison.model_dump(), evidence_ids=report.evidence_ids)


async def _ui_get_coverage(ctx: ToolContext, input_data: UIGetCoverageInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    coverage = ctx.runtime.ui.get_coverage(
        input_data.project_id, report, archive_bytes=archive_bytes
    )
    return ToolOutcome(data=coverage.model_dump(), evidence_ids=report.evidence_ids)


async def _ui_to_code(ctx: ToolContext, input_data: UIToCodeInput) -> ToolOutcome:
    report = ctx.runtime.analysis.get_report(input_data.project_id, input_data.job_id)
    archive_bytes = _get_archive_bytes(ctx, report.project_id, report.artifact_id)
    result = ctx.runtime.ui.export_code(
        input_data.project_id,
        report,
        input_data.screen_id,
        target=input_data.target,
        archive_bytes=archive_bytes,
    )
    return ToolOutcome(data=result.model_dump(), evidence_ids=report.evidence_ids)


async def _ui_runtime_capture(ctx: ToolContext, input_data: UIRuntimeCaptureInput) -> ToolOutcome:
    capture = ctx.runtime.ui.capture_runtime_ui(
        project_id=input_data.project_id,
        artifact_id=input_data.artifact_id,
        device_id=input_data.device_id,
        activity_name=input_data.activity_name or input_data.screen_name,
    )
    return ToolOutcome(data=capture.model_dump())


async def _ui_webview_inspect(ctx: ToolContext, input_data: UIWebviewInspectInput) -> ToolOutcome:
    report = ctx.runtime.ui.inspect_webview(
        project_id=input_data.project_id,
        device_id=input_data.device_id,
        cdp_port=input_data.cdp_port,
        target_filter=input_data.target_filter,
    )
    return ToolOutcome(data=report.model_dump())


async def _ui_redesign_generate(
    ctx: ToolContext, input_data: UIRedesignGenerateInput
) -> ToolOutcome:
    redesign = ctx.runtime.ui.redesign_screen(
        project_id=input_data.project_id,
        screen_id=input_data.screen_id,
        target_framework=input_data.target_framework,
        theme_mode=input_data.theme_mode,
        design_system=input_data.design_system,
    )
    return ToolOutcome(data=redesign.model_dump())


async def _ui_visual_compare(ctx: ToolContext, input_data: UIVisualCompareInput) -> ToolOutcome:

    ui_dir = ctx.runtime.ui.get_ui_dir(input_data.project_id)
    orig_path = input_data.original_screenshot_path
    if not orig_path and input_data.original_screen_id:
        p = ui_dir / f"{input_data.original_screen_id}.png"
        if not p.is_file():
            p.write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
        orig_path = str(p)
    if not orig_path:
        p = ui_dir / "screen_orig.png"
        p.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        orig_path = str(p)

    redesign_path = input_data.redesigned_screenshot_path
    if not redesign_path and input_data.redesigned_screen_id:
        p = ui_dir / f"{input_data.redesigned_screen_id}.png"
        if not p.is_file():
            p.write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
        redesign_path = str(p)
    if not redesign_path:
        p = ui_dir / "screen_redesign.png"
        p.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        redesign_path = str(p)

    comparison = ctx.runtime.ui.compare_visual(
        project_id=input_data.project_id,
        original_screenshot_path=orig_path,
        redesigned_screenshot_path=redesign_path,
        tolerance=input_data.tolerance,
    )
    return ToolOutcome(data=comparison.model_dump())


async def _ui_ax_tree_prune(ctx: ToolContext, args: UiAxTreePruneInput) -> ToolOutcome:
    raw_xml = args.raw_xml or args.hierarchy_xml
    if not raw_xml:
        raw_xml = (
            '<hierarchy rotation="0">'
            '<node class="android.widget.FrameLayout" bounds="[0,0][1080,2400]">'
            '<node class="android.widget.LinearLayout" bounds="[0,0][1080,2400]">'
            '<node class="android.widget.TextView" text="Welcome Back" '
            'bounds="[50,100][500,160]" />'
            '<node class="android.widget.EditText" resource-id="com.app:id/username" text="" '
            'clickable="true" editable="true" bounds="[50,200][1030,300]" />'
            '<node class="android.widget.Button" resource-id="com.app:id/submit" text="Log In" '
            'clickable="true" bounds="[50,350][1030,450]" />'
            "</node></node></hierarchy>"
        )
    res = prune_ax_tree(hierarchy_xml=raw_xml, min_text_len=args.min_text_len)
    return ToolOutcome(data=res)


async def _ui_icon_generate(ctx: ToolContext, args: UiIconGenerateInput) -> ToolOutcome:
    res = generate_adaptive_icon_suite(
        name=args.icon_name,
        background_color=args.background_color,
        foreground_vector_xml=args.foreground_vector_xml,
        output_dir=args.output_dir,
    )
    return ToolOutcome(data=res)


async def _ui_banner_generate(ctx: ToolContext, args: UiBannerGenerateInput) -> ToolOutcome:
    res = generate_play_store_banner(
        app_title=args.app_title,
        tagline=args.tagline,
        primary_color=args.primary_color,
        secondary_color=args.secondary_color,
        accent_color=args.accent_color,
        output_path=args.output_path,
    )
    return ToolOutcome(data=res)


async def _ui_notification_icon_generate(
    ctx: ToolContext, args: UiNotificationIconGenerateInput
) -> ToolOutcome:
    res = generate_notification_silhouette(
        name=args.name,
        source_vector_path=args.source_vector_path,
        output_dir=args.output_dir,
    )
    return ToolOutcome(data=res)


async def _ui_xml_semantic_modernize(
    ctx: ToolContext, args: UiXmlSemanticModernizeInput
) -> ToolOutcome:
    res = modernize_xml_to_compose(
        xml_content=args.xml_content,
        target_package=args.target_package,
        screen_name=args.screen_name,
        enable_edge_to_edge=args.enable_edge_to_edge,
    )
    return ToolOutcome(data=res)


async def _ui_parity_diff(ctx: ToolContext, args: UiParityDiffInput) -> ToolOutcome:
    res = diff_compose_parity(
        xml_element_count=args.xml_element_count,
        compose_element_count=args.compose_element_count,
        has_text_parity=args.has_text_parity,
        has_click_parity=args.has_click_parity,
    )
    return ToolOutcome(data=res)


async def _ui_visual_grounding_navigate(
    ctx: ToolContext, args: UiVisualGroundingNavigateInput
) -> ToolOutcome:
    res = ctx.runtime.ui.navigate_grounding(
        target_query=args.target_query,
        screen_width=args.screen_width,
        screen_height=args.screen_height,
        action_type=args.action_type,
    )
    return ToolOutcome(data=res)


async def _ui_notification_icon_audit(
    ctx: ToolContext, args: UiNotificationIconAuditInput
) -> ToolOutcome:
    from raa.services.android.notification_icons import audit_notification_icons

    res = audit_notification_icons(
        apk_path=args.apk_path,
        res_dir=args.res_dir,
        manifest_xml=args.manifest_xml,
    )
    return ToolOutcome(data=res)


def _ui_spec(
    *,
    name: str,
    title: str,
    description: str,
    handler: Any,
    input_model: type[BaseModel],
    profiles: frozenset[str] = UI,
    scopes: frozenset[str] = frozenset({"project.read", "static.read"}),
    read_only: bool = True,
    idempotent: bool = True,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        title=title,
        description=description,
        input_model=input_model,
        handler=handler,
        family="ui",
        profiles=profiles,
        scopes=scopes,
        annotations=ToolAnnotations(read_only=read_only, idempotent=idempotent),
        cost="fast",
    )


class UiTreeScreenshotFuseInput(BaseModel):
    """Parameters to fuse UI accessibility tree bounds with screenshot coordinates."""

    hierarchy_xml: str | None = Field(default=None, description="UIAutomator XML hierarchy.")
    hierarchy_dict: dict[str, Any] | None = Field(
        default=None, description="JSON accessibility hierarchy."
    )
    screen_width: int = Field(default=1080, ge=1, description="Device screen width in pixels.")
    screen_height: int = Field(default=2400, ge=1, description="Device screen height in pixels.")
    screenshot_path: str | None = Field(default=None, description="Optional screenshot path.")


async def _ui_tree_screenshot_fuse(
    ctx: ToolContext, args: UiTreeScreenshotFuseInput
) -> ToolOutcome:
    del ctx
    res = fuse_ui_tree_and_screenshot(
        hierarchy_xml=args.hierarchy_xml,
        hierarchy_dict=args.hierarchy_dict,
        screen_width=args.screen_width,
        screen_height=args.screen_height,
        screenshot_path=args.screenshot_path,
    )
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        _ui_spec(
            name="ui_list_screens",
            title="List UI screens",
            description="List static and observed runtime screens for an analyzed project.",
            handler=_ui_list_screens,
            input_model=UIListScreensInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_get_screen",
            title="Get screen model",
            description="Retrieve detailed screen model with regions, bounds, and provenance.",
            handler=_ui_get_screen,
            input_model=UIGetScreenInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_list_assets",
            title="List UI assets",
            description="Inventory UI assets: layouts, drawables, fonts, strings, themes, and nav.",
            handler=_ui_list_assets,
            input_model=UIListAssetsInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_get_hierarchy",
            title="Get UI hierarchy",
            description="Retrieve UIAutomator hierarchy tree for a screen or capture.",
            handler=_ui_get_hierarchy,
            input_model=UIGetHierarchyInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_get_ocr",
            title="Get OCR extraction",
            description="Retrieve OCR text and bounding box regions for a screen or capture.",
            handler=_ui_get_ocr,
            input_model=UIGetOCRInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_get_source_correlations",
            title="Get source correlations",
            description="Retrieve correlations linking UI components and layouts to DEX code.",
            handler=_ui_get_source_correlations,
            input_model=UIGetSourceCorrelationsInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_start_capture_session",
            title="Start UI capture session",
            description="Start authorized runtime capture session on connected emulator/device.",
            handler=_ui_start_capture_session,
            input_model=UIStartCaptureSessionInput,
            scopes=frozenset({"project.read", "dynamic.device"}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_capture_screenshot",
            title="Capture screen",
            description="Capture current screenshot and UI hierarchy from connected device.",
            handler=_ui_capture_screenshot,
            input_model=UICaptureScreenshotInput,
            scopes=frozenset({"project.read", "dynamic.device"}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_record_transition",
            title="Record transition",
            description="Record an approved navigation action/transition between screens.",
            handler=_ui_record_transition,
            input_model=UIRecordTransitionInput,
            scopes=frozenset({"project.read", "dynamic.device"}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_compare_screens",
            title="Compare screens",
            description="Compare two screens across visual IoU, OCR text, and structural fidelity.",
            handler=_ui_compare_screens,
            input_model=UICompareScreensInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_get_coverage",
            title="Get UI coverage",
            description="Report exploration coverage across discovered, visited, and unreachable.",
            handler=_ui_get_coverage,
            input_model=UIGetCoverageInput,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_to_code",
            title="Export screen to code",
            description="Export screen to Compose, Flutter, React Native, or HTML with fidelity.",
            handler=_ui_to_code,
            input_model=UIToCodeInput,
            scopes=frozenset({"project.read", "export.raw"}),
        )
    )
    registry.register(
        _ui_spec(
            name="ui_runtime_capture",
            title="Capture runtime UI",
            description="Directly capture screenshot and UIAutomator bounds matrix from device.",
            handler=_ui_runtime_capture,
            input_model=UIRuntimeCaptureInput,
            scopes=frozenset({"project.read", "dynamic.device"}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_webview_inspect",
            title="Inspect embedded webview",
            description="Connect to embedded WebView via Chrome DevTools Protocol (CDP port 9222).",
            handler=_ui_webview_inspect,
            input_model=UIWebviewInspectInput,
            scopes=frozenset({"project.read", "dynamic.device"}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_redesign_generate",
            title="Generate clean-room UI redesign",
            description=(
                "Generate modern mobile screen code applying 8pt grid and mobile design system."
            ),
            handler=_ui_redesign_generate,
            input_model=UIRedesignGenerateInput,
            scopes=frozenset({"project.read"}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_visual_compare",
            title="Compare visual screens",
            description="Perform pixel and perceptual visual diff between original and redesign.",
            handler=_ui_visual_compare,
            input_model=UIVisualCompareInput,
            scopes=frozenset({"project.read"}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_ax_tree_prune",
            title="Prune Accessibility Tree for LLM",
            description=(
                "Prune decorative containers and compress Android view hierarchy into "
                "an ultra-compact interactive element map for LLM reasoning."
            ),
            handler=_ui_ax_tree_prune,
            input_model=UiAxTreePruneInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_icon_generate",
            title="Generate Android Adaptive Icon Suite",
            description=(
                "Generate complete Android 8+ Adaptive Icon suite, monochrome tint layer, "
                "round masks, and multi-density mipmaps."
            ),
            handler=_ui_icon_generate,
            input_model=UiIconGenerateInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_banner_generate",
            title="Generate Play Store Feature Graphic Banner",
            description=(
                "Generate exact 1024x500 Google Play Console compliant feature graphic banner "
                "with device mockups and brand typography."
            ),
            handler=_ui_banner_generate,
            input_model=UiBannerGenerateInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_notification_icon_generate",
            title="Generate Notification Silhouette Icon",
            description=(
                "Generate Android 13+ compliant monochrome alpha-only status bar notification icon "
                "and multi-density drawables."
            ),
            handler=_ui_notification_icon_generate,
            input_model=UiNotificationIconGenerateInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_xml_semantic_modernize",
            title="Modernize XML Layout to Compose M3",
            description=(
                "Execute 10-step semantic transformation pipeline from legacy Android XML layout "
                "to idiomatic Material 3 Jetpack Compose with edge-to-edge support."
            ),
            handler=_ui_xml_semantic_modernize,
            input_model=UiXmlSemanticModernizeInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_parity_diff",
            title="Evaluate XML to Compose Parity",
            description=(
                "Evaluate structural, text, and interaction parity between legacy XML layout "
                "and modernized Jetpack Compose Composable function."
            ),
            handler=_ui_parity_diff,
            input_model=UiParityDiffInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_visual_grounding_navigate",
            title="Visual Grounding & Touch Navigation",
            description=(
                "Resolve natural language element queries to precise screen coordinates "
                "on Flutter/Canvas surfaces and synthesize touch dispatch actions."
            ),
            handler=_ui_visual_grounding_navigate,
            input_model=UiVisualGroundingNavigateInput,
            profiles=UI | DYNAMIC,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_notification_icon_audit",
            title="Audit Status Bar Notification Icons & Metadata",
            description=(
                "Audit Android status bar notification icons for monochrome compliance, "
                "contrast ratios against notification shades, and manifest metadata."
            ),
            handler=_ui_notification_icon_audit,
            input_model=UiNotificationIconAuditInput,
            profiles=UI,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _ui_spec(
            name="ui_tree_screenshot_fuse",
            title="Fuse UI Accessibility Tree With Screenshot Coordinates",
            description=(
                "Prune Android/iOS accessibility hierarchies and compute normalized [0..1000] "
                "bounding boxes and pixel tap centers (mobilerun-inspired)."
            ),
            handler=_ui_tree_screenshot_fuse,
            input_model=UiTreeScreenshotFuseInput,
            profiles=UI | DYNAMIC,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
