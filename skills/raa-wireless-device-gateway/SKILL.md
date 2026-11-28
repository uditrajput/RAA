---
name: raa-wireless-device-gateway
description: Cable-free Android Wi-Fi debugging, Android 11+ TLS pairing, loopback relay, resilient base64 chunked APK push, and port security audit.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [wireless_device_connect, wireless_device_status, wireless_apk_push, android_debloat_inspect, android_debloat_apply]
---

# RAA Wireless Device Gateway Skill

Cable-free Android and Android TV device interaction modeled after CleanYourTV and UAD-backed rootless debloating.

## Key Capabilities
- Zero-binary pure-Python ADB client
- Android 11+ TLS wireless pairing
- Resilient base64 chunked transfer with MD5 verification
- Post-test port closing verification
- Rootless UAD-backed package inspection (`android_debloat_inspect`) and dry-run-first debloating with `.sh`/`.ps1` undo scripts (`android_debloat_apply`)

## Safety & Verification Gate
- Always run `android_debloat_apply` with `dry_run=true` first and confirm UAD safety tiers before disabling packages.
- Verify backup JSON and restore script paths are written before executing `pm disable-user --user 0`.
