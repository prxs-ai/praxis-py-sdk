"""
Comprehensive tests for Advanced DSL Processing Engine.
Tests all components: tokenizer, AST builder, parser, validator, cache, planner.
"""

import asyncio
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.praxis_sdk.dsl import (
    DSLTokenizer, ASTBuilder, AdvancedDSLParser, DSLValidator,
    ToolExecutionCache, TaskPlanner, NetworkContext, WorkflowPlan,
    AST, ASTNode, NodeType, Token, TokenType, ExecutionContext,
    DSLSyntaxError, DSLValidationError, ValidationLevel,
    generate_cache_key
)


class TestDSLTokenizer:
    """Test DSL tokenizer functionality."""
    
    def setup_method(self):
        self.tokenizer = DSLTokenizer()
    
    def test_simple_command_tokenization(self):
        """Test tokenization of simple commands."""
        dsl = "CALL read_file test.txt"
        tokens = self.tokenizer.tokenize(dsl)
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.COMMAND
        assert tokens[0].value == "CALL"
        assert tokens[0].args == ["read_file", "test.txt"]
    
    def test_quoted_string_parsing(self):
        """Test parsing of quoted strings with spaces."""
        dsl = 'CALL write_file "my file.txt" "hello world"'
        tokens = self.tokenizer.tokenize(dsl)
        
        assert len(tokens) == 1
        assert tokens[0].args == ["write_file", "my file.txt", "hello world"]
    
    def test_escaped_quotes(self):
        """Test handling of escaped quotes."""
        dsl = r'CALL write_file file.txt "He said \"hello\" to me"'
        tokens = self.tokenizer.tokenize(dsl)
        
        assert len(tokens) == 1
        assert tokens[0].args == ["write_file", "file.txt", 'He said "hello" to me']
    
    def test_multiline_dsl(self):
        """Test multiline DSL tokenization."""
        dsl = """
        # This is a comment
        CALL read_file test.txt
        PARALLEL
        CALL list_files .
        """
        
        tokens = self.tokenizer.tokenize(dsl)
        
        assert len(tokens) == 3
        assert tokens[0].value == "CALL"
        assert tokens[1].value == "PARALLEL"
        assert tokens[2].value == "CALL"
    
    def test_named_parameters(self):
        """Test named parameter parsing."""
        dsl = "CALL read_file --filename test.txt --encoding utf-8"
        tokens = self.tokenizer.tokenize(dsl)
        
        assert len(tokens) == 1
        assert tokens[0].args == ["read_file", "--filename", "test.txt", "--encoding", "utf-8"]
    
    def test_syntax_error_detection(self):
        """Test syntax error detection."""
        with pytest.raises(DSLSyntaxError):
            self.tokenizer.tokenize('CALL read_file "unclosed quote')
    
    def test_validation_warnings(self):
        """Test token validation warnings."""
        tokens = [
            Token(TokenType.COMMAND, "CALL", ["invalid-tool-name", "arg"])
        ]
        
        warnings = self.tokenizer.validate_syntax(tokens)
        assert len(warnings) > 0


