"""
FILE: src/voltsentry/services/automation_hooks.py
PATH: voltsentry/src/voltsentry/services/automation_hooks.py
DESCRIPTION: Automation hooks for CLI and Webhook triggers
PHASE: 5.3 - Automation Hooks (CLI & Webhook)
DISCIPLINES:
- 0.1 Logging: Every hook invocation logged
- 0.2 Error Handling: Catches RequestException, non-zero exits
- 0.3 Retry Standard: 2 attempts on RequestException
- 0.4 Fallback: Auto-disabled after 5 consecutive failures
- BATTERY OPTIMIZATION: Event-driven only, no background polling
"""

from datetime import datetime
import json
from pathlib import Path
import shlex
import subprocess
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

import requests

from ..core.constants import WEBHOOK_TIMEOUT
from ..core.decorators import log_entry_exit
from ..core.exceptions import AutomationHookError, HookDisabledError
from ..core.logging_config import get_logger, log_audit
from ..core.resilience import CircuitBreaker, resilient
from ..core.types import AlarmType, BatteryReading
from ..db.models import AutomationHookLog
from ..db.repositories import AutomationHookRepository

logger = get_logger(__name__)


class WebhookHook:
    """
    Webhook automation hook.

    Sends HTTP POST requests to a configured URL.
    Auto-disabled after 5 consecutive failures.
    Battery optimized: Only fires on events, no background polling.
    """

    def __init__(
        self,
        url: str,
        failure_limit: int = 5,
        timeout: int = WEBHOOK_TIMEOUT,
    ):
        self.url = url
        self.timeout = timeout
        self.breaker = CircuitBreaker(
            failure_limit=failure_limit, name=f"webhook_{url[:30]}"
        )
        self._enabled = True

        logger.info("WebhookHook initialized: %s...", url[:50])

    @property
    def enabled(self) -> bool:
        """Check if the hook is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable the hook."""
        self._enabled = value
        if not value:
            logger.info("Webhook disabled")

    @log_entry_exit()
    def fire(self, payload: Dict[str, Any]) -> bool:
        """
        Fire the webhook with the given payload.

        Args:
            payload: Data to send as JSON

        Returns:
            True if successful

        Raises:
            AutomationHookError: If hook fails and is not auto-disabled
            HookDisabledError: If hook is disabled
        """
        if not self._enabled:
            raise HookDisabledError("Webhook is disabled")

        if self.breaker.is_open:
            logger.warning("Webhook circuit breaker open - skipping request")
            return False

        try:
            response = self._post(payload)
            self.breaker.record_success()
            logger.debug("Webhook successful: %d", response.status_code)
            return True

        except requests.exceptions.RequestException as e:
            self.breaker.record_failure()
            logger.error("Webhook failed: %s", e)

            if self.breaker.is_open:
                self._enabled = False
                logger.warning(
                    "Webhook auto-disabled after %d failures",
                    self.breaker.failure_limit,
                )
                raise HookDisabledError(
                    "Webhook auto-disabled after repeated failures"
                ) from e

            raise AutomationHookError(f"Webhook failed: {e}") from e

    @resilient(
        exceptions=(requests.exceptions.RequestException,), attempts=2
    )
    def _post(self, payload: Dict[str, Any]) -> requests.Response:
        """Make the HTTP POST request with retry support."""
        response = requests.post(
            self.url,
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response

    def get_status(self) -> dict:
        """Get hook status."""
        return {
            "enabled": self._enabled,
            "url": self.url[:50] + ("..." if len(self.url) > 50 else ""),
            "circuit_breaker": str(self.breaker),
            "is_open": self.breaker.is_open,
        }


class ScriptHook:
    """
    Script automation hook.

    Executes a local script or command.
    Battery optimized: Only fires on events, no background polling.
    """

    def __init__(self, script_path: Path, timeout: int = 30):
        self.script_path = script_path
        self.timeout = timeout
        self._enabled = True

        logger.info("ScriptHook initialized: %s", script_path)

    @property
    def enabled(self) -> bool:
        """Check if the hook is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable the hook."""
        self._enabled = value

    @log_entry_exit()
    def fire(self, payload: Dict[str, Any]) -> bool:
        """
        Execute the script with the given payload.

        Args:
            payload: Data to pass to the script (as JSON)

        Returns:
            True if successful

        Raises:
            AutomationHookError: If script fails
            HookDisabledError: If hook is disabled
        """
        if not self._enabled:
            raise HookDisabledError(f"Script is disabled: {self.script_path}")

        try:
            # Prepare command
            cmd = [str(self.script_path)]

            # Pass payload as JSON string
            cmd.append(json.dumps(payload))

            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False,
            )

            if result.returncode != 0:
                error_msg = f"Script exited with code {result.returncode}: {result.stderr}"
                logger.error("Script failed: %s", error_msg)
                raise AutomationHookError(error_msg)

            logger.debug(
                "Script executed successfully: %s",
                result.stdout[:100] if result.stdout else "",
            )
            return True

        except subprocess.TimeoutExpired as e:
            raise AutomationHookError(
                f"Script timed out after {self.timeout}s"
            ) from e
        except Exception as e:
            raise AutomationHookError(f"Script execution failed: {e}") from e

    def get_status(self) -> dict:
        """Get hook status."""
        return {
            "enabled": self._enabled,
            "script_path": str(self.script_path),
            "exists": self.script_path.exists(),
        }


