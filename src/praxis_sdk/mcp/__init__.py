"""MCP (Model Context Protocol) Integration for Praxis SDK

This module provides comprehensive MCP server and client functionality
for tool discovery, registration, and execution.
"""

from .client import MCPClient
from .registry import ToolRegistry
from .server import MCPServer
from .service import MCPService, mcp_service
from .tools.filesystem import FilesystemTools

__all__ = [
    "MCPServer",
    "MCPClient",
    "ToolRegistry",
    "FilesystemTools",
    "MCPService",
    "mcp_service",
]
