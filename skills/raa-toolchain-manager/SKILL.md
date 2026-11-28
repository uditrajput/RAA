---
name: raa-toolchain-manager
description: Autonomous toolchain provisioning, SHA-256 verification, dynamic runtime PATH injection, and uninstallation storage reclamation.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [tool_manager_list, tool_manager_download, tool_manager_verify, tool_manager_auto_path, tool_manager_delete, tool_manager_status]
---

# RAA Toolchain Manager Skill

Manages the lifecycle of external reversing binaries (JADX, Apktool, Platform-Tools, Ghidra, Frida, Uber-Signer).

## Key Capabilities
- 1-click downloads from verified mirrors
- Cryptographic SHA-256 integrity verification
- Dynamic runtime PATH registration without machine restarts
- Tool deletion and disk storage reclamation