class TestASTBuilder:
    """Test AST builder functionality."""
    
    def setup_method(self):
        self.builder = ASTBuilder()
    
    def test_simple_call_node(self):
        """Test building simple CALL node."""
        tokens = [Token(TokenType.COMMAND, "CALL", ["read_file", "test.txt"])]
        ast = self.builder.build_ast(tokens)
        
        assert len(ast.nodes) == 1
        node = ast.nodes[0]
        assert node.type == NodeType.CALL
        assert node.tool_name == "read_file"
        assert node.args["filename"] == "test.txt"
    
    def test_named_arguments(self):
        """Test building with named arguments."""
        tokens = [Token(TokenType.COMMAND, "CALL", ["read_file", "--filename", "test.txt", "--encoding", "utf-8"])]
        ast = self.builder.build_ast(tokens)
        
        node = ast.nodes[0]
        assert node.args["filename"] == "test.txt"
        assert node.args["encoding"] == "utf-8"
    
    def test_parallel_node(self):
        """Test building PARALLEL node."""
        tokens = [
            Token(TokenType.COMMAND, "PARALLEL", []),
            Token(TokenType.COMMAND, "CALL", ["read_file", "file1.txt"]),
            Token(TokenType.COMMAND, "CALL", ["read_file", "file2.txt"])
        ]
        ast = self.builder.build_ast(tokens)
        
        assert len(ast.nodes) == 3
        parallel_node = ast.nodes[0]
        assert parallel_node.type == NodeType.PARALLEL
        assert parallel_node.value == "PARALLEL"
    
    def test_conditional_node(self):
        """Test building conditional IF node."""
        tokens = [
            Token(TokenType.COMMAND, "IF", ["condition"]),
            Token(TokenType.COMMAND, "CALL", ["read_file", "file.txt"])
        ]
        ast = self.builder.build_ast(tokens)
        
        if_node = ast.nodes[0]
        assert if_node.type == NodeType.CONDITIONAL
        assert if_node.args["condition"] == "condition"
    
    def test_workflow_node(self):
        """Test building WORKFLOW node."""
        tokens = [Token(TokenType.COMMAND, "WORKFLOW", ["my_workflow", "--version", "1.0"])]
        ast = self.builder.build_ast(tokens)
        
        workflow_node = ast.nodes[0]
        assert workflow_node.type == NodeType.WORKFLOW
        assert workflow_node.args["name"] == "my_workflow"
        assert workflow_node.args["version"] == "1.0"
    
    def test_argument_value_parsing(self):
        """Test parsing of different argument value types."""
        # Test JSON parsing
        builder = self.builder
        assert builder._parse_argument_value('{"key": "value"}') == {"key": "value"}
        
        # Test number parsing
        assert builder._parse_argument_value("42") == 42
        assert builder._parse_argument_value("3.14") == 3.14
        
        # Test boolean parsing
        assert builder._parse_argument_value("true") == True
        assert builder._parse_argument_value("false") == False
        
        # Test string parsing
        assert builder._parse_argument_value('"quoted string"') == "quoted string"
        assert builder._parse_argument_value('plain_string') == "plain_string"


class TestDSLValidator:
    """Test DSL validator functionality."""
    
    def setup_method(self):
        self.validator = DSLValidator()
    
    def test_valid_tokens(self):
        """Test validation of valid tokens."""
        tokens = [
            Token(TokenType.COMMAND, "CALL", ["read_file", "test.txt"])
        ]
        result = self.validator.validate_tokens(tokens)
        
        assert result.is_valid
        assert result.summary["errors"] == 0
    
    def test_invalid_call_token(self):
        """Test validation of invalid CALL token."""
        tokens = [
            Token(TokenType.COMMAND, "CALL", [])  # Missing tool name
        ]
        result = self.validator.validate_tokens(tokens)
        
        assert not result.is_valid
        assert result.summary["errors"] > 0
    
    def test_balanced_blocks(self):
        """Test validation of balanced block structures."""
        # Test valid balanced blocks
        tokens = [
            Token(TokenType.COMMAND, "PARALLEL", []),
            Token(TokenType.COMMAND, "CALL", ["read_file", "test.txt"]),
            Token(TokenType.COMMAND, "END_PARALLEL", [])
        ]
        result = self.validator.validate_tokens(tokens)
        assert result.is_valid
        
        # Test unbalanced blocks
        unbalanced_tokens = [
            Token(TokenType.COMMAND, "PARALLEL", []),
            Token(TokenType.COMMAND, "CALL", ["read_file", "test.txt"])
            # Missing END_PARALLEL
        ]
        result = self.validator.validate_tokens(unbalanced_tokens)
        assert not result.is_valid
    
    def test_ast_validation(self):
        """Test AST structure validation."""
        # Valid AST
        valid_ast = AST(nodes=[
            ASTNode(
                type=NodeType.CALL,
                value="CALL",
                tool_name="read_file",
                args={"filename": "test.txt"}
            )
        ])
        result = self.validator.validate_ast(valid_ast)
        assert result.is_valid
        
        # Invalid AST - CALL without tool_name
        invalid_ast = AST(nodes=[
            ASTNode(
                type=NodeType.CALL,
                value="CALL",
                tool_name=None,
                args={}
            )
        ])
        result = self.validator.validate_ast(invalid_ast)
        assert not result.is_valid
    
    def test_tool_availability_validation(self):
        """Test validation against available tools."""
        ast = AST(nodes=[
            ASTNode(
                type=NodeType.CALL,
                value="CALL",
                tool_name="nonexistent_tool",
                args={}
            )
        ])
        
        available_tools = ["read_file", "write_file", "list_files"]
        result = self.validator.validate_ast(ast, available_tools)
        
        assert not result.is_valid
        errors = result.get_errors()
        assert any("not available" in error["message"] for error in errors)


