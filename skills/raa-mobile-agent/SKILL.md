---
name: raa-mobile-agent
description: Orchestrates two-way conversational reverse engineering over Telegram and WhatsApp, validates domain intent, and delivers patched APKs.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [channel_prompt_receive, channel_message_dispatch, channel_apk_deliver, channel_test_ping, channel_whitelist_manage]
---

# RAA Mobile Agent Skill

Provides two-way natural language control of RAA via mobile messaging platforms (Telegram & WhatsApp).

## Key Capabilities
- Validate inbound prompts against Domain Intent Guard (`guard.py`)
- Dispatch progress digests to mobile chats
- Upload signed, patched, and rebuilt `.apk` binaries directly into chat
