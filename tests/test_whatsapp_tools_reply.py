"""Tests for WhatsApp inbound tool-count query and bridge self-chat handling."""

from __future__ import annotations

from raa.runtime import Runtime


def test_whatsapp_tools_query_replies_with_exact_tool_count(runtime: Runtime) -> None:
    runtime.channels.whatsapp.pair_device(phone="+15550001234", device_name="Test Phone")
    res = runtime.channels.process_inbound_message(
        channel="whatsapp",
        sender_id="+15550001234",
        text="How many tools you have",
        runtime=runtime,
        auto_reply=False,
    )
    assert res["accepted"] is True
    assert res["intent"] == "tools_capabilities"
    assert "379" in res["reply"]
    assert "MCP Tools" in res["reply"]


def test_whatsapp_remote_logout_signs_out_from_raa(
    runtime: Runtime,
    monkeypatch: object,
) -> None:
    runtime.channels.configure_whatsapp(mode="baileys", phone="+15550001234", paired=True)
    assert runtime.channels.whatsapp.paired is True

    # Simulate user logging out from WhatsApp on their phone (bridge reports disconnected + logged_out)
    monkeypatch.setattr(  # type: ignore[attr-defined]
        runtime.channels.whatsapp,
        "_bridge_request",
        lambda method, path, payload=None, timeout=8.0: {
            "state": "disconnected",
            "connected": False,
            "logged_out": True,
        },
    )

    status = runtime.channels.get_channels_status()
    assert status["whatsapp"]["paired"] is False
    assert status["whatsapp"]["configured"] is False
    assert status["whatsapp"]["status"] == "awaiting_scan"
    assert runtime.channels.whatsapp.phone == ""


def test_whatsapp_cadence_config_via_chat(runtime: Runtime) -> None:
    runtime.channels.whatsapp.pair_device(phone="+15550001234", device_name="Test Phone")
    res = runtime.channels.process_inbound_message(
        channel="whatsapp",
        sender_id="+15550001234",
        text="set cadence 2m",
        runtime=runtime,
        auto_reply=False,
    )
    assert res["accepted"] is True
    assert res["intent"] == "cadence_config"
    assert runtime.cadence.get_status()["mode"] == "interval"
    assert runtime.cadence.get_status()["interval_minutes"] == 2.0


def test_whatsapp_llm_interaction_for_general_question(
    runtime: Runtime,
    monkeypatch: object,
) -> None:
    import httpx

    runtime.channels.whatsapp.pair_device(phone="+15550001234", device_name="Test Phone")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")  # type: ignore[attr-defined]

    seen_payloads: list[dict[str, object]] = []

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        seen_payloads.append(kwargs.get("json") or {})  # type: ignore[arg-type]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "RAA uses libflutter.so and Dart snapshots."}}]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("raa.services.channels.gateway.httpx.post", fake_post)  # type: ignore[attr-defined]

    res = runtime.channels.process_inbound_message(
        channel="whatsapp",
        sender_id="+15550001234",
        text="Explain how RAA reverses Flutter apps",
        runtime=runtime,
        auto_reply=False,
    )
    assert res["accepted"] is True
    assert res["intent"] == "llm_response"
    assert "libflutter.so" in res["reply"]
    assert seen_payloads and "379 MCP tools" in str(seen_payloads[0])


def test_whatsapp_ping_pong_plan_is_tailored(runtime: Runtime, monkeypatch: object) -> None:
    runtime.channels.whatsapp.pair_device(phone="+15550001234", device_name="Test Phone")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("RAA_LLM_API_KEY", raising=False)  # type: ignore[attr-defined]

    res = runtime.channels.process_inbound_message(
        channel="whatsapp",
        sender_id="+15550001234",
        text="I want to plan to develop a simple ping pong app can you give me a plan for develop this.",
        runtime=runtime,
        auto_reply=False,
    )
    assert res["accepted"] is True
    assert res["intent"] == "development_plan"
    assert "Ping Pong" in res["reply"]
    assert "Game Loop & Canvas Physics" in res["reply"]


def test_whatsapp_app_building_and_download_are_relevant(
    runtime: Runtime, monkeypatch: object, tmp_path: object
) -> None:
    from pathlib import Path

    runtime.channels.whatsapp.pair_device(phone="+15550001234", device_name="Test Phone")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("RAA_LLM_API_KEY", raising=False)  # type: ignore[attr-defined]

    res_build = runtime.channels.process_inbound_message(
        channel="whatsapp",
        sender_id="+15550001234",
        text="Hi can you help me app building?",
        runtime=runtime,
        auto_reply=False,
    )
    assert res_build["accepted"] is True
    assert "build & ship Android apps" in res_build["reply"]

    fake_apk = Path(str(tmp_path)) / "myvida.apk"
    fake_apk.write_bytes(b"PK\x03\x04FAKE")
    monkeypatch.setattr(runtime.channels, "_search_play_package", lambda q: ["com.myvida.app"])  # type: ignore[attr-defined]
    monkeypatch.setattr(
        runtime.playstore,
        "download_app",
        lambda pkg, provider="auto", auto_ingest=False: {
            "downloaded_path": str(fake_apk),
            "provider": "apkeep",
        },
    )  # type: ignore[attr-defined]

    res_dl = runtime.channels.process_inbound_message(
        channel="whatsapp",
        sender_id="+15550001234",
        text="Can you download MyVida apk and share with me",
        runtime=runtime,
        auto_reply=False,
    )
    assert res_dl["accepted"] is True
    assert res_dl["intent"] == "app_download"
    assert "com.myvida.app" in res_dl["reply"]
    assert "apkeep" in res_dl["reply"]


def test_telegram_configure_resolves_vault_key_name(runtime: Runtime, monkeypatch: object) -> None:
    sample_token = "712948123:" + "AAH_sampleTokenValue1234567890"
    runtime.vault.store_credential(
        key_name="Telegram_bot_TOKEN",
        secret_value=sample_token,
        username="RAABot",
        service="Telegram",
    )
    seen_tokens: list[str] = []

    def fake_verify(token: str) -> dict[str, object]:
        seen_tokens.append(token)
        runtime.channels.telegram.bot_token = token
        return {
            "valid": token == sample_token,
            "bot_username": "@RaaTel_bot",
            "bot_name": "RAABot",
            "pairing_code": "pair123",
            "pairing_url": "https://t.me/RaaTel_bot?start=pair123",
            "qr_svg": "<svg/>",
        }

    monkeypatch.setattr(runtime.channels.telegram, "verify_token_live", fake_verify)  # type: ignore[attr-defined]

    res = runtime.channels.configure_telegram(
        bot_token="Telegram_bot_TOKEN", chat_id="123456", live_only=True
    )
    assert res["status"] == "success"
    assert res["configured"] is True
    assert runtime.channels.telegram.bot_token == sample_token

    res2 = runtime.channels.configure_telegram(
        bot_token="vault://telegram_bot_token", live_only=True
    )
    assert res2["status"] == "success"
    assert seen_tokens == [sample_token, sample_token]
