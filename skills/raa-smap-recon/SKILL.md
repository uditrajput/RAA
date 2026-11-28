---
name: raa-smap-recon
description: Passive Shodan InternetDB port, service, and vulnerability reconnaissance for mobile backend hosts using s0md3v/Smap without sending active packets.
version: 1.0.0
category: security
tools: [api_list_operations, security_scan_static, tool_manager_download]
---

# Passive Backend Reconnaissance (Smap)

Perform zero-contact, passive port and service discovery against backend domains and IPs extracted from mobile applications using **Smap** (`https://github.com/s0md3v/Smap`).

## Upstream Reference
- **Repository:** `https://github.com/s0md3v/Smap`
- **Tool ID:** `smap` (installable via RAA Tools Manager or `go install -v github.com/s0md3v/smap/cmd/smap@latest`)

## Workflow
1. Extract backend API domains and IP addresses from the target APK/IPA using `api_list_operations`.
2. Ensure `smap` is available (`tool_manager_download` or on `PATH`).
3. Run passive reconnaissance with JSON output (`smap -iL targets.txt -oJ smap_results.json`) — zero packets are sent to target servers.
4. Correlate discovered open ports, service banners, and Shodan-indexed CVEs into the RAA security report.
