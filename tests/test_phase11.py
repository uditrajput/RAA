"""Tests for Phase 11 production hardening, tamper-evident audit, signatures, tenancy,
and backup.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from raa.errors import LimitExceededError
from raa.runtime import Runtime
from raa.services.audit import AuditService
from raa.services.signing import SigningService
from raa.services.tenancy import TenantQuota
from tests.conftest import make_apk


def test_audit_hash_chain_and_tamper_detection(tmp_path: Path) -> None:
    audit = AuditService(tmp_path)

    # 1. Record series of events
    for i in range(5):
        audit.record(
            tool=f"test_tool_{i}",
            surface="cli",
            profile="core",
            request_id=f"req_{i}",
            project_id=None,
            arguments={"arg": i},
            outcome="ok",
            duration_ms=1.5,
        )

    # 2. Verify clean chain
    res = audit.verify_integrity()
    assert res["valid"] is True
    assert res["records_checked"] == 5
    assert res["tampered"] is False

    # 3. Intentionally tamper with line 3
    lines = audit.path.read_text(encoding="utf-8").splitlines()
    tampered_entry = json.loads(lines[2])
    tampered_entry["tool"] = "hacked_tool"
    lines[2] = json.dumps(tampered_entry)
    audit.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 4. Verify tampering detected
    tamper_res = audit.verify_integrity()
    assert tamper_res["valid"] is False
    assert tamper_res["tampered"] is True
    assert tamper_res["broken_at_line"] == 3


def test_signing_service_verification(tmp_path: Path) -> None:
    signer = SigningService(trust_key="test-key-2026")
    content = "skill: raa-sample-skill\nversion: 1.0.0"

    sig = signer.sign(content)
    assert len(sig) == 64

    # Valid verification
    assert signer.verify(content, sig) is True

    # Tampered verification
    assert signer.verify(content + "\nextra", sig) is False

    # Content report
    rep = signer.verify_content("skill", "sample", content, sig)
    assert rep["verified"] is True
    assert rep["status"] == "trusted"

    # File signing
    f = tmp_path / "recipe.yaml"
    f.write_text(content, encoding="utf-8")
    sig_path = signer.sign_file(f)
    assert sig_path.is_file()

    file_rep = signer.verify_file(f)
    assert file_rep["verified"] is True
    assert file_rep["status"] == "trusted"


def test_tenancy_quota_enforcement(runtime: Runtime) -> None:
    quota = TenantQuota(tenant_id="restricted", name="Test Tenant", max_projects=1)
    runtime.tenancy.set_tenant_quota(quota)

    # First check passes
    runtime.tenancy.enforce_project_creation("restricted", 0)

    # Second check raises
    with pytest.raises(LimitExceededError):
        runtime.tenancy.enforce_project_creation("restricted", 1)


def test_sbom_generation(runtime: Runtime) -> None:
    cyclonedx = runtime.sbom.generate_cyclonedx()
    assert cyclonedx["bomFormat"] == "CycloneDX"
    assert cyclonedx["specVersion"] == "1.5"
    assert len(cyclonedx["components"]) > 10

    spdx = runtime.sbom.generate_spdx()
    assert spdx["spdxVersion"] == "SPDX-2.3"
    assert len(spdx["packages"]) > 10


def test_backup_restore_and_retention(runtime: Runtime, tmp_path: Path) -> None:
    # Create project and artifact
    proj = runtime.projects.create(name="Backup Target Project", description="Test")
    sample_apk = make_apk(tmp_path / "sample.apk")
    runtime.artifacts.ingest_path(
        project_id=proj.id,
        raw_path=str(sample_apk),
    )

    # 1. Create backup
    backup_meta = runtime.backup.create_backup(project_id=proj.id)
    assert Path(backup_meta["backup_file"]).is_file()
    assert backup_meta["artifact_count"] == 1
    assert len(backup_meta["sha256"]) == 64

    # 2. Restore backup
    restored = runtime.backup.restore_backup(
        bundle_path=Path(backup_meta["backup_file"]),
        new_name="Restored Copy",
    )
    assert restored["status"] == "restored"
    assert restored["artifacts_restored"] == 1

    # 3. Retention purge
    retention = runtime.backup.purge_retention(retention_days=100)
    assert retention["status"] == "retention_policy_enforced"


def test_metrics_service(runtime: Runtime) -> None:
    metrics = runtime.metrics.get_system_metrics()
    assert metrics["runtime_health"]["database_ok"] is True
    assert "storage" in metrics
    assert "audit" in metrics
    assert "engines" in metrics


async def test_phase11_admin_tool_invocations(runtime: Runtime) -> None:
    # admin_audit_verify
    verify_out = await runtime.invoke("admin_audit_verify", {}, profile="admin")
    assert verify_out.data["valid"] is True

    # admin_signature_verify
    sig_out = await runtime.invoke(
        "admin_signature_verify",
        {"name": "test_item", "content_type": "skill"},
        profile="admin",
    )
    assert sig_out.data["signed"] is False

    # admin_sbom_generate
    sbom_out = await runtime.invoke(
        "admin_sbom_generate",
        {"format": "cyclonedx"},
        profile="admin",
    )
    assert sbom_out.data["bomFormat"] == "CycloneDX"

    # admin_system_metrics
    metrics_out = await runtime.invoke("admin_system_metrics", {}, profile="admin")
    assert metrics_out.data["runtime_health"]["database_ok"] is True

    # admin_backup_create & restore
    proj = runtime.projects.create(name="Tool Invocation Project")
    backup_out = await runtime.invoke(
        "admin_backup_create",
        {"project_id": proj.id},
        profile="admin",
    )
    assert "backup_file" in backup_out.data

    restore_out = await runtime.invoke(
        "admin_backup_restore",
        {"bundle_path": backup_out.data["backup_file"]},
        profile="admin",
    )
    assert restore_out.data["status"] == "restored"

    # admin_retention_purge
    purge_out = await runtime.invoke(
        "admin_retention_purge",
        {"retention_days": 30},
        profile="admin",
    )
    assert purge_out.data["status"] == "retention_policy_enforced"


def test_signing_service_ephemeral_and_env_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import raa.services.signing as signing_mod

    assert not hasattr(signing_mod, "DEFAULT_SIGNING_KEY")

    monkeypatch.delenv("RAA_SIGNING_KEY", raising=False)
    with caplog.at_level("DEBUG"):
        s1 = SigningService()
        s2 = SigningService()
    assert s1.ephemeral is True
    assert s2.ephemeral is True
    assert s1.trust_key != s2.trust_key
    assert len(s1.trust_key) == 64
    assert "ephemeral" in caplog.text.lower()

    monkeypatch.setenv("RAA_SIGNING_KEY", "env-provided-signing-key-2026")
    s_env = SigningService()
    assert s_env.ephemeral is False
    assert s_env.trust_key == "env-provided-signing-key-2026"


def test_audit_verify_integrity_rejects_mid_chain_unhashed_entry(tmp_path: Path) -> None:
    audit = AuditService(tmp_path)
    # Pre-chain legacy unhashed entry is allowed before any hashed entry
    legacy_line = json.dumps({"ts": "2026-01-01T00:00:00Z", "tool": "legacy_tool", "outcome": "ok"})
    audit.path.write_text(legacy_line + "\n", encoding="utf-8")

    audit.record(
        tool="hashed_tool_1",
        surface="cli",
        profile="core",
        request_id="req_1",
        project_id=None,
        arguments={},
        outcome="ok",
        duration_ms=1.0,
    )
    assert audit.verify_integrity()["valid"] is True

    # Injecting an unhashed entry after hashed chain began must fail integrity
    with audit.path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps({"ts": "2026-01-02T00:00:00Z", "tool": "injected", "outcome": "ok"}) + "\n"
        )

    res = audit.verify_integrity()
    assert res["valid"] is False
    assert res["tampered"] is True
    assert res["broken_at_line"] == 3
