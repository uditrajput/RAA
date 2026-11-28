"""Tests for registry speed caching, two-way WhatsApp/Telegram media/reports, and smart orchestrator."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from raa.runtime import Runtime
from raa.tools import build_registry


def test_registry_caching_is_fast() -> None:
    # First call warms lru_cache, second call clones in < 5ms
    _ = build_registry()
    t0 = time.perf_counter()
    reg = build_registry()
    elapsed = time.perf_counter() - t0
    assert reg.count() == 379
    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_two_way_whatsapp_and_telegram_ui_design_and_reports(
    runtime: Runtime,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime.channels.configure_whatsapp(mode="baileys", phone="+15550001234", paired=True)
    runtime.channels.configure_telegram(
        bot_token="123456:" + "ABC-DEF1234ghIkl-zyx57W2v1u123ew11", chat_id="999888"
    )
    monkeypatch.setattr(
        runtime.channels.whatsapp,
        "send_live_document",
        lambda recipient, file_path, caption="": {
            "channel": "whatsapp",
            "recipient": recipient,
            "status": "uploaded",
            "file_path": file_path,
            "caption": caption,
        },
    )
    monkeypatch.setattr(
        runtime.channels.telegram,
        "send_live_document",
        lambda chat_id, file_path, caption="": {
            "channel": "telegram",
            "recipient": chat_id,
            "status": "uploaded",
            "file_path": file_path,
            "caption": caption,
        },
    )
    monkeypatch.setattr(
        runtime.channels.telegram,
        "send_photo",
        lambda chat_id, image_path, caption="": {
            "channel": "telegram",
            "recipient": chat_id,
            "status": "uploaded",
            "file_path": image_path,
            "caption": caption,
        },
    )

    # 1. User sends a screenshot image over WhatsApp asking for UI design
    shot = tmp_path / "login_screen.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    ui_res = runtime.channels.process_inbound_message(
        channel="whatsapp",
        sender_id="+15550001234",
        text="Redesign this app UI in Compose",
        attachment_path=str(shot),
        runtime=runtime,
        auto_reply=True,
    )
    assert ui_res["accepted"] is True
    assert ui_res["intent"] == "ui_design"
    assert ui_res["delivery"]["status"] == "uploaded"
    assert Path(ui_res["delivery"]["file_path"]).exists()

    # 2. User asks for a report over Telegram
    rep_res = runtime.channels.process_inbound_message(
        channel="telegram",
        sender_id="999888",
        text="Send full report",
        runtime=runtime,
        auto_reply=True,
    )
    assert rep_res["accepted"] is True
    assert rep_res["intent"] == "report_export"
    assert rep_res["delivery"]["status"] == "uploaded"
    assert Path(rep_res["delivery"]["file_path"]).exists()

    # 3. Proactive progress report broadcast via MCP tool
    prog = await runtime.invoke(
        "channel_progress_report",
        {
            "stage": "Decompilation & UI Synthesis",
            "progress_pct": 80,
            "summary": "Extracted 12 endpoints and synthesized Compose M3 screen.",
            "attachment_path": str(shot),
        },
    )
    assert prog.data["status"] == "broadcast_complete"
    assert prog.data["targets_notified"] == 2


@pytest.mark.asyncio
async def test_smart_orchestrate_single_and_combined(runtime: Runtime) -> None:
    runtime.channels.whatsapp.pair_device(phone="+15550001234", device_name="Test Phone")

    combined = await runtime.invoke(
        "smart_orchestrate",
        {
            "goal": "Triage APK, design Compose UI, and send report on WhatsApp",
            "mode": "auto",
            "target_path": "sample.apk",
            "notify_channel": "whatsapp",
            "notify_recipient": "+15550001234",
        },
    )
    assert combined.data["mode"] == "combined"
    assert combined.data["step_count"] >= 4
    kinds = {s["kind"] for s in combined.data["steps"]}
    assert {"tool", "skill"} <= kinds
    assert combined.data["notification"]["status"] == "broadcast_complete"

    single = await runtime.invoke(
        "smart_orchestrate",
        {
            "goal": "Triage APK and design UI",
            "mode": "single",
            "target_path": "sample.apk",
        },
    )
    assert single.data["mode"] == "single"
    assert single.data["step_count"] == 1


@pytest.mark.asyncio
async def test_setup_ui_channels_chat_and_no_ping(
    runtime: Runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from raa.api.app import create_app

    app = create_app(runtime)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        html = (await client.get("/setup")).text
        assert "Send Test Ping" not in html
        assert 'id="tgChatBox"' in html
        assert 'id="waChatBox"' in html
        assert 'id="tgManualChatInput"' in html
        assert 'id="waManualChatInput"' in html

        monkeypatch.setattr(
            runtime.channels,
            "dispatch_message",
            lambda channel, recipient, text: {
                "channel": channel,
                "recipient": recipient,
                "status": "delivered",
                "text_length": len(text),
            },
        )
        monkeypatch.setattr(
            runtime.channels,
            "deliver_file",
            lambda channel, recipient, file_path, caption="": {
                "channel": channel,
                "recipient": recipient,
                "status": "uploaded",
                "file_path": file_path,
            },
        )

        for mode in ("manual", "llm", "report", "suggest"):
            resp = await client.post(
                "/api/setup/channels/chat",
                json={
                    "channel": "whatsapp",
                    "recipient": "+15550001234",
                    "text": "Triage APK and design UI",
                    "mode": mode,
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] in {"delivered", "sent"}
            assert body["mode"] == mode
            assert body["reply_preview"]
