"""
DSL (Domain-Specific Language) module for Praxis SDK.

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

from .orchestrator import DSLOrchestrator
from .parser import AdvancedDSLParser, AgentInterface
from .tokenizer import DSLTokenizer, TokenStream
from .ast_builder import ASTBuilder
from .validator import DSLValidator, ValidationResult, ValidationLevel
from .cache import ToolExecutionCache, CacheKeyBuilder
from .planner import TaskPlanner, NetworkContext, WorkflowPlan
from .types import (
    AST, ASTNode, NodeType, Token, TokenType,
    ExecutionContext, ExecutionResult, CacheEntry,
    DSLSyntaxError, DSLValidationError, DSLExecutionError,
    generate_cache_key
)

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
    "generate_cache_key"
]