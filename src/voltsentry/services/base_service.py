"""
FILE: src/voltsentry/services/base_service.py
PATH: voltsentry/src/voltsentry/services/base_service.py
DESCRIPTION: Base service class with common patterns for all services
PHASE: 2.5 - Persistence Layer (Base for all services)

DISCIPLINES:
- 0.1 Logging Standard: Unified logging through base class
- 0.2 Error Handling: Standardized error handling
- 0.4 Fallback Standard: Degraded mode support
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

from ..core.decorators import log_entry_exit, timed
from ..core.exceptions import VoltSentryError
from ..core.logging_config import get_logger

T = TypeVar("T")


class BaseService(ABC, Generic[T]):
    """
    Base service class with common patterns.

    Provides:
    - Unified logging
    - Error handling
    - Health checking
    - Status reporting
    """

    def __init__(self, name: str):
        self._name = name
        self._logger = get_logger(f"services.{name}")
        self._initialized = False
        self._degraded = False
        self._error_count = 0
        self._max_errors = 10

        self._logger.info("%s service initialized", name)

    @abstractmethod
    def _do_initialize(self) -> None:
        """Internal initialization (override in subclasses)."""
        pass

    def initialize(self) -> None:
        """Initialize the service."""
        if self._initialized:
            return

        try:
            self._do_initialize()
            self._initialized = True
            self._logger.info("%s service initialized successfully", self._name)
        except Exception as e:
            self._logger.error("Failed to initialize %s: %s", self._name, e)
            raise

    @property
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._initialized

    @property
    def is_degraded(self) -> bool:
        """Check if the service is in degraded mode."""
        return self._degraded

    @log_entry_exit()
    @timed()
    def _handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle an error with logging and degradation tracking.

        Args:
            error: The exception that occurred
            context: Context string for logging
        """
        self._error_count += 1
        self._logger.error(
            "%s error (%d): %s%s",
            self._name,
            self._error_count,
            error,
            f" in {context}" if context else "",
        )

        if self._error_count >= self._max_errors:
            self._degraded = True
            self._logger.warning("%s entering degraded mode", self._name)

    def reset_errors(self) -> None:
        """Reset error count and exit degraded mode."""
        self._error_count = 0
        self._degraded = False
        self._logger.info("%s error count reset", self._name)

    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            "name": self._name,
            "initialized": self._initialized,
            "degraded": self._degraded,
            "error_count": self._error_count,
            "max_errors": self._max_errors,
        }

    def health_check(self) -> bool:
        """
        Perform a health check.

        Returns:
            True if service is healthy
        """
        return self._initialized and not self._degraded

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(name={self._name}, initialized={self._initialized})>"
        )