# File: resilience.py
# Path: voltsentry/src/voltsentry/core/resilience.py
# Description: Resilience pattern utilities: exponential retries, circuit breakers, fallbacks, and health checkers.

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, ParamSpec, Tuple, Type, TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from voltsentry.core.constants import (
    CIRCUIT_BREAKER_FAILURE_LIMIT,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_MAX_WAIT,
    DEFAULT_RETRY_MULTIPLIER,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Transient exceptions suited for automatic retries
TRANSIENT_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    OSError,
    TimeoutError,
    ConnectionError,
)


def resilient(
    exceptions: Tuple[Type[BaseException], ...] = TRANSIENT_EXCEPTIONS,
    attempts: int = DEFAULT_RETRY_ATTEMPTS,
    max_wait: int = DEFAULT_RETRY_MAX_WAIT,
    multiplier: float = DEFAULT_RETRY_MULTIPLIER,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Standard retry decorator with exponential backoff."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=multiplier, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
        )
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        wrapper._retry_attempts = attempts  # type: ignore[attr-defined]
        wrapper._retry_max_wait = max_wait  # type: ignore[attr-defined]

        return wrapper

    return decorator


# ============================================================================
# Circuit Breaker
# ============================================================================
class CircuitBreaker:
    """Circuit breaker pattern - stops hammering a failing operation."""

    def __init__(
        self,
        failure_limit: int = CIRCUIT_BREAKER_FAILURE_LIMIT,
        cooldown_seconds: float = 60.0,
        name: Optional[str] = None,
    ) -> None:
        self.failure_limit = failure_limit
        self.cooldown_seconds = cooldown_seconds
        self.name = name or "circuit_breaker"
        self._consecutive_failures = 0
        self._is_open = False
        self._last_failure_time: Optional[float] = None

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._is_open

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._consecutive_failures

    def record_success(self) -> None:
        """Record a success (closes circuit)."""
        if self._is_open:
            logger.info("%s: Circuit CLOSED (recovered on successful call)", self.name)
        self._consecutive_failures = 0
        self._is_open = False
        self._last_failure_time = None

    def record_failure(self) -> None:
        """Record a failure (may trip circuit)."""
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        if self._consecutive_failures >= self.failure_limit:
            self._is_open = True
            logger.warning(
                "%s: Circuit OPENED after %d consecutive failures",
                self.name,
                self._consecutive_failures,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._consecutive_failures = 0
        self._is_open = False
        self._last_failure_time = None
        logger.info("%s: Circuit manually reset", self.name)

    def can_attempt(self) -> bool:
        """Check if we can attempt the operation (supports half-open probe after cooldown)."""
        if not self._is_open:
            return True

        # Half-open check
        if self._last_failure_time is not None:
            if time.time() - self._last_failure_time >= self.cooldown_seconds:
                logger.info("%s: Circuit entering HALF-OPEN state (testing service)", self.name)
                return True

        return False

    def __repr__(self) -> str:
        status = "OPEN" if self._is_open else "CLOSED"
        return (
            f"CircuitBreaker(name={self.name}, status={status}, "
            f"failures={self._consecutive_failures}/{self.failure_limit})"
        )


def with_circuit_breaker(
    breaker: CircuitBreaker,
    fallback_return: Optional[Any] = None,
) -> Callable[[Callable[P, T]], Callable[P, Optional[T]]]:
    """Decorator to apply a circuit breaker to a function."""
    def decorator(func: Callable[P, T]) -> Callable[P, Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[T]:
            if not breaker.can_attempt():
                logger.warning("%s: Circuit open, returning fallback", breaker.name)
                return fallback_return

            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise e

        return wrapper

    return decorator


# ============================================================================
# Fallback Helpers
# ============================================================================
def fallback_if_fails(
    fallback_func: Callable[[], T],
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to execute a fallback function on failure."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.warning(
                    "%s failed with error: %s. Invoking fallback.",
                    func.__qualname__,
                    e,
                )
                return fallback_func()

        return wrapper

    return decorator


def safe_call(
    func: Callable[[], T],
    fallback: Optional[T] = None,
    log_level: int = logging.WARNING,
) -> Optional[T]:
    """Safely call a function with a fallback value."""
    try:
        return func()
    except Exception as e:
        logger.log(log_level, "Safe call execution failed: %s", e)
        return fallback


# ============================================================================
# Health Checker
# ============================================================================
class HealthChecker:
    """Aggregates and executes health check probes."""

    def __init__(self, name: str = "health_check") -> None:
        self.name = name
        self._checks: Dict[str, Callable[[], bool]] = {}

    def add_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Add a health check callback."""
        self._checks[name] = check_func

    def is_healthy(self) -> bool:
        """Check if all probes return True."""
        for check_func in self._checks.values():
            try:
                if not check_func():
                    return False
            except Exception:
                return False
        return True

    def get_report(self) -> Dict[str, bool]:
        """Get detailed status for each probe."""
        report: Dict[str, bool] = {}
        for name, check_func in self._checks.items():
            try:
                report[name] = bool(check_func())
            except Exception:
                report[name] = False
        return report

    def __repr__(self) -> str:
        return f"HealthChecker(name={self.name}, checks={len(self._checks)})"