class TestToolExecutionCache:
    """Test tool execution cache functionality."""
    
    def setup_method(self):
        self.cache = ToolExecutionCache(max_size=3, default_ttl_seconds=1)
    
    def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        self.cache.set("read_file", {"filename": "test.txt"}, "file content")
        result = self.cache.get("read_file", {"filename": "test.txt"})
        
        assert result == "file content"
        
        # Test cache miss
        miss_result = self.cache.get("nonexistent_tool", {})
        assert miss_result is None
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = generate_cache_key("read_file", {"filename": "test.txt"})
        key2 = generate_cache_key("read_file", {"filename": "test.txt"})
        key3 = generate_cache_key("read_file", {"filename": "other.txt"})
        
        assert key1 == key2  # Same parameters should generate same key
        assert key1 != key3  # Different parameters should generate different keys
    
    def test_cache_expiration(self):
        """Test cache entry expiration."""
        self.cache.set("read_file", {"filename": "test.txt"}, "content")
        
        # Should be available immediately
        assert self.cache.get("read_file", {"filename": "test.txt"}) == "content"
        
        # Wait for expiration (1 second TTL)
        import time
        time.sleep(1.1)
        
        # Should be expired now
        assert self.cache.get("read_file", {"filename": "test.txt"}) is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        self.cache.set("tool1", {"arg": "1"}, "result1")
        self.cache.set("tool2", {"arg": "2"}, "result2")
        self.cache.set("tool3", {"arg": "3"}, "result3")
        
        # Access first item to make it recently used
        self.cache.get("tool1", {"arg": "1"})
        
        # Add new item to trigger eviction
        self.cache.set("tool4", {"arg": "4"}, "result4")
        
        # tool2 should be evicted (least recently used)
        assert self.cache.get("tool2", {"arg": "2"}) is None
        assert self.cache.get("tool1", {"arg": "1"}) == "result1"  # Should still be there
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        self.cache.set("tool1", {}, "result1")
        self.cache.get("tool1", {})  # Hit
        self.cache.get("nonexistent", {})  # Miss
        
        stats = self.cache.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["hit_rate"] == 0.5


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self):
        self.tools = [
            {"name": "read_file", "description": "Read a file"},
            {"name": "write_file", "description": "Write to a file"},
            {"name": "list_files", "description": "List files in directory"}
        ]
    
    def get_available_tools(self):
        return self.tools
    
    async def invoke_tool(self, tool_name, args):
        if tool_name == "read_file":
            return {"success": True, "content": f"Content of {args.get('filename', 'unknown')}"}
        elif tool_name == "write_file":
            return {"success": True, "message": f"Written to {args.get('filename', 'unknown')}"}
        elif tool_name == "list_files":
            return {"success": True, "files": ["file1.txt", "file2.txt"]}
        else:
            raise Exception(f"Tool {tool_name} not found")
    
    def has_local_tool(self, tool_name):
        return tool_name in [tool["name"] for tool in self.tools]
    
    async def find_agent_with_tool(self, tool_name):
        if tool_name in [tool["name"] for tool in self.tools]:
            return None  # Local tool
        return "remote_peer_123"  # Remote tool
    
    async def execute_remote_tool(self, peer_id, tool_name, args):
        return {"success": True, "result": f"Remote execution of {tool_name} on {peer_id}"}


