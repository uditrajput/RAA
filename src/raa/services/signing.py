"""Cryptographic signature generation and verification for skills, recipes, and engine packs."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SigningService:
    """Provides cryptographic signature verification for skills, recipes, and engine manifests."""

    def __init__(self, trust_key: str | None = None) -> None:
        resolved_key = (trust_key or os.environ.get("RAA_SIGNING_KEY", "")).strip()
        if not resolved_key:
            resolved_key = secrets.token_hex(32)
            self.ephemeral = True
            logger.debug(
                "RAA_SIGNING_KEY is not set and no trust_key was provided; "
                "generated an ephemeral per-process signing key."
            )
        else:
            self.ephemeral = False
        self.trust_key = resolved_key

    def sign(self, data: str | bytes, key: str | None = None) -> str:
        """Generate a deterministic HMAC-SHA256 signature for the given payload."""
        secret = (key or self.trust_key).encode("utf-8")
        payload = data.encode("utf-8") if isinstance(data, str) else data
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

    def verify(self, data: str | bytes, signature: str, key: str | None = None) -> bool:
        """Verify an HMAC-SHA256 signature using constant-time comparison."""
        expected = self.sign(data, key)
        return hmac.compare_digest(expected.lower(), signature.strip().lower())

    def verify_content(
        self,
        content_type: str,
        name: str,
        content: str | bytes,
        signature: str | None = None,
    ) -> dict[str, Any]:
        """Verify content integrity and optional digital signature."""
        payload = content.encode("utf-8") if isinstance(content, str) else content
        digest = hashlib.sha256(payload).hexdigest()

        if not signature:
            return {
                "content_type": content_type,
                "name": name,
                "sha256": digest,
                "signed": False,
                "verified": False,
                "status": "unsigned",
                "message": f"{content_type.capitalize()} '{name}' is not signed.",
            }

        valid = self.verify(payload, signature)
        return {
            "content_type": content_type,
            "name": name,
            "sha256": digest,
            "signed": True,
            "verified": valid,
            "status": "trusted" if valid else "tampered",
            "message": (
                f"{content_type.capitalize()} '{name}' signature verified successfully."
                if valid
                else (
                    f"SIGNATURE VERIFICATION FAILED: {content_type} '{name}' "
                    "has been modified or forged."
                )
            ),
        }

    def verify_file(self, file_path: Path, signature_path: Path | None = None) -> dict[str, Any]:
        """Verify a file on disk against its detached signature file (<file>.sig)."""
        if not file_path.is_file():
            return {
                "file": str(file_path),
                "verified": False,
                "status": "file_not_found",
                "message": f"File '{file_path}' does not exist.",
            }

        content = file_path.read_bytes()
        sig_file = signature_path or file_path.with_suffix(file_path.suffix + ".sig")

        if not sig_file.is_file():
            digest = hashlib.sha256(content).hexdigest()
            return {
                "file": str(file_path),
                "sha256": digest,
                "signed": False,
                "verified": False,
                "status": "unsigned",
                "message": f"No detached signature found at '{sig_file}'.",
            }

        signature = sig_file.read_text(encoding="utf-8").strip()
        return self.verify_content(
            content_type="file",
            name=file_path.name,
            content=content,
            signature=signature,
        )

    def sign_file(self, file_path: Path, output_sig_path: Path | None = None) -> Path:
        """Create a detached signature file for a target file on disk."""
        content = file_path.read_bytes()
        signature = self.sign(content)
        target = output_sig_path or file_path.with_suffix(file_path.suffix + ".sig")
        target.write_text(signature + "\n", encoding="utf-8")
        return target
