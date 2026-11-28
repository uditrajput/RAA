"""Cadence and Notification Intensity Controller.

Regulates frequency of mobile updates (start/end only, 1m/2m/5m/10m intervals, milestone-driven,
or adaptive), and enforces emergency CVE break-ins for high-risk security findings.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_CADENCE_MODES = {"start_end", "interval", "milestone", "adaptive"}


class CadenceService:
    """Regulates notification intensity, throttle windows, and emergency security alerts."""

    def __init__(
        self,
        default_mode: str = "interval",
        default_interval_minutes: int = 5,
        urgent_cve_breakin: bool = True,
    ) -> None:
        self.mode = default_mode if default_mode in SUPPORTED_CADENCE_MODES else "interval"
        self.interval_seconds = max(30, default_interval_minutes * 60)
        self.urgent_cve_breakin = urgent_cve_breakin
        self.last_dispatch_time = 0.0
        self.dispatch_count = 0
        self.urgent_breakins_count = 0
        self.pending_digests: list[dict[str, Any]] = []

    def configure(
        self,
        mode: str | None = None,
        interval_minutes: int | None = None,
        urgent_cve_breakin: bool | None = None,
    ) -> dict[str, Any]:
        if mode:
            mode_clean = mode.lower()
            if mode_clean not in SUPPORTED_CADENCE_MODES:
                raise ValueError(
                    f"Invalid mode '{mode}'. Choose from: {sorted(SUPPORTED_CADENCE_MODES)}"
                )
            self.mode = mode_clean

        if interval_minutes is not None:
            if interval_minutes <= 0:
                raise ValueError("Interval minutes must be greater than 0.")
            self.interval_seconds = interval_minutes * 60

        if urgent_cve_breakin is not None:
            self.urgent_cve_breakin = urgent_cve_breakin

        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        now = time.time()
        elapsed = now - self.last_dispatch_time
        time_to_next = max(0, self.interval_seconds - elapsed) if self.mode == "interval" else None

        return {
            "mode": self.mode,
            "interval_minutes": round(self.interval_seconds / 60, 1),
            "interval_seconds": self.interval_seconds,
            "urgent_cve_breakin": self.urgent_cve_breakin,
            "last_dispatch_time": self.last_dispatch_time,
            "next_dispatch_in_seconds": round(time_to_next, 1)
            if time_to_next is not None
            else None,
            "total_dispatches": self.dispatch_count,
            "urgent_breakins_count": self.urgent_breakins_count,
            "queued_digest_items": len(self.pending_digests),
        }

    def should_dispatch(self, event_type: str, is_critical: bool = False) -> tuple[bool, str]:
        """Determines if a notification should be dispatched now or queued."""
        if is_critical and self.urgent_cve_breakin:
            return True, "emergency_cve_breakin"

        if self.mode == "start_end":
            if event_type in {"task_start", "task_completed", "task_failed"}:
                return True, "start_end_boundary"
            return False, "held_by_start_end_cadence"

        if self.mode == "milestone":
            if event_type in {
                "task_start",
                "milestone",
                "phase_transition",
                "task_completed",
                "task_failed",
            }:
                return True, "milestone_achieved"
            return False, "held_by_milestone_cadence"

        if self.mode == "interval":
            now = time.time()
            if event_type in {"task_start", "task_completed", "task_failed"}:
                return True, "terminal_event"
            if now - self.last_dispatch_time >= self.interval_seconds:
                return True, "interval_elapsed"
            return False, "held_by_interval_throttle"

        if self.mode == "adaptive":
            # Adaptive sends start/end, milestone, and bursts if activity accelerates
            if event_type in {"task_start", "milestone", "task_completed", "task_failed"}:
                return True, "adaptive_milestone"
            now = time.time()
            if now - self.last_dispatch_time >= self.interval_seconds:
                return True, "adaptive_interval"
            return False, "held_by_adaptive_smoother"

        return True, "default_allow"

    def record_and_dispatch(
        self,
        event_type: str,
        message: str,
        is_critical: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        should_send, reason = self.should_dispatch(event_type, is_critical=is_critical)
        now = time.time()

        item = {
            "timestamp": now,
            "event_type": event_type,
            "message": message,
            "is_critical": is_critical,
            "metadata": metadata or {},
        }

        if should_send:
            self.last_dispatch_time = now
            self.dispatch_count += 1
            if is_critical and reason == "emergency_cve_breakin":
                self.urgent_breakins_count += 1

            bundled_digest = list(self.pending_digests)
            self.pending_digests.clear()

            return {
                "dispatched": True,
                "reason": reason,
                "message": message,
                "bundled_previous_items": len(bundled_digest),
                "is_critical": is_critical,
            }
        else:
            self.pending_digests.append(item)
            return {
                "dispatched": False,
                "reason": reason,
                "queued_in_digest": True,
                "total_queued": len(self.pending_digests),
            }

    def trigger_urgent_breakin(
        self, severity: str, finding_title: str, details: str
    ) -> dict[str, Any]:
        """Directly forces an emergency break-in alert for high-risk vulnerabilities."""
        message = f"🚨 [URGENT {severity.upper()} BREAK-IN] {finding_title}\n{details}"
        return self.record_and_dispatch(
            event_type="urgent_cve_alert",
            message=message,
            is_critical=True,
            metadata={"severity": severity, "finding": finding_title},
        )
