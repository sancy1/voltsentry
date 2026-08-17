"""
FILE: src/voltsentry/utils/__init__.py
PATH: voltsentry/src/voltsentry/utils/__init__.py
DESCRIPTION: Utilities module exports
"""

from .path_utils import get_resource_path
from .startup_utils import set_auto_start, is_auto_start_enabled, get_current_exe_path

__all__ = [
    "get_resource_path",
    "set_auto_start",
    "is_auto_start_enabled",
    "get_current_exe_path",
]