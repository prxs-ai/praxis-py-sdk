"""
Advanced DSL Tokenizer with support for nested quotes and escaping.
Based on Go SDK parseQuotedFields function with Python enhancements.
"""

import re
from typing import List, Optional, Tuple, Iterator
from loguru import logger

from .types import Token, TokenType, DSLSyntaxError, DSL_COMMAND_PATTERNS


class DSLTokenizer:
    """
    Advanced DSL tokenizer that handles:
    - Quoted strings with escape sequences
    - Nested quotes and complex arguments
    - Command detection and argument parsing  
    - Comment and empty line handling
    - Error reporting with line/position info
    """
    
    def __init__(self):
        self.line_number = 0
        self.position = 0
    
    def tokenize(self, dsl_content: str) -> List[Token]:
        """
        Tokenize complete DSL content into tokens.
        Handles multiline DSL with proper error reporting.
        
        Args:
            dsl_content: Complete DSL text to tokenize
            
        Returns:
            List of tokens
            
        Raises:
            DSLSyntaxError: If syntax is invalid
        """
        tokens = []
        
        lines = dsl_content.split('\n')
        self.line_number = 0
        
        for line in lines:
            self.line_number += 1
            self.position = 0
            
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            try:
                # Parse the line into fields respecting quotes
                fields = self.parse_quoted_fields(line)
                
                if fields:
                    # Create token from parsed fields
                    token = self._create_token_from_fields(fields, line)
                    if token:
                        tokens.append(token)
                        
            except DSLSyntaxError as e:
                # Re-raise with line context
                raise DSLSyntaxError(
                    e.message, 
                    line_number=self.line_number,
                    position=e.position
                )
            except Exception as e:
                raise DSLSyntaxError(
                    f"Unexpected error parsing line: {str(e)}",
                    line_number=self.line_number
                )
        
        logger.debug(f"Tokenized {len(tokens)} tokens from {self.line_number} lines")
        return tokens
    
    def parse_quoted_fields(self, line: str) -> List[str]:
        """
        Parse a line respecting quoted strings and escape sequences.
        Python implementation of Go SDK parseQuotedFields function.
        
        Args:
            line: Line to parse
            
        Returns:
            List of parsed fields
            
        Raises:
            DSLSyntaxError: If quotes are unmatched or invalid
        """
        fields = []
        current = []
        in_quotes = False
        escaped = False
        quote_char = None
        
        for i, char in enumerate(line):
            self.position = i
            
            # Handle escape sequences
            if escaped:
                current.append(char)
                escaped = False
                continue
            
            if char == '\\':
                escaped = True
                continue
            
            # Handle quotes
            if char in ('"', "'"):
                if in_quotes:
                    if char == quote_char:
                        # End of quoted string
                        if current:
                            fields.append(''.join(current))
                            current = []
                        in_quotes = False
                        quote_char = None
                        
                        # Skip whitespace after quote
                        while i + 1 < len(line) and line[i + 1] == ' ':
                            i += 1
                            
                    else:
                        # Different quote inside quoted string
                        current.append(char)
                else:
                    # Start of quoted string
                    if current:
                        # Add any unquoted content before quote
                        fields.append(''.join(current))
                        current = []
                    in_quotes = True
                    quote_char = char
                continue
            
            # Handle spaces
            if char == ' ' and not in_quotes:
                if current:
                    fields.append(''.join(current))
                    current = []
                # Skip consecutive spaces
                while i + 1 < len(line) and line[i + 1] == ' ':
                    i += 1
            else:
                current.append(char)
        
        # Handle end of line
        if escaped:
            raise DSLSyntaxError(
                "Line ends with escape character",
                position=len(line) - 1
            )
        
        if in_quotes:
            raise DSLSyntaxError(
                f"Unclosed quote ({quote_char})",
                position=self.position
            )
        
        # Add any remaining content
        if current:
            fields.append(''.join(current))
        
        return fields
    
    def _create_token_from_fields(self, fields: List[str], original_line: str) -> Optional[Token]:
        """
        Create a token from parsed fields.
        Determines token type and processes arguments.
        
        Args:
            fields: Parsed fields from line
            original_line: Original line for context
            
        Returns:
            Token or None if not a valid token
        """
        if not fields:
            return None
        
        command = fields[0].upper()
        args = fields[1:] if len(fields) > 1 else []
        
        # Determine token type based on command
        token_type = TokenType.COMMAND
        
        # Special handling for operators and values
        if command in ['|', '&&', '||', ';']:
            token_type = TokenType.OPERATOR
        elif not self._is_command(command):
            token_type = TokenType.VALUE
        
        logger.debug(f"Created token: type={token_type}, command={command}, args={args}")
        
        return Token(
            type=token_type,
            value=command,
            args=args
        )
    
    def _is_command(self, text: str) -> bool:
        """
        Check if text represents a valid DSL command.
        
        Args:
            text: Text to check
            
        Returns:
            True if text is a valid command
        """
        text_lower = text.lower()
        
        # Check against defined patterns
        for pattern_name in DSL_COMMAND_PATTERNS:
            if text_lower.startswith(pattern_name.lower()):
                return True
        
        # Check for common DSL keywords
        dsl_keywords = {
            'CALL', 'PARALLEL', 'SEQUENCE', 'WORKFLOW', 'TASK', 'AGENT',
            'IF', 'ELSE', 'ENDIF', 'WHILE', 'FOR', 'RETURN', 'BREAK',
            'CONTINUE', 'TRY', 'CATCH', 'FINALLY'
        }
        
        return text.upper() in dsl_keywords
    
    def validate_syntax(self, tokens: List[Token]) -> List[str]:
        """
        Validate token sequence for basic syntax errors.
        
        Args:
            tokens: List of tokens to validate
            
        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []
        
        # Basic validation rules
        if not tokens:
            warnings.append("Empty DSL")
            return warnings
        
        # Check for balanced PARALLEL/SEQUENCE blocks
        parallel_count = 0
        sequence_count = 0
        
        for i, token in enumerate(tokens):
            if token.value == 'PARALLEL':
                parallel_count += 1
            elif token.value == 'SEQUENCE':
                sequence_count += 1
            elif token.value == 'CALL':
                if not token.args:
                    warnings.append(f"Token {i}: CALL command missing tool name")
                elif len(token.args) < 1:
                    warnings.append(f"Token {i}: CALL command has no tool specified")
            
            # Validate argument structure
            if token.type == TokenType.COMMAND and token.value == 'CALL':
                if not self._validate_call_args(token.args):
                    warnings.append(f"Token {i}: Invalid CALL arguments: {token.args}")
        
        # Check for unbalanced blocks
        if parallel_count > 0 and parallel_count % 2 != 0:
            warnings.append("Unbalanced PARALLEL blocks")
        
        if sequence_count > 0 and sequence_count % 2 != 0:
            warnings.append("Unbalanced SEQUENCE blocks")
        
        return warnings
    
    def _validate_call_args(self, args: List[str]) -> bool:
        """
        Validate CALL command arguments.
        
        Args:
            args: Arguments to validate
            
        Returns:
            True if arguments are valid
        """
        if not args:
            return False
        
        # First argument must be tool name
        tool_name = args[0]
        if not tool_name or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tool_name):
            return False
        
        # Remaining arguments should be valid parameter format
        remaining_args = args[1:]
        
        i = 0
        while i < len(remaining_args):
            arg = remaining_args[i]
            
            if arg.startswith('--'):
                # Named parameter: --key value or --flag
                key = arg[2:]
                if not key or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                    return False
                
                # Check if next argument is value (not another flag)
                if i + 1 < len(remaining_args) and not remaining_args[i + 1].startswith('--'):
                    i += 2  # Skip key and value
                else:
                    i += 1  # Just a flag
            else:
                # Positional argument - always valid
                i += 1
        
        return True
    
    def get_line_info(self) -> Tuple[int, int]:
        """
        Get current line and position information.
        
        Returns:
            Tuple of (line_number, position)
        """
        return self.line_number, self.position


class TokenStream:
    """
    Token stream for advanced parsing with lookahead and backtracking.
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.length = len(tokens)
    
    def current(self) -> Optional[Token]:
        """Get current token without advancing."""
        if self.position < self.length:
            return self.tokens[self.position]
        return None
    
    def peek(self, offset: int = 1) -> Optional[Token]:
        """Peek at token at offset from current position."""
        peek_pos = self.position + offset
        if peek_pos < self.length:
            return self.tokens[peek_pos]
        return None
    
    def advance(self) -> Optional[Token]:
        """Advance to next token and return current."""
        token = self.current()
        if token:
            self.position += 1
        return token
    
    def has_more(self) -> bool:
        """Check if there are more tokens."""
        return self.position < self.length
    
    def reset(self):
        """Reset stream to beginning."""
        self.position = 0
    
    def save_position(self) -> int:
        """Save current position for backtracking."""
        return self.position
    
    def restore_position(self, position: int):
        """Restore position for backtracking."""
        self.position = min(position, self.length)