"""Artifact ingestion and inventory tools."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from raa.policy.scopes import NETWORK_FETCH
from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolInput,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import CORE, MINIMAL
from raa.services.android.source_fetcher import (
    download_upstream_apk,
    resolve_upstream_release,
)
from raa.services.inspection import list_archive_members


class ArtifactIngestInput(ToolInput):
    project_id: str = Field(description="Project that will own the artifact.")
    path: str = Field(
        description=("Path to an APK/AAB/APKS/XAPK inside the workspace or an allowed input root.")
    )


class ArtifactGetInfoInput(ToolInput):
    project_id: str
    artifact_id: str


class ArtifactListInput(ToolInput):
    project_id: str
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ArtifactListFilesInput(ToolInput):
    project_id: str
    artifact_id: str
    pattern: str | None = Field(
        default=None,
        max_length=300,
        description="Optional case-insensitive glob such as 'lib/*/*.so'.",
    )
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class PlayStoreAppInfoInput(ToolInput):
    package_or_url: str = Field(
        description="Android package ID (e.g. com.example.app) or play.google.com app URL."
    )
    lang: str = Field(default="en", max_length=16, description="Store listing language code.")
    country: str = Field(default="us", max_length=16, description="Store listing country code.")


class PlayStoreDownloadAppInput(ToolInput):
    package_or_url: str = Field(
        description="Android package ID (e.g. com.example.app) or play.google.com app URL."
    )
    project_id: str | None = Field(
        default=None,
        description="Project ID to auto-ingest the downloaded APK/APKS into.",
    )
    provider: Literal["auto", "avd", "adb", "apkeep", "gplaycli"] = Field(
        default="auto",
        description=(
            "Download provider: 'auto' (prefers AVD Manager + Play Store), 'avd', "
            "'adb', 'apkeep', or 'gplaycli'."
        ),
    )
    avd_name: str | None = Field(
        default=None,
        description="Optional AVD name from AVD Manager to boot and install from Play Store.",
    )
    headless: bool = Field(
        default=False,
        description="Launch the AVD emulator headlessly (-no-window) when booting a new AVD.",
    )
    boot_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        description="Maximum seconds to wait for the AVD to finish booting.",
    )
    install_timeout_seconds: float = Field(
        default=180.0,
        ge=10.0,
        le=900.0,
        description="Maximum seconds to wait for Google Play Store to install the app on the AVD.",
    )
    auto_tap_install: bool = Field(
        default=True,
        description="Automatically tap the Play Store 'Install' button via UIAutomator on the AVD.",
    )
    version_code: int | None = Field(
        default=None,
        ge=1,
        description="Optional specific Android versionCode to request (apkeep).",
    )
    split_apk: bool = Field(
        default=False,
        description="Request split APKs when supported by the provider.",
    )
    device_serial: str | None = Field(
        default=None,
        description="Optional ADB/emulator device serial (e.g. emulator-5554).",
    )
    email: str | None = Field(
        default=None,
        description="Optional Google account email for apkeep (falls back to RAA_PLAY_EMAIL).",
    )
    aas_token: str | None = Field(
        default=None,
        description="Optional Google AAS token for apkeep (falls back to RAA_PLAY_AAS_TOKEN).",
    )
    oauth_token: str | None = Field(
        default=None,
        description="Optional Google OAuth token for apkeep (falls back to RAA_PLAY_OAUTH_TOKEN).",
    )
    apkeep_source: Literal["google-play", "apk-pure", "f-droid", "huawei-app-gallery"] = Field(
        default="google-play",
        description="apkeep download source when using apkeep (defaults to 'google-play').",
    )
    auto_ingest: bool = Field(
        default=True,
        description="Automatically ingest the downloaded APK/APKS into project_id.",
    )


class ApkeepDownloadAppInput(ToolInput):
    package_or_url: str = Field(
        description="Android package ID (e.g. com.example.app) or play.google.com app URL."
    )
    project_id: str | None = Field(
        default=None,
        description="Project ID to auto-ingest the downloaded APK/APKS into.",
    )
    source: Literal["google-play", "apk-pure", "f-droid", "huawei-app-gallery"] = Field(
        default="google-play",
        description="apkeep download source; defaults to 'google-play' (first priority).",
    )
    version_code: int | None = Field(
        default=None,
        ge=1,
        description="Optional specific Android versionCode to request.",
    )
    split_apk: bool = Field(
        default=False,
        description="Request split APKs when supported.",
    )
    email: str | None = Field(
        default=None,
        description="Google account email for google-play (falls back to RAA_PLAY_EMAIL).",
    )
    aas_token: str | None = Field(
        default=None,
        description="Google AAS token for google-play (falls back to RAA_PLAY_AAS_TOKEN).",
    )
    oauth_token: str | None = Field(
        default=None,
        description="Google OAuth token for google-play (falls back to RAA_PLAY_OAUTH_TOKEN).",
    )
    auto_ingest: bool = Field(
        default=True,
        description="Automatically ingest the downloaded APK/APKS into project_id.",
    )


async def _artifact_ingest(ctx: ToolContext, args: ArtifactIngestInput) -> ToolOutcome:
    ingested = ctx.runtime.artifacts.ingest_path(args.project_id, args.path)
    return ToolOutcome(
        data=ingested.artifact,
        evidence_ids=[record.id for record in ingested.evidence],
    )


async def _artifact_get_info(ctx: ToolContext, args: ArtifactGetInfoInput) -> ToolOutcome:
    artifact = ctx.runtime.artifacts.get_or_raise(args.project_id, args.artifact_id)
    return ToolOutcome(data=artifact)


async def _artifact_list(ctx: ToolContext, args: ArtifactListInput) -> ToolOutcome:
    artifacts = ctx.runtime.artifacts.list(
        args.project_id,
        limit=args.limit,
        offset=args.offset,
    )
    return ToolOutcome(
        data={
            "items": [artifact.model_dump(mode="json") for artifact in artifacts],
            "count": len(artifacts),
            "limit": args.limit,
            "offset": args.offset,
        }
    )


async def _artifact_list_files(
    ctx: ToolContext,
    args: ArtifactListFilesInput,
) -> ToolOutcome:
    artifact = ctx.runtime.artifacts.get_or_raise(args.project_id, args.artifact_id)
    path = ctx.runtime.artifacts.path_for(artifact)
    items, total = list_archive_members(
        path,
        pattern=args.pattern,
        limit=args.limit,
        offset=args.offset,
        max_entries=ctx.runtime.settings.max_archive_entries,
    )
    return ToolOutcome(
        data={
            "artifact_id": artifact.id,
            "items": items,
            "total": total,
            "limit": args.limit,
            "offset": args.offset,
        }
    )


async def _playstore_app_info(ctx: ToolContext, args: PlayStoreAppInfoInput) -> ToolOutcome:
    info = ctx.runtime.playstore.fetch_app_info(
        args.package_or_url,
        lang=args.lang,
        country=args.country,
    )
    return ToolOutcome(data=info)


async def _playstore_download_app(
    ctx: ToolContext,
    args: PlayStoreDownloadAppInput,
) -> ToolOutcome:
    result = ctx.runtime.playstore.download_app(
        args.package_or_url,
        project_id=args.project_id,
        provider=args.provider,
        avd_name=args.avd_name,
        headless=args.headless,
        boot_timeout_seconds=args.boot_timeout_seconds,
        install_timeout_seconds=args.install_timeout_seconds,
        auto_tap_install=args.auto_tap_install,
        version_code=args.version_code,
        split_apk=args.split_apk,
        device_serial=args.device_serial,
        email=args.email,
        aas_token=args.aas_token,
        oauth_token=args.oauth_token,
        apkeep_source=args.apkeep_source,
        auto_ingest=args.auto_ingest,
    )
    return ToolOutcome(
        data=result,
        evidence_ids=list(result.get("evidence_ids", [])),
    )


async def _apkeep_download_app(
    ctx: ToolContext,
    args: ApkeepDownloadAppInput,
) -> ToolOutcome:
    result = ctx.runtime.playstore.download_with_apkeep(
        args.package_or_url,
        project_id=args.project_id,
        source=args.source,
        version_code=args.version_code,
        split_apk=args.split_apk,
        email=args.email,
        aas_token=args.aas_token,
        oauth_token=args.oauth_token,
        auto_ingest=args.auto_ingest,
    )
    return ToolOutcome(
        data=result,
        evidence_ids=list(result.get("evidence_ids", [])),
    )


class ApkFetchUpstreamInput(ToolInput):
    project_id: str = Field(description="Project ID owning the upstream fetch.")
    provider: Literal["github", "gitlab", "fdroid"] = Field(
        description="Upstream release provider (Obtainium-inspired)."
    )
    identifier: str = Field(
        min_length=1,
        description="Repository slug (owner/repo) for GitHub/GitLab or package ID for F-Droid.",
    )
    download: bool = Field(
        default=False,
        description="When true, downloads the resolved APK into the project's workspace.",
    )


async def _apk_fetch_upstream(ctx: ToolContext, args: ApkFetchUpstreamInput) -> ToolOutcome:
    release = await resolve_upstream_release(args.provider, args.identifier)
    downloaded_path: str | None = None
    if args.download and release.get("download_url"):
        filename = release.get("asset_name") or "upstream.apk"
        dest = ctx.runtime.workspace.root / "projects" / args.project_id / "upstream" / filename
        await download_upstream_apk(str(release["download_url"]), dest)
        downloaded_path = str(dest)
    return ToolOutcome(
        data={
            **release,
            "downloaded": downloaded_path is not None,
            "downloaded_path": downloaded_path,
        }
    )


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="artifact_ingest",
            title="Ingest artifact",
            description=(
                "Copy an APK/AAB/APKS/XAPK into the project workspace, hash it, "
                "classify the container and record evidence. Paths outside allowed "
                "input roots are rejected."
            ),
            input_model=ArtifactIngestInput,
            handler=_artifact_ingest,
            family="artifacts",
            profiles=MINIMAL,
            scopes=frozenset({"project.write", "static.read"}),
            annotations=ToolAnnotations(
                read_only=False,
                destructive=False,
                idempotent=False,
            ),
        )
    )
    registry.register(
        ToolSpec(
            name="artifact_get_info",
            title="Get artifact info",
            description="Return hash, size, container type and storage metadata for an artifact.",
            input_model=ArtifactGetInfoInput,
            handler=_artifact_get_info,
            family="artifacts",
            profiles=MINIMAL,
            scopes=frozenset({"project.read"}),
            annotations=ToolAnnotations(read_only=True),
        )
    )
    registry.register(
        ToolSpec(
            name="artifact_list",
            title="List artifacts",
            description="List artifacts in a project.",
            input_model=ArtifactListInput,
            handler=_artifact_list,
            family="artifacts",
            profiles=CORE,
            scopes=frozenset({"project.read"}),
            annotations=ToolAnnotations(read_only=True),
        )
    )
    registry.register(
        ToolSpec(
            name="artifact_list_files",
            title="List artifact files",
            description=(
                "List archive members with sizes and compression metadata. "
                "No extraction or path traversal is permitted."
            ),
            input_model=ArtifactListFilesInput,
            handler=_artifact_list_files,
            family="artifacts",
            profiles=CORE,
            scopes=frozenset({"project.read", "static.read"}),
            annotations=ToolAnnotations(read_only=True),
        )
    )
    registry.register(
        ToolSpec(
            name="playstore_app_info",
            title="Get Google Play Store app info",
            description=(
                "Fetch public Google Play Store listing metadata (title, description, "
                "icon URL, store URL) for a package ID or play.google.com URL."
            ),
            input_model=PlayStoreAppInfoInput,
            handler=_playstore_app_info,
            family="artifacts",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="playstore_download_app",
            title="Download Google Play Store app",
            description=(
                "Download an APK/APKS/XAPK from Google Play via AVD Manager + Play Store "
                "(first priority), ADB, apkeep, or gplaycli, and optionally ingest it into a project."
            ),
            input_model=PlayStoreDownloadAppInput,
            handler=_playstore_download_app,
            family="artifacts",
            profiles=CORE,
            scopes=frozenset({"project.write", "static.read"}),
            annotations=ToolAnnotations(
                read_only=False,
                destructive=False,
                idempotent=False,
            ),
        )
    )
    registry.register(
        ToolSpec(
            name="apkeep_download_app",
            title="Download app via efforg/apkeep",
            description=(
                "Download an APK/APKS/XAPK using EFF apkeep (defaults to google-play as first "
                "priority; also supports apk-pure, f-droid, and huawei-app-gallery) and optionally ingest it."
            ),
            input_model=ApkeepDownloadAppInput,
            handler=_apkeep_download_app,
            family="artifacts",
            profiles=CORE,
            scopes=frozenset({"project.write", "static.read"}),
            annotations=ToolAnnotations(
                read_only=False,
                destructive=False,
                idempotent=False,
            ),
        )
    )
    registry.register(
        ToolSpec(
            name="apk_fetch_upstream",
            title="Resolve & Fetch Upstream APK Release",
            description=(
                "Resolve latest APK release metadata from GitHub, GitLab, or F-Droid (Obtainium-inspired) "
                "and optionally download the APK into the project workspace."
            ),
            input_model=ApkFetchUpstreamInput,
            handler=_apk_fetch_upstream,
            family="artifacts",
            profiles=CORE,
            scopes=frozenset({NETWORK_FETCH}),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
