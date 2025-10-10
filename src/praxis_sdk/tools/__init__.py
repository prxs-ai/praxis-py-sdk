"""Tool Discovery and Registration Module
Automatically discovers and registers tools from the /tools directory with YAML contracts.
"""

from .discovery import discover_tools, validate_tool_contract
from .registry import ToolRegistry, load_tools_from_directory

__all__ = [
    "ToolRegistry",
    "load_tools_from_directory",
    "discover_tools",
    "validate_tool_contract",
]
