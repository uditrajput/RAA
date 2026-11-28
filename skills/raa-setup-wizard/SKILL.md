---
name: raa-setup-wizard
description: Launches and orchestrates the responsive React/Tailwind visual onboarding wizard and persistent domain tabs dashboard.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [open_setup_ui, setup_state_get, setup_skip_register, setup_reopen_request]
---

# RAA Setup Wizard Skill

Provides visual configuration and onboarding ergonomics via the Cyber-Glass Neon Design System.

## Key Capabilities
- Guided 5-step interactive wizard
- Prominent Skip action with instant fallback to pure-Python parsers
- On-demand reopening via `open_setup_ui` or `raa setup`