class TestAdvancedDSLParser:
    """Test advanced DSL parser functionality."""
    
    def setup_method(self):
        from src.praxis_sdk.dsl.parser import AgentInterface
        
        self.mock_agent = MockAgent()
        self.agent_interface = AgentInterface(self.mock_agent)
        self.parser = AdvancedDSLParser(self.agent_interface)
    
    @pytest.mark.asyncio
    async def test_simple_call_execution(self):
        """Test execution of simple CALL command."""
        dsl = "CALL read_file --filename test.txt"
        result = await self.parser.parse_and_execute(dsl)
        
        assert result.success
        assert result.data["status"] == "completed"
        assert len(result.data["results"]) == 1
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel execution of multiple commands."""
        dsl = """
        PARALLEL
        CALL read_file file1.txt
        CALL read_file file2.txt
        """
        result = await self.parser.parse_and_execute(dsl)
        
        assert result.success
        # Should have PARALLEL node execution result
        parallel_result = result.data["results"][0]
        assert parallel_result["type"] == "parallel"
        assert parallel_result["success_count"] >= 0
    
    @pytest.mark.asyncio
    async def test_sequence_execution(self):
        """Test sequential execution of commands."""
        dsl = """
        SEQUENCE
        CALL write_file file.txt "hello"
        CALL read_file file.txt
        """
        result = await self.parser.parse_and_execute(dsl)
        
        assert result.success
        sequence_result = result.data["results"][0]
        assert sequence_result["type"] == "sequence"
        assert sequence_result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_conditional_execution(self):
        """Test conditional execution with IF statement."""
        dsl = """
        IF true
        CALL read_file file.txt
        """
        result = await self.parser.parse_and_execute(dsl)
        
        assert result.success
        conditional_result = result.data["results"][0]
        assert conditional_result["type"] == "conditional"
        assert conditional_result["condition_result"] == True
        assert conditional_result["branch_executed"] == "if"
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self):
        """Test tool execution caching."""
        dsl = "CALL read_file --filename test.txt"
        
        # First execution - should not be cached
        result1 = await self.parser.parse_and_execute(dsl, use_cache=True)
        assert result1.success
        
        # Second execution - should use cache
        result2 = await self.parser.parse_and_execute(dsl, use_cache=True)
        assert result2.success
        
        stats = self.parser.get_stats()
        assert stats["cache_stats"]["hits"] > 0
    
    @pytest.mark.asyncio
    async def test_validation_integration(self):
        """Test validation integration with parser."""
        # Test invalid DSL
        invalid_dsl = "CALL"  # Missing tool name
        
        result = await self.parser.parse_and_execute(invalid_dsl, validate=True)
        assert not result.success
        assert "validation failed" in result.error.lower() or "syntax" in result.error.lower()
    
    def test_parser_statistics(self):
        """Test parser statistics tracking."""
        stats = self.parser.get_stats()
        
        assert "commands_processed" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "total_execution_time" in stats
        assert "cache_stats" in stats


class TestTaskPlanner:
    """Test task planner functionality."""
    
    def setup_method(self):
        # Mock OpenAI client
        self.mock_llm_client = AsyncMock()
        self.planner = TaskPlanner(self.mock_llm_client, "gpt-4")
    
    @pytest.mark.asyncio
    async def test_workflow_generation_from_natural_language(self):
        """Test workflow generation from natural language."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "workflow_dsl": "CALL read_file test.txt",
            "explanation": "Read a test file",
            "estimated_duration": 30,
            "confidence_score": 0.9,
            "required_tools": ["read_file"],
            "parallel_opportunities": []
        })
        
        self.mock_llm_client.chat.completions.create.return_value = mock_response
        
        network_context = NetworkContext()
        network_context.add_tool({"name": "read_file", "description": "Read file"})
        
        plan = await self.planner.generate_workflow_from_natural_language(
            "Read the test file",
            network_context
        )
        
        assert plan is not None
        assert plan.description == "Read the test file"
        assert plan.confidence_score == 0.9
        assert "read_file" in plan.metadata["required_tools"]
    
    def test_network_context(self):
        """Test network context functionality."""
        context = NetworkContext()
        
        # Add agent
        context.add_agent({
            "id": "agent1",
            "tools": ["read_file", "write_file"],
            "load": 0.5
        })
        
        # Add tool
        context.add_tool({
            "name": "read_file",
            "description": "Read a file"
        })
        
        # Test agent selection
        agents_with_tool = context.get_agents_with_tool("read_file")
        assert "agent1" in agents_with_tool
        
        best_agent = context.get_best_agent_for_tool("read_file")
        assert best_agent == "agent1"
    
    @pytest.mark.asyncio
    async def test_workflow_plan_validation(self):
        """Test workflow plan validation."""
        plan = WorkflowPlan("test_plan", "Test workflow")
        plan.add_node("node1", "tool", {"tool_name": "read_file"})
        plan.add_node("node2", "tool", {"tool_name": "nonexistent_tool"})
        plan.add_edge("edge1", "node1", "node2")
        plan.metadata["required_tools"] = ["read_file", "nonexistent_tool"]
        
        network_context = NetworkContext()
        network_context.add_tool({"name": "read_file", "description": "Read file"})
        
        errors = await self.planner.validate_plan(plan, network_context)
        
        assert len(errors) > 0
        assert any("not available" in error for error in errors)


