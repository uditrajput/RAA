---
name: raa-ui-redesign
description: Capture runtime UI, inspect embedded webviews, generate modern Jetpack Compose code, and run visual diff verification.
version: 1.0.0
tools: [ui_runtime_capture, ui_webview_inspect, ui_redesign_generate, ui_visual_compare]
---

# Mobile UI Extraction & Redesign

Extract Android UI view hierarchies and screenshots, synthesize modern design tokens, and generate production Jetpack Compose or React Native code.

## Workflow
1. Capture running screen hierarchy and screenshot using `ui_runtime_capture`.
2. If hybrid, inspect DOM nodes and resources via `ui_webview_inspect`.
3. Generate modern Jetpack Compose code with 8pt grid and 60/30/10 color rules via `ui_redesign_generate`.
4. Validate visual fidelity against the original screenshot using `ui_visual_compare`.

## Mandatory Verification Gate
- Do not claim UI parity without running `ui_visual_compare` against the captured baseline screenshot.
- Implement screens incrementally and verify every interactive state (loading, empty, error) before finalizing.
