"""
FILE: src/voltsentry/__init__.py
PATH: voltsentry/src/voltsentry/__init__.py
DESCRIPTION: VoltSentry package exports
"""

from .app import VoltSentryApplication, create_app, main
from .core.config import VoltSentrySettings, get_config
from .core.exceptions import VoltSentryError
from .core.logging_config import setup_logging

__version__ = "1.0.0"
__app_name__ = "VoltSentry"
__app_id__ = "com.voltsentry.app"

__all__ = [
    "__version__",
    "__app_name__",
    "__app_id__",
    "VoltSentryApplication",
    "create_app",
    "main",
    "VoltSentrySettings",
    "get_config",
    "setup_logging",
    "VoltSentryError",
]