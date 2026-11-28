---
name: raa-android-tv-studio
description: Android TV and Google TV 10-foot layout deconstruction, D-pad spatial focus graph generation, Compose for TV Material 3 redesign, and screendiff parity verification.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [tv_ui_redesign, visual_screendiff_verify, wireless_perf_benchmark]
---

# RAA Android TV Studio Skill

10-Foot UI deconstruction and modernization for Android TV / Google TV.

## Key Capabilities
- Android TV Compose Material 3 (`androidx.tv.material3`) synthesis
- Spatial D-pad directional navigation graph validation
- Pixel-level screendiff parity checking with coordinate masking
- Wireless cold start and Perfetto trace slicing benchmark

## Verification Gate
- Run `visual_screendiff_verify` after Compose TV UI generation to confirm 10-foot layout parity.
- Verify D-pad focus reachability across all interactive elements before signing off on a TV redesign.
