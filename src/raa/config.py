"""Runtime configuration.

Settings are read from ``RAA_*`` environment variables and an optional
``.env`` file. Paths are resolved lazily so the package can be imported from
any working directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProfileName = Literal["minimal", "core", "full", "dynamic", "api", "ui", "admin", "swarm"]

DEFAULT_PROFILE: ProfileName = "core"


class Settings(BaseSettings):
    """Process-wide settings with safe local defaults."""

    model_config = SettingsConfigDict(
        env_prefix="RAA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "RAA"
    profile: ProfileName = DEFAULT_PROFILE
    workspace: Path = Path(".raa-workspace")

    log_level: str = "INFO"
    log_json: bool = False

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8765, ge=1, le=65535)
    api_token: SecretStr | None = None

    allowed_input_roots: list[Path] = Field(default_factory=list)
    max_input_bytes: int = Field(default=2 * 1024**3, ge=1)
    max_archive_entries: int = Field(default=50_000, ge=1)
    max_uncompressed_bytes: int = Field(default=8 * 1024**3, ge=1)
    max_manifest_bytes: int = Field(default=4 * 1024**2, ge=1024)
    max_resource_bytes: int = Field(default=64 * 1024**2, ge=1024)
    max_dex_bytes: int = Field(default=64 * 1024**2, ge=1024)
    max_dex_instruction_units: int = Field(default=500_000, ge=1024)
    max_dex_references: int = Field(default=200_000, ge=1000)
    analysis_timeout_seconds: float = Field(default=120.0, gt=0)

    engine_execution_enabled: bool = False
    engine_timeout_seconds: float = Field(default=120.0, gt=0)
    engine_max_output_bytes: int = Field(default=8 * 1024**2, ge=1024)
    engine_max_file_bytes: int = Field(default=1024**2, ge=1024)

    admin_enabled: bool = True

    # Setup & Web UI (v4.0.0)
    setup_port: int = Field(default=8765, ge=1, le=65535)
    setup_auto_launch: bool = True
    tools_managed_dir: str = ".raa-workspace/tools"

    # Mobile Channels (Telegram & WhatsApp) (v4.0.0)
    notifications_telegram_enabled: bool = False
    telegram_bot_token: SecretStr | None = None
    telegram_allowed_users: list[str] = Field(default_factory=list)

    notifications_whatsapp_enabled: bool = False
    whatsapp_mode: str = "cloud"  # "cloud" or "baileys"
    whatsapp_phone: str = ""
    whatsapp_api_token: SecretStr | None = None

    # Cadence & Notification Intensity (v4.0.0)
    cadence_mode: str = "interval"  # "start_end", "interval", "milestone", or "adaptive"
    cadence_interval_minutes: int = 5
    cadence_urgent_cve_breakin: bool = True
    send_apk_attachment: bool = True

    # Self-Evolving & Vault Security (v4.0.0)
    self_evolving_enabled: bool = True
    untrusted_content_shield: bool = True
    vault_enabled: bool = True

    # External MCP Mesh & Connectors (v4.0.0)
    mcp_mesh_enabled: bool = True
    mcp_mesh_store: str = ".raa-workspace/mcp_servers.json"
    mcp_mesh_auto_discovery: bool = True

    # Wireless Device Gateway & Android TV Studio (v4.0.0)
    wireless_device_host: str = "192.168.1.100:5555"
    wireless_auto_pair: bool = True
    tv_studio_enabled: bool = True
    tv_compose_target: str = "androidx.tv.material3"
    screendiff_mask_topbar: bool = True

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
        return normalized

    def resolved_workspace(self) -> Path:
        """Absolute workspace path, created on demand by the runtime."""
        return self.workspace.expanduser().resolve()

    @property
    def database_path(self) -> Path:
        return self.resolved_workspace() / "raa.sqlite3"

    def resolved_input_roots(self) -> list[Path]:
        """Directories from which ``artifact_ingest`` may read a file.

        The workspace and current working directory are always allowed. Add
        explicit sample directories with ``RAA_ALLOWED_INPUT_ROOTS``.
        """

        roots = [Path.cwd(), self.resolved_workspace(), *self.allowed_input_roots]
        resolved: list[Path] = []
        for root in roots:
            candidate = root.expanduser().resolve()
            if candidate not in resolved:
                resolved.append(candidate)
        return resolved
