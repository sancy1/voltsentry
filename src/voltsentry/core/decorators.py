# File: decorators.py
# Path: voltsentry/src/voltsentry/core/decorators.py
# Description: Reusable decorators for DRY code patterns including logging, timing, retry, exception handling, and singletons.

import functools
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, ParamSpec, Type, TypeVar

from voltsentry.core.logging_config import get_logger
from voltsentry.core.resilience import DEFAULT_RETRY_ATTEMPTS, DEFAULT_RETRY_MAX_WAIT, resilient

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")
C = TypeVar("C", bound=Type[Any])


def log_entry_exit(level: int = logging.DEBUG, log_args: bool = False) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to log function entry and exit.

    Example:
        @log_entry_exit()
        def process_battery(percent: int) -> None:
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            func_name = func.__qualname__
            logger.log(level, "→ Entering %s", func_name)

            if log_args and (args or kwargs):
                logger.log(level, "  Args: %s, Kwargs: %s", args, kwargs)

            try:
                result = func(*args, **kwargs)
                logger.log(level, "← Exiting %s", func_name)
                return result
            except Exception as e:
                logger.error("✗ %s raised %s", func_name, type(e).__name__)
                raise

        return wrapper

    return decorator


def timed(log_level: int = logging.DEBUG) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to time function execution.

    Example:
        @timed()
        def expensive_operation():
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            func_name = func.__qualname__
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.log(log_level, "%s took %.3f ms", func_name, elapsed * 1000)
                return result
            except Exception:
                elapsed = time.perf_counter() - start
                logger.error("%s failed after %.3f ms", func_name, elapsed * 1000)
                raise

        return wrapper

    return decorator


def with_retry(
    attempts: int = DEFAULT_RETRY_ATTEMPTS,
    max_wait: int = DEFAULT_RETRY_MAX_WAIT,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to retry a function on specified exceptions.

    Example:
        @with_retry(attempts=3)
        def read_battery():
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Wrap once at decoration time rather than every invocation
        retry_wrapped = resilient(
            exceptions=exceptions,
            attempts=attempts,
            max_wait=max_wait,
        )(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return retry_wrapped(*args, **kwargs)

        return wrapper

    return decorator


def handle_exceptions(
    fallback_return: Optional[Any] = None,
    log_level: int = logging.ERROR,
    reraise: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, Optional[T]]]:
    """Decorator to handle exceptions gracefully with fallback.

    Example:
        @handle_exceptions(fallback_return=None, log_level=logging.WARNING)
        def get_battery():
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, Optional[T]]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[T]:
            func_name = func.__qualname__
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.log(log_level, "%s failed: %s", func_name, e)
                if reraise:
                    raise
                return fallback_return

        return wrapper

    return decorator


def singleton(cls: C) -> C:
    """Thread-safe singleton decorator for classes.

    Example:
        @singleton
        class ConfigManager:
            pass
    """
    instances: Dict[Any, Any] = {}

    @wraps(cls)
    def get_instance(*args: Any, **kwargs: Any) -> Any:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance  # type: ignore[return-value]


def ensure_initialized(attr_name: str = "_initialized") -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to ensure a class method is only called after initialization.

    Example:
        class MyService:
            @ensure_initialized()
            def start(self):
                pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> T:
            if not hasattr(self, attr_name) or not getattr(self, attr_name):
                raise RuntimeError(f"{self.__class__.__name__} is not initialized")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def deprecated(replacement: Optional[str] = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to mark a function as deprecated.

    Example:
        @deprecated(replacement="new_function")
        def old_function():
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            msg = f"Deprecated: {func.__qualname__}"
            if replacement:
                msg += f" (use {replacement} instead)"
            logger.warning(msg)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Class-level decorators
# ============================================================================
def auto_log(level: int = logging.DEBUG) -> Callable[[C], C]:
    """Class decorator to automatically log all public method entries/exits.

    Example:
        @auto_log()
        class MyService:
            def do_work(self):
                pass
    """
    def decorator(cls: C) -> C:
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and not attr_name.startswith("_"):
                setattr(cls, attr_name, log_entry_exit(level)(attr_value))
        return cls

    return decorator