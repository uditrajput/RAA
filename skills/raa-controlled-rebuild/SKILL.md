---
name: raa-controlled-rebuild
description: Perform bytecode patching, Frida gadget injection, app resigning, and behavioral test verification.
version: 1.0.0
tools: [dynamic_inject_gadget, apk_patch, apk_sign, verify_behavior, test_run]
---

# Controlled APK Patching & Rebuild

Patch, instrument, resign, and behaviorally verify modified Android packages.

## Workflow
1. Inject Frida Gadget for non-rooted dynamic tracing using `dynamic_inject_gadget`.
2. Apply targeted Smali patches or manifest adjustments using `apk_patch`.
3. Sign the modified package with a test key using `apk_sign`.
4. Validate behavioral equivalence and integrity using `verify_behavior` and `test_run`.

## Mandatory Verification Gate
- Do not report a rebuild as complete until `apk_sign` succeeds and `verify_behavior` / `test_run` pass on the newly signed artifact.
- Never claim a patch works based on static inspection alone; record the exact tool output and signed APK hash.
- Preserve a rollback copy of the original unpatched artifact before mutating bytecode.
