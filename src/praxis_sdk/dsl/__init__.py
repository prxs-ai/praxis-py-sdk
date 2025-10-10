"""DSL (Domain-Specific Language) module for Praxis SDK.

This module provides advanced DSL parsing, orchestration, and execution capabilities
including tokenization, AST generation, validation, caching, and natural language planning.

Components:
- Advanced DSL Parser with AST support
- Tokenizer with nested quotes and escaping
- AST Builder for PARALLEL, SEQUENCE, CONDITIONAL nodes
- Validation Engine for workflow correctness
- Tool Execution Cache for performance optimization
- Task Planner for natural language to workflow conversion
- Enhanced DSL Orchestrator with A2A integration
"""

from .ast_builder import ASTBuilder
from .cache import CacheKeyBuilder, ToolExecutionCache
from .orchestrator import DSLOrchestrator
from .parser import AdvancedDSLParser, AgentInterface
from .planner import NetworkContext, TaskPlanner, WorkflowPlan
from .tokenizer import DSLTokenizer, TokenStream
from .types import (
    AST,
    ASTNode,
    CacheEntry,
    DSLExecutionError,
    DSLSyntaxError,
    DSLValidationError,
    ExecutionContext,
    ExecutionResult,
    NodeType,
    Token,
    TokenType,
    generate_cache_key,
)
from .validator import DSLValidator, ValidationLevel, ValidationResult

__all__ = [
    # Main interfaces
    "DSLOrchestrator",
    "AdvancedDSLParser",
    "AgentInterface",
    # Core components
    "DSLTokenizer",
    "TokenStream",
    "ASTBuilder",
    "DSLValidator",
    "ValidationResult",
    "ValidationLevel",
    "ToolExecutionCache",
    "CacheKeyBuilder",
    "TaskPlanner",
    # Data structures
    "AST",
    "ASTNode",
    "NodeType",
    "Token",
    "TokenType",
    "ExecutionContext",
    "ExecutionResult",
    "CacheEntry",
    "NetworkContext",
    "WorkflowPlan",
    # Exceptions
    "DSLSyntaxError",
    "DSLValidationError",
    "DSLExecutionError",
    # Utilities
    "generate_cache_key",
]