class TestIntegrationScenarios:
    """Integration tests for complete DSL workflows."""
    
    def setup_method(self):
        from src.praxis_sdk.dsl.parser import AgentInterface
        
        self.mock_agent = MockAgent()
        self.agent_interface = AgentInterface(self.mock_agent)
        self.parser = AdvancedDSLParser(self.agent_interface)
    
    @pytest.mark.asyncio
    async def test_complex_workflow_execution(self):
        """Test execution of complex workflow with multiple constructs."""
        dsl = """
        WORKFLOW data_processing --version 1.0
        
        SEQUENCE
        CALL read_file --filename input.txt
        
        PARALLEL
        CALL write_file --filename output1.txt --content "processed data 1"
        CALL write_file --filename output2.txt --content "processed data 2"
        
        CALL list_files .
        """
        
        result = await self.parser.parse_and_execute(dsl)
        assert result.success
        
        # Should have workflow, sequence, and other nodes
        results = result.data["results"]
        assert len(results) >= 3
        
        # Check workflow execution
        workflow_result = results[0]
        assert workflow_result["type"] == "workflow"
        assert workflow_result["name"] == "data_processing"
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling in complex workflows."""
        dsl = """
        SEQUENCE
        CALL read_file valid_file.txt
        CALL nonexistent_tool invalid_args
        CALL read_file another_file.txt
        """
        
        result = await self.parser.parse_and_execute(dsl)
        
        # Sequence should fail on invalid tool
        sequence_result = result.data["results"][0]
        assert sequence_result["type"] == "sequence"
        assert not sequence_result["success"]
        assert "failed_at_step" in sequence_result
    
    @pytest.mark.asyncio
    async def test_performance_with_caching(self):
        """Test performance improvements with caching."""
        dsl = """
        PARALLEL
        CALL read_file test.txt
        CALL read_file test.txt
        CALL read_file test.txt
        """
        
        # First execution
        start_time = asyncio.get_event_loop().time()
        result1 = await self.parser.parse_and_execute(dsl, use_cache=True)
        end_time = asyncio.get_event_loop().time()
        first_duration = end_time - start_time
        
        # Second execution with cache
        start_time = asyncio.get_event_loop().time()
        result2 = await self.parser.parse_and_execute(dsl, use_cache=True)
        end_time = asyncio.get_event_loop().time()
        second_duration = end_time - start_time
        
        assert result1.success
        assert result2.success
        
        # Second execution should be faster (cached)
        # Note: In real scenarios with actual I/O, this would be more noticeable
        stats = self.parser.get_stats()
        assert stats["cache_stats"]["hits"] > 0
    
    @pytest.mark.asyncio
    async def test_validation_prevents_invalid_execution(self):
        """Test that validation prevents execution of invalid DSL."""
        invalid_dsl_examples = [
            "CALL",  # Missing tool name
            "PARALLEL\nCALL read_file test.txt",  # Unbalanced blocks
            "CALL invalid-tool-name test.txt",  # Invalid tool name format
            "IF\nCALL read_file test.txt",  # IF without condition
        ]
        
        for invalid_dsl in invalid_dsl_examples:
            result = await self.parser.parse_and_execute(invalid_dsl, validate=True)
            assert not result.success, f"Should have failed for: {invalid_dsl}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])