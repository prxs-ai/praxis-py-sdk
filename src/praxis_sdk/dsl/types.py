"""
DSL Types and Data Structures for Advanced DSL Processing Engine.
Based on Go SDK analyzer.go implementation with Python enhancements.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime


class TokenType(str, Enum):
    """Token types for DSL parsing."""
    COMMAND = "command"
    OPERATOR = "operator"
    VALUE = "value"


class NodeType(str, Enum):
    """AST node types matching Go SDK implementation."""
    COMMAND = "command"
    WORKFLOW = "workflow"
    TASK = "task"
    AGENT = "agent"
    CALL = "call"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"
    CONDITIONAL = "conditional"


@dataclass
class Token:
    """
    Token representation for DSL parsing.
    Matches Go SDK Token struct.
    """
    type: TokenType
    value: str
    args: List[str] = field(default_factory=list)


@dataclass
class ASTNode:
    """
    AST node representation matching Go SDK ASTNode struct.
    Enhanced with Python-specific features.
    """
    type: NodeType
    value: str
    tool_name: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    children: List["ASTNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "value": self.value,
            "tool_name": self.tool_name,
            "args": self.args,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ASTNode":
        """Create node from dictionary."""
        children = [cls.from_dict(child) for child in data.get("children", [])]
        return cls(
            type=NodeType(data["type"]),
            value=data["value"],
            tool_name=data.get("tool_name"),
            args=data.get("args", {}),
            children=children,
            metadata=data.get("metadata", {})
        )


@dataclass
class AST:
    """
    Abstract Syntax Tree representation.
    Matches Go SDK AST struct with enhancements.
    """
    nodes: List[ASTNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AST to dictionary for JSON serialization."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AST":
        """Create AST from dictionary."""
        nodes = [ASTNode.from_dict(node) for node in data.get("nodes", [])]
        created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        return cls(
            nodes=nodes,
            metadata=data.get("metadata", {}),
            created_at=created_at
        )


@dataclass
class ExecutionContext:
    """
    Execution context for DSL commands.
    Contains runtime information and state.
    """
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    agent_capabilities: List[str] = field(default_factory=list)
    p2p_peers: List[str] = field(default_factory=list)
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """
    Result of DSL execution.
    Comprehensive result structure for analysis and reporting.
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    cache_hit: bool = False
    executed_by: Optional[str] = None  # local or peer_id
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "tool_calls": self.tool_calls,
            "cache_hit": self.cache_hit,
            "executed_by": self.executed_by,
            "metadata": self.metadata
        }


@dataclass
class CacheEntry:
    """
    Cache entry for tool execution results.
    Based on Go SDK ToolCacheEntry.
    """
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: int = 300  # 5 minutes default


class DSLSyntaxError(Exception):
    """Custom exception for DSL syntax errors."""
    
    def __init__(self, message: str, line_number: Optional[int] = None, position: Optional[int] = None):
        self.message = message
        self.line_number = line_number
        self.position = position
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with context."""
        if self.line_number is not None and self.position is not None:
            return f"DSL Syntax Error at line {self.line_number}, position {self.position}: {self.message}"
        elif self.line_number is not None:
            return f"DSL Syntax Error at line {self.line_number}: {self.message}"
        else:
            return f"DSL Syntax Error: {self.message}"


class DSLValidationError(Exception):
    """Custom exception for DSL validation errors."""
    pass


class DSLExecutionError(Exception):
    """Custom exception for DSL execution errors."""
    pass


# Utility functions for cache key generation matching Go implementation
def generate_cache_key(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Generate cache key for tool execution.
    Matches Go SDK GenerateCacheKey function.
    """
    try:
        args_json = json.dumps(args, sort_keys=True)
        return f"{tool_name}:{args_json}"
    except (TypeError, ValueError):
        # If serialization fails, just use the tool name
        return tool_name


# Pattern definitions for common DSL commands
DSL_COMMAND_PATTERNS = {
    "read": r"^read\s+(.+)$",
    "write": r"^write\s+(.+?)\s+(.+)$",
    "list": r"^list(?:\s+(.+))?$",
    "exec": r"^exec\s+(.+?)\s+(.*)$",
    "tool": r"^tool\s+(.+?)\s+(.*)$",
    "help": r"^help(?:\s+(.+))?$",
    "call": r"^CALL\s+(.+?)(?:\s+(.*))?$",
    "parallel": r"^PARALLEL$",
    "sequence": r"^SEQUENCE$",
    "workflow": r"^WORKFLOW(?:\s+(.+))?$",
    "task": r"^TASK(?:\s+(.+))?$",
    "agent": r"^AGENT(?:\s+(.+))?$",
}


# Tool name to parameter mapping for backward compatibility
TOOL_PARAMETER_MAPPING = {
    "read_file": {"primary_arg": "filename", "params": ["filename", "encoding"]},
    "write_file": {"primary_arg": "filename", "params": ["filename", "content", "encoding"]},
    "delete_file": {"primary_arg": "filename", "params": ["filename"]},
    "list_files": {"primary_arg": "directory", "params": ["directory", "pattern", "recursive"]},
    "list_directory": {"primary_arg": "directory", "params": ["directory", "pattern", "recursive"]},
    "create_directory": {"primary_arg": "directory", "params": ["directory", "recursive"]},
    "move_file": {"primary_arg": "source", "params": ["source", "destination"]},
    "copy_file": {"primary_arg": "source", "params": ["source", "destination"]},
    "search_files": {"primary_arg": "pattern", "params": ["pattern", "directory", "recursive"]},
}