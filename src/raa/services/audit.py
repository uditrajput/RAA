"""Append-only local audit trail with cryptographic hash chaining.

Argument values are deliberately not recorded. The audit log stores the tool,
caller surface, project, argument keys, hash of the canonical arguments, and
a SHA-256 hash chain linking every entry to the previous entry for tamper resistance.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Any

from raa.utils.time import utc_now

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


class AuditService:
    def __init__(self, directory: Path) -> None:
        self.path = directory / "audit.jsonl"
        self._lock = threading.Lock()

    def _get_last_hash(self) -> str:
        """Retrieve the hash of the most recent audit entry, or genesis hash if empty."""
        if not self.path.is_file():
            return GENESIS_HASH
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if isinstance(entry, dict) and "hash" in entry:
                        return str(entry["hash"])
                except Exception as exc:
                    logger.debug("Skipping unreadable audit entry while reading last hash: %s", exc)
                    continue
        except OSError:
            return GENESIS_HASH
        return GENESIS_HASH

    @staticmethod
    def _compute_hash(prev_hash: str, entry_without_hash: dict[str, Any]) -> str:
        """Compute deterministic SHA-256 hash linking prev_hash and entry payload."""
        canonical = json.dumps(entry_without_hash, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(f"{prev_hash}:{canonical}".encode()).hexdigest()

    def record(
        self,
        *,
        tool: str,
        surface: str,
        profile: str,
        request_id: str,
        project_id: str | None,
        arguments: dict[str, Any],
        outcome: str,
        duration_ms: float,
        error_code: str | None = None,
    ) -> None:
        canonical_args = json.dumps(arguments, sort_keys=True, default=str, ensure_ascii=False)
        entry: dict[str, Any] = {
            "ts": utc_now().isoformat(),
            "tool": tool,
            "surface": surface,
            "profile": profile,
            "request_id": request_id,
            "project_id": project_id,
            "argument_keys": sorted(arguments),
            "arguments_sha256": hashlib.sha256(canonical_args.encode("utf-8")).hexdigest(),
            "outcome": outcome,
            "duration_ms": round(duration_ms, 3),
        }
        if error_code:
            entry["error_code"] = error_code

        with self._lock:
            prev_hash = self._get_last_hash()
            entry["prev_hash"] = prev_hash
            entry["hash"] = self._compute_hash(prev_hash, entry)

            line = json.dumps(entry, ensure_ascii=False, default=str)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def query(
        self,
        *,
        tool: str | None = None,
        outcome: str | None = None,
        error_code: str | None = None,
        project_id: str | None = None,
        request_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Query recorded audit trail events with optional filtering and pagination."""
        if not self.path.is_file():
            return {"total": 0, "limit": limit, "offset": offset, "entries": []}
        entries: list[dict[str, Any]] = []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception as exc:
                logger.debug("Skipping unreadable audit entry during query: %s", exc)
                continue
            if tool and entry.get("tool") != tool:
                continue
            if outcome and entry.get("outcome") != outcome:
                continue
            if error_code and entry.get("error_code") != error_code:
                continue
            if project_id and entry.get("project_id") != project_id:
                continue
            if request_id and entry.get("request_id") != request_id:
                continue
            entries.append(entry)
        total = len(entries)
        paged = entries[offset : offset + limit]
        return {"total": total, "limit": limit, "offset": offset, "entries": paged}

    def verify_integrity(self) -> dict[str, Any]:
        """Cryptographically verify the tamper-evident hash chain of the audit log."""
        if not self.path.is_file():
            return {
                "valid": True,
                "records_checked": 0,
                "latest_hash": GENESIS_HASH,
                "tampered": False,
                "message": "Audit log is empty.",
            }

        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()

        expected_prev = GENESIS_HASH
        records_checked = 0
        seen_hashed = False

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return {
                    "valid": False,
                    "records_checked": records_checked,
                    "broken_at_line": line_no,
                    "tampered": True,
                    "error": "Corrupt JSON payload encountered in audit trail.",
                }

            # Handle backward compatibility for entries written before hash chaining
            recorded_hash = entry.get("hash")
            recorded_prev = entry.get("prev_hash")

            if recorded_hash is None or recorded_prev is None:
                if seen_hashed:
                    return {
                        "valid": False,
                        "records_checked": records_checked,
                        "broken_at_line": line_no,
                        "tampered": True,
                        "error": (
                            f"Unhashed audit entry encountered at line {line_no} "
                            "after hash chain started."
                        ),
                    }
                # Legacy unhashed record before the first hashed entry
                records_checked += 1
                continue

            if recorded_prev != expected_prev:
                return {
                    "valid": False,
                    "records_checked": records_checked,
                    "broken_at_line": line_no,
                    "tampered": True,
                    "error": (
                        f"Hash chain broken at line {line_no}: "
                        f"expected prev_hash '{expected_prev}', got '{recorded_prev}'."
                    ),
                }

            entry_core = {k: v for k, v in entry.items() if k != "hash"}
            computed_hash = self._compute_hash(recorded_prev, entry_core)
            if computed_hash != recorded_hash:
                return {
                    "valid": False,
                    "records_checked": records_checked,
                    "broken_at_line": line_no,
                    "tampered": True,
                    "error": (
                        f"Hash signature mismatch at line {line_no}: "
                        f"content was modified. Expected '{computed_hash}', got '{recorded_hash}'."
                    ),
                }

            seen_hashed = True
            expected_prev = recorded_hash
            records_checked += 1

        return {
            "valid": True,
            "records_checked": records_checked,
            "latest_hash": expected_prev,
            "tampered": False,
            "message": f"Audit trail verified successfully across {records_checked} entries.",
        }