class AutomationHookManager:
    """
    Manages all automation hooks.

    Fires hooks when threshold events occur.
    All hooks are event-driven (battery optimized).
    """

    def __init__(self):
        self._webhooks: List[WebhookHook] = []
        self._scripts: List[ScriptHook] = []
        self._repository = AutomationHookRepository()
        self._lock = Lock()

        # Event callbacks
        self._on_webhook_failure: List[Callable[[str], None]] = []
        self._on_script_failure: List[Callable[[str], None]] = []

        logger.info("AutomationHookManager initialized")

    def add_webhook(self, url: str, failure_limit: int = 5) -> WebhookHook:
        """Add a webhook hook."""
        with self._lock:
            hook = WebhookHook(url, failure_limit=failure_limit)
            self._webhooks.append(hook)
            logger.info("Webhook added: %s", url[:50])
            return hook

    def remove_webhook(self, url: str) -> bool:
        """Remove a webhook hook."""
        with self._lock:
            self._webhooks = [h for h in self._webhooks if h.url != url]
            logger.info("Webhook removed: %s", url[:50])
            return True

    def add_script(self, script_path: Path, timeout: int = 30) -> ScriptHook:
        """Add a script hook."""
        with self._lock:
            hook = ScriptHook(script_path, timeout=timeout)
            self._scripts.append(hook)
            logger.info("Script added: %s", script_path)
            return hook

    def remove_script(self, script_path: Path) -> bool:
        """Remove a script hook."""
        with self._lock:
            self._scripts = [
                s for s in self._scripts if s.script_path != script_path
            ]
            logger.info("Script removed: %s", script_path)
            return True

    @log_entry_exit()
    def fire_event(
        self,
        event_type: str,
        reading: BatteryReading,
        alarm_type: Optional[AlarmType] = None,
    ) -> None:
        """
        Fire automation hooks for an event.

        Args:
            event_type: Type of event (threshold_crossed, alarm_triggered, etc.)
            reading: Battery reading at event time
            alarm_type: Alarm type if applicable
        """
        # Build payload
        payload = self._build_payload(event_type, reading, alarm_type)

        # Fire webhooks
        for hook in self._webhooks:
            try:
                success = hook.fire(payload)
                self._log_hook("webhook", success, hook.url)
            except Exception as e:
                logger.error("Webhook fire failed: %s", e)
                self._log_hook("webhook", False, hook.url, str(e))

        # Fire scripts
        for script in self._scripts:
            try:
                success = script.fire(payload)
                self._log_hook("script", success, str(script.script_path))
            except Exception as e:
                logger.error("Script fire failed: %s", e)
                self._log_hook("script", False, str(script.script_path), str(e))

    def _build_payload(
        self,
        event_type: str,
        reading: BatteryReading,
        alarm_type: Optional[AlarmType] = None,
    ) -> Dict[str, Any]:
        """Build payload for hooks."""
        payload = {
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "battery": {
                "percent": reading.percent,
                "is_charging": reading.is_charging,
                "power_draw_watts": reading.power_draw_watts,
            },
        }

        if alarm_type:
            payload["alarm"] = {
                "type": alarm_type.value,
            }

        return payload

    def _log_hook(
        self,
        hook_type: str,
        success: bool,
        identifier: str,
        detail: Optional[str] = None,
    ) -> None:
        """Log hook invocation to database."""
        try:
            log_entry = AutomationHookLog(
                hook_type=hook_type,
                success=success,
                detail=f"{identifier}: {detail}" if detail else identifier,
            )
            self._repository.save(log_entry)
        except Exception as e:
            logger.error("Failed to log hook invocation: %s", e)

    def get_status(self) -> dict:
        """Get automation manager status."""
        return {
            "webhooks": [h.get_status() for h in self._webhooks],
            "scripts": [s.get_status() for s in self._scripts],
            "total_webhooks": len(self._webhooks),
            "total_scripts": len(self._scripts),
        }

    def get_hook_logs(self, limit: int = 50) -> List[AutomationHookLog]:
        """Get recent hook logs."""
        return self._repository.get_recent_failures(limit)

    def clear_hooks(self) -> None:
        """Clear all hooks."""
        with self._lock:
            self._webhooks.clear()
            self._scripts.clear()
            logger.info("All hooks cleared")

    def add_webhook_failure_callback(
        self, callback: Callable[[str], None]
    ) -> None:
        """Add callback for webhook failures."""
        self._on_webhook_failure.append(callback)

    def add_script_failure_callback(
        self, callback: Callable[[str], None]
    ) -> None:
        """Add callback for script failures."""
        self._on_script_failure.append(callback)