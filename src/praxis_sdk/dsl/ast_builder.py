"""AST Builder for converting tokens to Abstract Syntax Tree.
Supports PARALLEL, SEQUENCE, CONDITIONAL nodes with nested structures.
Based on Go SDK parse function with Python enhancements.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from .tokenizer import TokenStream
from .types import (
    AST,
    TOOL_PARAMETER_MAPPING,
    ASTNode,
    DSLSyntaxError,
    DSLValidationError,
    NodeType,
    Token,
    TokenType,
)


class ASTBuilder:
    """Advanced AST builder that converts tokens to structured AST.
    Handles complex DSL structures including nested blocks and conditionals.
    """

    def __init__(self):
        self.logger = logger

    def build_ast(self, tokens: list[Token]) -> AST:
        """Build AST from token list.
        Main entry point for AST construction.

        Args:
            tokens: List of tokens to convert

        Returns:
            Complete AST structure

        Raises:
            DSLSyntaxError: If token structure is invalid
            DSLValidationError: If AST validation fails

        """
        if not tokens:
            return AST(nodes=[])

        stream = TokenStream(tokens)
        nodes = []

        try:
            while stream.has_more():
                node = self._parse_node(stream)
                if node:
                    nodes.append(node)

        except Exception as e:
            raise DSLSyntaxError(f"Failed to build AST: {str(e)}")

        ast = AST(nodes=nodes)

        # Validate the constructed AST
        self._validate_ast(ast)

        logger.debug(f"Built AST with {len(nodes)} top-level nodes")
        return ast

    def _parse_node(self, stream: TokenStream) -> ASTNode | None:
        """Parse a single AST node from token stream.
        Handles different node types and their specific parsing rules.

        Args:
            stream: Token stream to parse from

        Returns:
            Parsed AST node or None

        """
        token = stream.current()
        if not token:
            return None

        # Determine node type and parse accordingly
        command = token.value.upper()

        if command == "CALL":
            return self._parse_call_node(stream)
        if command == "PARALLEL":
            return self._parse_parallel_node(stream)
        if command == "SEQUENCE":
            return self._parse_sequence_node(stream)
        if command == "WORKFLOW":
            return self._parse_workflow_node(stream)
        if command == "TASK":
            return self._parse_task_node(stream)
        if command == "AGENT":
            return self._parse_agent_node(stream)
        if command == "IF":
            return self._parse_conditional_node(stream)
        # Default command parsing
        return self._parse_simple_command(stream)

    def _parse_call_node(self, stream: TokenStream) -> ASTNode:
        """Parse CALL node with tool name and arguments.
        Implements Go SDK CALL parsing logic with enhancements.

        Args:
            stream: Token stream

        Returns:
            CALL AST node

        """
        token = stream.advance()  # Consume CALL token

        if not token or not token.args:
            raise DSLSyntaxError("CALL command requires tool name")

        tool_name = token.args[0]

        # Parse arguments using Go SDK logic
        args_map = self._parse_tool_arguments(tool_name, token.args[1:])

        logger.debug(f"Parsed CALL node: tool={tool_name}, args={args_map}")

        return ASTNode(
            type=NodeType.CALL,
            value="CALL",
            tool_name=tool_name,
            args=args_map,
            metadata={"original_args": token.args},
        )

    def _parse_tool_arguments(self, tool_name: str, args: list[str]) -> dict[str, Any]:
        """Parse tool arguments with support for named and positional parameters.
        Based on Go SDK argument parsing logic with Python enhancements.

        Args:
            tool_name: Name of the tool
            args: List of argument strings

        Returns:
            Dictionary of parsed arguments

        """
        args_map = {}

        i = 0
        positional_count = 0

        while i < len(args):
            arg = args[i]

            if arg.startswith("--"):
                # Named parameter: --key value or --flag
                key = arg[2:]

                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    # Key-value pair: --key value
                    value = args[i + 1]
                    args_map[key] = self._parse_argument_value(value)
                    i += 2
                else:
                    # Boolean flag: --verbose
                    args_map[key] = True
                    i += 1
            else:
                # Positional argument - map to tool-specific parameter names
                param_name = self._get_positional_param_name(
                    tool_name, positional_count, args[i:]
                )

                if param_name:
                    if param_name == "content" and tool_name == "write_file":
                        # Special handling for write_file content - join remaining args
                        content = " ".join(args[i:])
                        # Remove quotes if present
                        content = content.strip("\"'")
                        args_map[param_name] = content
                        break
                    args_map[param_name] = self._parse_argument_value(arg)
                else:
                    # Generic fallback
                    args_map[f"arg{positional_count}"] = self._parse_argument_value(arg)

                positional_count += 1
                i += 1

        return args_map

    def _get_positional_param_name(
        self, tool_name: str, position: int, remaining_args: list[str]
    ) -> str | None:
        """Get parameter name for positional argument based on tool type.

        Args:
            tool_name: Name of the tool
            position: Position of the argument (0-based)
            remaining_args: Remaining arguments for context

        Returns:
            Parameter name or None

        """
        mapping = TOOL_PARAMETER_MAPPING.get(tool_name)
        if not mapping:
            return None

        params = mapping["params"]

        if position < len(params):
            return params[position]

        return None

    def _parse_argument_value(self, value: str) -> Any:
        """Parse argument value with type detection.

        Args:
            value: String value to parse

        Returns:
            Parsed value with appropriate type

        """
        # Remove surrounding quotes
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]

        # Try to parse as JSON for complex structures
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to parse as number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Try to parse as boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Return as string
        return value

    def _parse_parallel_node(self, stream: TokenStream) -> ASTNode:
        """Parse PARALLEL node with child nodes.

        Args:
            stream: Token stream

        Returns:
            PARALLEL AST node with children

        """
        stream.advance()  # Consume PARALLEL token

        children = []

        # Parse children until we hit a block terminator or end
        while stream.has_more():
            token = stream.current()
            if not token:
                break

            # Stop at block terminators or next block starters
            if token.value.upper() in ["END_PARALLEL", "SEQUENCE", "WORKFLOW", "IF"]:
                break

            child = self._parse_node(stream)
            if child:
                children.append(child)

        logger.debug(f"Parsed PARALLEL node with {len(children)} children")

        return ASTNode(
            type=NodeType.PARALLEL,
            value="PARALLEL",
            children=children,
            metadata={"execution_mode": "parallel"},
        )

    def _parse_sequence_node(self, stream: TokenStream) -> ASTNode:
        """Parse SEQUENCE node with ordered child nodes.

        Args:
            stream: Token stream

        Returns:
            SEQUENCE AST node with children

        """
        stream.advance()  # Consume SEQUENCE token

        children = []

        # Parse children in sequence
        while stream.has_more():
            token = stream.current()
            if not token:
                break

            # Stop at block terminators
            if token.value.upper() in ["END_SEQUENCE", "PARALLEL", "WORKFLOW", "IF"]:
                break

            child = self._parse_node(stream)
            if child:
                children.append(child)

        logger.debug(f"Parsed SEQUENCE node with {len(children)} children")

        return ASTNode(
            type=NodeType.SEQUENCE,
            value="SEQUENCE",
            children=children,
            metadata={"execution_mode": "sequence"},
        )

    def _parse_conditional_node(self, stream: TokenStream) -> ASTNode:
        """Parse conditional (IF/ELSE) node structure.

        Args:
            stream: Token stream

        Returns:
            CONDITIONAL AST node

        """
        token = stream.advance()  # Consume IF token

        # Parse condition expression
        condition_args = token.args if token and token.args else []
        condition = " ".join(condition_args) if condition_args else "true"

        # Parse IF block children
        if_children = []
        else_children = []
        current_block = if_children

        while stream.has_more():
            token = stream.current()
            if not token:
                break

            command = token.value.upper()

            if command == "ELSE":
                stream.advance()  # Consume ELSE token
                current_block = else_children
                continue
            if command in ["ENDIF", "END_IF"]:
                stream.advance()  # Consume terminator
                break
            if command in ["IF", "PARALLEL", "SEQUENCE", "WORKFLOW"]:
                # Nested blocks
                break

            child = self._parse_node(stream)
            if child:
                current_block.append(child)

        logger.debug(
            f"Parsed CONDITIONAL node: condition='{condition}', if_children={len(if_children)}, else_children={len(else_children)}"
        )

        return ASTNode(
            type=NodeType.CONDITIONAL,
            value="IF",
            children=if_children,
            args={"condition": condition, "else_children": else_children},
            metadata={"has_else": len(else_children) > 0},
        )

    def _parse_workflow_node(self, stream: TokenStream) -> ASTNode:
        """Parse WORKFLOW node.

        Args:
            stream: Token stream

        Returns:
            WORKFLOW AST node

        """
        token = stream.advance()  # Consume WORKFLOW token

        workflow_name = ""
        if token and token.args:
            workflow_name = token.args[0] if token.args else ""

        # Parse workflow arguments
        args = {}
        if token and token.args:
            for i in range(1, len(token.args), 2):
                if i + 1 < len(token.args):
                    key = token.args[i].lstrip("-")
                    value = token.args[i + 1]
                    args[key] = self._parse_argument_value(value)

        logger.debug(f"Parsed WORKFLOW node: name='{workflow_name}', args={args}")

        return ASTNode(
            type=NodeType.WORKFLOW,
            value="WORKFLOW",
            args={"name": workflow_name, **args},
            metadata={"workflow_name": workflow_name},
        )

    def _parse_task_node(self, stream: TokenStream) -> ASTNode:
        """Parse TASK node.

        Args:
            stream: Token stream

        Returns:
            TASK AST node

        """
        token = stream.advance()  # Consume TASK token

        task_name = ""
        if token and token.args:
            task_name = token.args[0] if token.args else ""

        # Parse task arguments
        args = {"name": task_name}
        if token and token.args:
            for i in range(1, len(token.args), 2):
                if i + 1 < len(token.args):
                    key = token.args[i].lstrip("-")
                    value = token.args[i + 1]
                    args[key] = self._parse_argument_value(value)

        logger.debug(f"Parsed TASK node: name='{task_name}', args={args}")

        return ASTNode(
            type=NodeType.TASK,
            value="TASK",
            args=args,
            metadata={"task_name": task_name},
        )

    def _parse_agent_node(self, stream: TokenStream) -> ASTNode:
        """Parse AGENT node.

        Args:
            stream: Token stream

        Returns:
            AGENT AST node

        """
        token = stream.advance()  # Consume AGENT token

        agent_id = ""
        if token and token.args:
            agent_id = token.args[0] if token.args else ""

        args = {"agent_id": agent_id}

        logger.debug(f"Parsed AGENT node: agent_id='{agent_id}'")

        return ASTNode(
            type=NodeType.AGENT,
            value="AGENT",
            args=args,
            metadata={"agent_id": agent_id},
        )

    def _parse_simple_command(self, stream: TokenStream) -> ASTNode:
        """Parse simple command node.

        Args:
            stream: Token stream

        Returns:
            COMMAND AST node

        """
        token = stream.advance()  # Consume command token

        if not token:
            return None

        # Convert args to map format
        args = {}
        if token.args:
            for i, arg in enumerate(token.args):
                args[f"arg{i}"] = self._parse_argument_value(arg)

        logger.debug(f"Parsed simple command: value='{token.value}', args={args}")

        return ASTNode(
            type=NodeType.COMMAND,
            value=token.value,
            args=args,
            metadata={"simple_command": True},
        )

    def _validate_ast(self, ast: AST):
        """Validate AST structure for consistency and correctness.

        Args:
            ast: AST to validate

        Raises:
            DSLValidationError: If validation fails

        """
        errors = []

        for i, node in enumerate(ast.nodes):
            try:
                self._validate_node(node, f"node[{i}]")
            except DSLValidationError as e:
                errors.append(str(e))

        if errors:
            raise DSLValidationError(f"AST validation failed: {'; '.join(errors)}")

    def _validate_node(self, node: ASTNode, path: str):
        """Validate individual AST node.

        Args:
            node: Node to validate
            path: Path to node for error reporting

        Raises:
            DSLValidationError: If validation fails

        """
        # Validate node type
        if not isinstance(node.type, NodeType):
            raise DSLValidationError(f"{path}: Invalid node type: {node.type}")

        # Type-specific validation
        if node.type == NodeType.CALL:
            if not node.tool_name:
                raise DSLValidationError(f"{path}: CALL node missing tool_name")
            if not isinstance(node.args, dict):
                raise DSLValidationError(f"{path}: CALL node args must be dictionary")

        elif node.type == NodeType.PARALLEL:
            if not node.children:
                raise DSLValidationError(f"{path}: PARALLEL node has no children")

        elif node.type == NodeType.SEQUENCE:
            if not node.children:
                raise DSLValidationError(f"{path}: SEQUENCE node has no children")

        elif node.type == NodeType.CONDITIONAL:
            if "condition" not in node.args:
                raise DSLValidationError(f"{path}: CONDITIONAL node missing condition")

        # Validate children recursively
        for i, child in enumerate(node.children):
            self._validate_node(child, f"{path}.children[{i}]")
