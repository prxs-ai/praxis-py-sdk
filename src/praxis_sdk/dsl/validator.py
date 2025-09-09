"""
DSL Validation Engine for workflow correctness.
Comprehensive validation of DSL syntax, semantics, and execution constraints.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from loguru import logger

from .types import (
    AST, ASTNode, NodeType, Token, TokenType,
    DSLSyntaxError, DSLValidationError, TOOL_PARAMETER_MAPPING
)


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult:
    """Result of validation with details."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.is_valid: bool = True
        self.summary: Dict[str, int] = {"errors": 0, "warnings": 0, "info": 0}
    
    def add_issue(
        self, 
        level: ValidationLevel, 
        message: str, 
        node_path: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> None:
        """Add validation issue."""
        self.issues.append({
            "level": level.value,
            "message": message,
            "node_path": node_path,
            "suggestion": suggestion,
            "timestamp": logger.opt(depth=1).info.__self__.now().isoformat()
        })
        
        self.summary[level.value + "s"] += 1
        
        if level == ValidationLevel.ERROR:
            self.is_valid = False
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get only error-level issues."""
        return [issue for issue in self.issues if issue["level"] == "error"]
    
    def get_warnings(self) -> List[Dict[str, Any]]:
        """Get only warning-level issues."""
        return [issue for issue in self.issues if issue["level"] == "warning"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "summary": self.summary,
            "issues": self.issues
        }


class DSLValidator:
    """
    Comprehensive DSL validator for syntax, semantics, and execution constraints.
    Validates AST structures, tool availability, parameter correctness, and workflow logic.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Built-in tool schemas for validation
        self.tool_schemas = {
            "read_file": {
                "required": ["filename"],
                "optional": ["encoding"],
                "types": {"filename": str, "encoding": str}
            },
            "write_file": {
                "required": ["filename", "content"],
                "optional": ["encoding", "append"],
                "types": {"filename": str, "content": str, "encoding": str, "append": bool}
            },
            "list_files": {
                "required": [],
                "optional": ["directory", "pattern", "recursive"],
                "types": {"directory": str, "pattern": str, "recursive": bool}
            },
            "delete_file": {
                "required": ["filename"],
                "optional": [],
                "types": {"filename": str}
            },
            "create_directory": {
                "required": ["directory"],
                "optional": ["recursive"],
                "types": {"directory": str, "recursive": bool}
            }
        }
        
        # Reserved keywords that cannot be used as variables
        self.reserved_keywords = {
            "CALL", "PARALLEL", "SEQUENCE", "WORKFLOW", "TASK", "AGENT",
            "IF", "ELSE", "ENDIF", "WHILE", "FOR", "RETURN", "BREAK", "CONTINUE",
            "TRY", "CATCH", "FINALLY", "TRUE", "FALSE", "NULL", "NONE"
        }
    
    def validate_tokens(self, tokens: List[Token]) -> ValidationResult:
        """
        Validate token sequence for basic syntax issues.
        
        Args:
            tokens: List of tokens to validate
            
        Returns:
            Validation result with issues found
        """
        result = ValidationResult()
        
        if not tokens:
            result.add_issue(
                ValidationLevel.WARNING,
                "Empty token sequence",
                suggestion="Add some DSL commands"
            )
            return result
        
        # Check for basic token structure issues
        self._validate_token_structure(tokens, result)
        
        # Check for balanced blocks
        self._validate_balanced_blocks(tokens, result)
        
        # Check for valid command sequences
        self._validate_command_sequences(tokens, result)
        
        self.logger.debug(f"Token validation completed: {result.summary}")
        return result
    
    def validate_ast(self, ast: AST, available_tools: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate AST structure for semantic correctness.
        
        Args:
            ast: AST to validate
            available_tools: List of available tool names
            
        Returns:
            Validation result with issues found
        """
        result = ValidationResult()
        
        if not ast.nodes:
            result.add_issue(
                ValidationLevel.WARNING,
                "Empty AST - no nodes to execute",
                suggestion="Add some workflow nodes"
            )
            return result
        
        # Validate each node recursively
        for i, node in enumerate(ast.nodes):
            self._validate_node(node, f"ast.nodes[{i}]", result, available_tools)
        
        # Validate overall AST structure
        self._validate_ast_structure(ast, result)
        
        self.logger.debug(f"AST validation completed: {result.summary}")
        return result
    
    def validate_workflow_logic(self, ast: AST) -> ValidationResult:
        """
        Validate workflow execution logic and dependencies.
        
        Args:
            ast: AST to validate for workflow logic
            
        Returns:
            Validation result with logic issues
        """
        result = ValidationResult()
        
        # Check for data flow issues
        self._validate_data_flow(ast, result)
        
        # Check for execution order dependencies
        self._validate_execution_dependencies(ast, result)
        
        # Check for resource conflicts
        self._validate_resource_conflicts(ast, result)
        
        # Check for performance issues
        self._validate_performance_concerns(ast, result)
        
        self.logger.debug(f"Workflow logic validation completed: {result.summary}")
        return result
    
    def _validate_token_structure(self, tokens: List[Token], result: ValidationResult) -> None:
        """Validate basic token structure."""
        for i, token in enumerate(tokens):
            token_path = f"tokens[{i}]"
            
            # Check for empty values
            if not token.value:
                result.add_issue(
                    ValidationLevel.ERROR,
                    "Token has empty value",
                    token_path,
                    "Ensure all tokens have valid values"
                )
            
            # Check for reserved keyword conflicts
            if token.value.upper() in self.reserved_keywords and token.type == TokenType.VALUE:
                result.add_issue(
                    ValidationLevel.WARNING,
                    f"Using reserved keyword '{token.value}' as value",
                    token_path,
                    "Consider using a different name"
                )
            
            # Validate command-specific arguments
            if token.value.upper() == "CALL":
                self._validate_call_token(token, token_path, result)
    
    def _validate_call_token(self, token: Token, token_path: str, result: ValidationResult) -> None:
        """Validate CALL token arguments."""
        if not token.args:
            result.add_issue(
                ValidationLevel.ERROR,
                "CALL command missing tool name",
                token_path,
                "Add tool name after CALL command"
            )
            return
        
        tool_name = token.args[0]
        
        # Validate tool name format
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tool_name):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Invalid tool name format: '{tool_name}'",
                f"{token_path}.args[0]",
                "Tool names must start with letter/underscore and contain only letters, numbers, underscores"
            )
        
        # Validate argument structure
        args = token.args[1:]
        self._validate_argument_structure(args, f"{token_path}.args[1:]", result)
    
    def _validate_argument_structure(self, args: List[str], args_path: str, result: ValidationResult) -> None:
        """Validate argument structure for proper key-value pairing."""
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('--'):
                key = arg[2:]
                
                # Validate key format
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                    result.add_issue(
                        ValidationLevel.ERROR,
                        f"Invalid argument key format: '--{key}'",
                        f"{args_path}[{i}]",
                        "Argument keys must start with letter/underscore"
                    )
                
                # Check if next argument is value
                if i + 1 < len(args) and not args[i + 1].startswith('--'):
                    i += 2  # Skip key-value pair
                else:
                    i += 1  # Just a flag
            else:
                # Positional argument
                i += 1
    
    def _validate_balanced_blocks(self, tokens: List[Token], result: ValidationResult) -> None:
        """Validate balanced block structures."""
        block_stack = []
        
        for i, token in enumerate(tokens):
            command = token.value.upper()
            
            if command in ['PARALLEL', 'SEQUENCE', 'IF']:
                block_stack.append((command, i))
            elif command in ['END_PARALLEL', 'END_SEQUENCE', 'ENDIF', 'END_IF']:
                if not block_stack:
                    result.add_issue(
                        ValidationLevel.ERROR,
                        f"Unexpected block terminator '{command}' without opening block",
                        f"tokens[{i}]",
                        "Add matching opening block command"
                    )
                    continue
                
                expected_end = self._get_expected_block_end(block_stack[-1][0])
                if command not in expected_end:
                    opening_command, opening_pos = block_stack[-1]
                    result.add_issue(
                        ValidationLevel.ERROR,
                        f"Mismatched block terminator '{command}' for '{opening_command}' at position {opening_pos}",
                        f"tokens[{i}]",
                        f"Use {' or '.join(expected_end)} to close {opening_command} block"
                    )
                else:
                    block_stack.pop()
            elif command == 'ELSE':
                if not block_stack or block_stack[-1][0] != 'IF':
                    result.add_issue(
                        ValidationLevel.ERROR,
                        "ELSE command without matching IF block",
                        f"tokens[{i}]",
                        "ELSE must be inside an IF block"
                    )
        
        # Check for unclosed blocks
        for command, pos in block_stack:
            expected_end = self._get_expected_block_end(command)
            result.add_issue(
                ValidationLevel.ERROR,
                f"Unclosed '{command}' block started at position {pos}",
                f"tokens[{pos}]",
                f"Add {' or '.join(expected_end)} to close the block"
            )
    
    def _get_expected_block_end(self, command: str) -> List[str]:
        """Get expected block terminator commands."""
        endings = {
            'PARALLEL': ['END_PARALLEL'],
            'SEQUENCE': ['END_SEQUENCE'],
            'IF': ['ENDIF', 'END_IF']
        }
        return endings.get(command, [])
    
    def _validate_command_sequences(self, tokens: List[Token], result: ValidationResult) -> None:
        """Validate logical command sequences."""
        for i in range(len(tokens) - 1):
            current = tokens[i].value.upper()
            next_cmd = tokens[i + 1].value.upper()
            
            # Check for invalid sequences
            if current == 'ELSE' and next_cmd == 'IF':
                result.add_issue(
                    ValidationLevel.WARNING,
                    "ELSE followed by IF - consider using ELIF if supported",
                    f"tokens[{i}]-tokens[{i+1}]",
                    "Use nested IF blocks or implement ELIF logic"
                )
            
            # Check for redundant sequences
            if current == next_cmd and current in ['PARALLEL', 'SEQUENCE']:
                result.add_issue(
                    ValidationLevel.WARNING,
                    f"Consecutive {current} blocks may be redundant",
                    f"tokens[{i}]-tokens[{i+1}]",
                    "Consider merging blocks or adding meaningful separation"
                )
    
    def _validate_node(
        self, 
        node: ASTNode, 
        node_path: str, 
        result: ValidationResult,
        available_tools: Optional[List[str]] = None
    ) -> None:
        """Validate individual AST node."""
        # Validate node type
        if not isinstance(node.type, NodeType):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Invalid node type: {node.type}",
                node_path,
                "Use valid NodeType enum values"
            )
            return
        
        # Node-specific validation
        if node.type == NodeType.CALL:
            self._validate_call_node(node, node_path, result, available_tools)
        elif node.type == NodeType.PARALLEL:
            self._validate_parallel_node(node, node_path, result)
        elif node.type == NodeType.SEQUENCE:
            self._validate_sequence_node(node, node_path, result)
        elif node.type == NodeType.CONDITIONAL:
            self._validate_conditional_node(node, node_path, result)
        elif node.type == NodeType.WORKFLOW:
            self._validate_workflow_node(node, node_path, result)
        elif node.type == NodeType.TASK:
            self._validate_task_node(node, node_path, result)
        
        # Validate children recursively
        for i, child in enumerate(node.children):
            self._validate_node(child, f"{node_path}.children[{i}]", result, available_tools)
    
    def _validate_call_node(
        self, 
        node: ASTNode, 
        node_path: str, 
        result: ValidationResult,
        available_tools: Optional[List[str]] = None
    ) -> None:
        """Validate CALL node."""
        if not node.tool_name:
            result.add_issue(
                ValidationLevel.ERROR,
                "CALL node missing tool_name",
                f"{node_path}.tool_name",
                "Set tool_name for CALL nodes"
            )
            return
        
        # Check tool availability
        if available_tools and node.tool_name not in available_tools:
            result.add_issue(
                ValidationLevel.ERROR,
                f"Tool '{node.tool_name}' not available",
                f"{node_path}.tool_name",
                f"Available tools: {', '.join(available_tools[:5])}{'...' if len(available_tools) > 5 else ''}"
            )
        
        # Validate tool arguments
        if node.tool_name in self.tool_schemas:
            self._validate_tool_arguments(node, node_path, result)
    
    def _validate_tool_arguments(self, node: ASTNode, node_path: str, result: ValidationResult) -> None:
        """Validate tool arguments against schema."""
        schema = self.tool_schemas[node.tool_name]
        args = node.args or {}
        
        # Check required arguments
        for required_arg in schema["required"]:
            if required_arg not in args:
                result.add_issue(
                    ValidationLevel.ERROR,
                    f"Missing required argument '{required_arg}' for tool '{node.tool_name}'",
                    f"{node_path}.args",
                    f"Add '{required_arg}' argument"
                )
        
        # Check argument types
        for arg_name, arg_value in args.items():
            expected_type = schema.get("types", {}).get(arg_name)
            if expected_type and not isinstance(arg_value, expected_type):
                result.add_issue(
                    ValidationLevel.WARNING,
                    f"Argument '{arg_name}' expected type {expected_type.__name__}, got {type(arg_value).__name__}",
                    f"{node_path}.args.{arg_name}",
                    f"Convert value to {expected_type.__name__}"
                )
        
        # Check for unknown arguments
        all_valid_args = set(schema["required"] + schema.get("optional", []))
        for arg_name in args:
            if arg_name not in all_valid_args:
                result.add_issue(
                    ValidationLevel.WARNING,
                    f"Unknown argument '{arg_name}' for tool '{node.tool_name}'",
                    f"{node_path}.args.{arg_name}",
                    f"Valid arguments: {', '.join(all_valid_args)}"
                )
    
    def _validate_parallel_node(self, node: ASTNode, node_path: str, result: ValidationResult) -> None:
        """Validate PARALLEL node."""
        if not node.children:
            result.add_issue(
                ValidationLevel.ERROR,
                "PARALLEL node has no children",
                f"{node_path}.children",
                "Add child nodes for parallel execution"
            )
            return
        
        if len(node.children) == 1:
            result.add_issue(
                ValidationLevel.WARNING,
                "PARALLEL node with single child may be unnecessary",
                f"{node_path}.children",
                "Consider removing PARALLEL wrapper or adding more children"
            )
    
    def _validate_sequence_node(self, node: ASTNode, node_path: str, result: ValidationResult) -> None:
        """Validate SEQUENCE node."""
        if not node.children:
            result.add_issue(
                ValidationLevel.ERROR,
                "SEQUENCE node has no children",
                f"{node_path}.children",
                "Add child nodes for sequential execution"
            )
    
    def _validate_conditional_node(self, node: ASTNode, node_path: str, result: ValidationResult) -> None:
        """Validate CONDITIONAL node."""
        condition = node.args.get("condition")
        if not condition:
            result.add_issue(
                ValidationLevel.ERROR,
                "CONDITIONAL node missing condition",
                f"{node_path}.args.condition",
                "Add condition expression for IF node"
            )
        
        if not node.children and not node.args.get("else_children"):
            result.add_issue(
                ValidationLevel.WARNING,
                "CONDITIONAL node with no children in either branch",
                f"{node_path}",
                "Add commands to IF or ELSE branches"
            )
    
    def _validate_workflow_node(self, node: ASTNode, node_path: str, result: ValidationResult) -> None:
        """Validate WORKFLOW node."""
        workflow_name = node.args.get("name")
        if not workflow_name:
            result.add_issue(
                ValidationLevel.WARNING,
                "WORKFLOW node without name",
                f"{node_path}.args.name",
                "Consider adding descriptive workflow name"
            )
    
    def _validate_task_node(self, node: ASTNode, node_path: str, result: ValidationResult) -> None:
        """Validate TASK node."""
        task_name = node.args.get("name")
        if not task_name:
            result.add_issue(
                ValidationLevel.WARNING,
                "TASK node without name",
                f"{node_path}.args.name",
                "Consider adding descriptive task name"
            )
    
    def _validate_ast_structure(self, ast: AST, result: ValidationResult) -> None:
        """Validate overall AST structure."""
        # Check for deeply nested structures
        max_depth = self._calculate_max_depth(ast)
        if max_depth > 10:
            result.add_issue(
                ValidationLevel.WARNING,
                f"Deeply nested structure (depth: {max_depth})",
                "ast",
                "Consider flattening nested structures for better performance"
            )
        
        # Check for excessive parallel branches
        max_parallel_children = self._find_max_parallel_children(ast)
        if max_parallel_children > 20:
            result.add_issue(
                ValidationLevel.WARNING,
                f"High parallel execution count ({max_parallel_children} branches)",
                "ast",
                "Consider limiting parallel branches to avoid resource exhaustion"
            )
    
    def _calculate_max_depth(self, ast: AST) -> int:
        """Calculate maximum nesting depth of AST."""
        def node_depth(node: ASTNode) -> int:
            if not node.children:
                return 1
            return 1 + max(node_depth(child) for child in node.children)
        
        if not ast.nodes:
            return 0
        return max(node_depth(node) for node in ast.nodes)
    
    def _find_max_parallel_children(self, ast: AST) -> int:
        """Find maximum number of parallel children in any PARALLEL node."""
        def check_node(node: ASTNode) -> int:
            max_children = 0
            
            if node.type == NodeType.PARALLEL:
                max_children = len(node.children)
            
            for child in node.children:
                child_max = check_node(child)
                max_children = max(max_children, child_max)
            
            return max_children
        
        if not ast.nodes:
            return 0
        return max(check_node(node) for node in ast.nodes)
    
    def _validate_data_flow(self, ast: AST, result: ValidationResult) -> None:
        """Validate data flow between nodes."""
        # This would check for proper data dependencies
        # For now, just check for obvious issues
        pass
    
    def _validate_execution_dependencies(self, ast: AST, result: ValidationResult) -> None:
        """Validate execution order dependencies."""
        # Check for operations that require sequential execution but are in parallel blocks
        pass
    
    def _validate_resource_conflicts(self, ast: AST, result: ValidationResult) -> None:
        """Validate for potential resource conflicts."""
        # Check for concurrent file operations on same files
        pass
    
    def _validate_performance_concerns(self, ast: AST, result: ValidationResult) -> None:
        """Validate for potential performance issues."""
        # Check for expensive operations in tight loops
        pass