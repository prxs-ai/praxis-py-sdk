"""
Task Planning Engine for converting natural language to DSL workflows.
Integrates with LLM for intelligent workflow generation and agent selection.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from openai import AsyncOpenAI

from .types import AST, ASTNode, NodeType, ExecutionContext, DSLValidationError
from .ast_builder import ASTBuilder
from .tokenizer import DSLTokenizer


class NetworkContext:
    """
    Network context for agent and tool discovery.
    Contains information about available agents and their capabilities.
    """
    
    def __init__(self):
        self.available_agents: List[Dict[str, Any]] = []
        self.available_tools: List[Dict[str, Any]] = []
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.agent_load: Dict[str, float] = {}
        self.peer_latency: Dict[str, float] = {}
        self.last_updated: datetime = datetime.now()
    
    def add_agent(self, agent_info: Dict[str, Any]) -> None:
        """Add agent to network context."""
        agent_id = agent_info.get("id") or agent_info.get("peer_id")
        if agent_id:
            self.available_agents.append(agent_info)
            self.agent_capabilities[agent_id] = agent_info.get("tools", [])
            self.agent_load[agent_id] = agent_info.get("load", 0.0)
            self.last_updated = datetime.now()
    
    def add_tool(self, tool_info: Dict[str, Any]) -> None:
        """Add tool to network context."""
        self.available_tools.append(tool_info)
        self.last_updated = datetime.now()
    
    def get_agents_with_tool(self, tool_name: str) -> List[str]:
        """Get list of agent IDs that have the specified tool."""
        agents = []
        for agent_id, tools in self.agent_capabilities.items():
            if tool_name in tools:
                agents.append(agent_id)
        return agents
    
    def get_best_agent_for_tool(self, tool_name: str) -> Optional[str]:
        """Get the best agent for a specific tool based on load and latency."""
        candidates = self.get_agents_with_tool(tool_name)
        if not candidates:
            return None
        
        # Score agents based on load and latency
        best_agent = None
        best_score = float('inf')
        
        for agent_id in candidates:
            load = self.agent_load.get(agent_id, 1.0)
            latency = self.peer_latency.get(agent_id, 100.0)  # Default 100ms
            
            # Lower score is better
            score = load * 0.7 + (latency / 1000.0) * 0.3
            
            if score < best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "available_agents": self.available_agents,
            "available_tools": self.available_tools,
            "agent_capabilities": self.agent_capabilities,
            "agent_load": self.agent_load,
            "peer_latency": self.peer_latency,
            "last_updated": self.last_updated.isoformat()
        }


class WorkflowPlan:
    """
    Generated workflow plan from natural language.
    Contains structured workflow with nodes and execution metadata.
    """
    
    def __init__(self, plan_id: str, description: str):
        self.id = plan_id
        self.description = description
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.estimated_duration: Optional[int] = None
        self.confidence_score: Optional[float] = None
        self.created_at: datetime = datetime.now()
    
    def add_node(self, node_id: str, node_type: str, data: Dict[str, Any]) -> None:
        """Add workflow node."""
        self.nodes.append({
            "id": node_id,
            "type": node_type,
            "data": data
        })
    
    def add_edge(self, edge_id: str, source: str, target: str, edge_type: str = "default") -> None:
        """Add workflow edge."""
        self.edges.append({
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "nodes": self.nodes,
            "edges": self.edges,
            "metadata": self.metadata,
            "estimated_duration": self.estimated_duration,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat()
        }


class TaskPlanner:
    """
    Advanced task planner that converts natural language to executable workflows.
    Uses LLM for intelligent task breakdown and agent selection.
    """
    
    def __init__(self, llm_client: AsyncOpenAI, model: str = "gpt-4"):
        self.llm_client = llm_client
        self.model = model
        self.tokenizer = DSLTokenizer()
        self.ast_builder = ASTBuilder()
        self.logger = logger
        
        # Planning prompts
        self.system_prompt = """
You are an expert workflow planner that converts natural language requests into structured DSL workflows.

Your task is to analyze user requests and generate executable workflows using available tools and agents.

DSL Commands Available:
- CALL tool_name --arg1 value1 --arg2 value2: Execute a tool with arguments
- PARALLEL: Execute multiple commands in parallel
- SEQUENCE: Execute commands in sequence
- WORKFLOW name: Create a named workflow
- TASK name: Create a named task
- AGENT agent_id: Select specific agent
- IF condition: Conditional execution

Available Tool Types:
- File operations: read_file, write_file, list_files, delete_file
- Directory operations: create_directory, list_directory
- Search operations: search_files, find_in_files
- Network operations: http_request, download_file
- Data processing: parse_json, parse_csv, format_data
- Analysis operations: analyze_text, summarize_content

Response Format:
Respond with a JSON object containing:
{
  "workflow_dsl": "DSL commands as multiline string",
  "explanation": "Brief explanation of the workflow",
  "estimated_duration": 60,
  "confidence_score": 0.85,
  "required_tools": ["tool1", "tool2"],
  "parallel_opportunities": ["step1", "step2"]
}

Focus on:
1. Breaking down complex requests into simple tool calls
2. Identifying parallel execution opportunities
3. Using appropriate agents for specialized tasks
4. Error handling and validation
5. Efficient workflow structure
"""
    
    async def generate_workflow_from_natural_language(
        self, 
        user_request: str,
        network_context: NetworkContext,
        execution_context: Optional[ExecutionContext] = None
    ) -> WorkflowPlan:
        """
        Generate workflow plan from natural language request.
        
        Args:
            user_request: Natural language description of desired workflow
            network_context: Available agents and tools
            execution_context: Additional context for planning
            
        Returns:
            Generated workflow plan
            
        Raises:
            Exception: If workflow generation fails
        """
        self.logger.info(f"Generating workflow from request: {user_request[:100]}...")
        
        try:
            # Build context for LLM
            context_info = self._build_context_prompt(network_context, execution_context)
            
            # Generate workflow using LLM
            llm_response = await self._call_llm_for_planning(user_request, context_info)
            
            # Parse LLM response
            workflow_data = self._parse_llm_response(llm_response)
            
            # Create workflow plan
            plan_id = f"plan_{int(datetime.now().timestamp())}"
            plan = WorkflowPlan(plan_id, user_request)
            
            # Convert DSL to AST and then to workflow nodes
            dsl_content = workflow_data.get("workflow_dsl", "")
            if dsl_content:
                ast = await self._dsl_to_ast(dsl_content)
                self._ast_to_workflow_plan(ast, plan, network_context)
            
            # Set metadata
            plan.estimated_duration = workflow_data.get("estimated_duration")
            plan.confidence_score = workflow_data.get("confidence_score")
            plan.metadata = {
                "required_tools": workflow_data.get("required_tools", []),
                "parallel_opportunities": workflow_data.get("parallel_opportunities", []),
                "explanation": workflow_data.get("explanation", ""),
                "original_request": user_request
            }
            
            self.logger.info(f"Generated workflow plan: {plan.id} with {len(plan.nodes)} nodes")
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to generate workflow from natural language: {e}")
            raise
    
    def _build_context_prompt(
        self, 
        network_context: NetworkContext,
        execution_context: Optional[ExecutionContext]
    ) -> str:
        """Build context prompt for LLM."""
        context_parts = []
        
        # Available tools
        if network_context.available_tools:
            tools_info = []
            for tool in network_context.available_tools:
                tool_name = tool.get("name", "unknown")
                tool_desc = tool.get("description", "No description")
                tools_info.append(f"- {tool_name}: {tool_desc}")
            
            context_parts.append("Available Tools:\n" + "\n".join(tools_info))
        
        # Available agents
        if network_context.available_agents:
            agents_info = []
            for agent in network_context.available_agents:
                agent_id = agent.get("id", "unknown")
                agent_tools = agent.get("tools", [])
                load = network_context.agent_load.get(agent_id, 0.0)
                agents_info.append(f"- Agent {agent_id}: tools={agent_tools}, load={load:.2f}")
            
            context_parts.append("Available Agents:\n" + "\n".join(agents_info))
        
        # Execution context
        if execution_context:
            if execution_context.variables:
                context_parts.append(f"Variables: {execution_context.variables}")
            if execution_context.agent_capabilities:
                context_parts.append(f"Agent Capabilities: {execution_context.agent_capabilities}")
        
        return "\n\n".join(context_parts)
    
    async def _call_llm_for_planning(self, user_request: str, context_info: str) -> Dict[str, Any]:
        """Call LLM to generate workflow plan."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Request: {user_request}\n\nContext:\n{context_info}"}
        ]
        
        response = await self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    
    def _parse_llm_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate LLM response."""
        required_fields = ["workflow_dsl", "explanation"]
        
        for field in required_fields:
            if field not in response:
                raise ValueError(f"LLM response missing required field: {field}")
        
        # Validate confidence score
        confidence = response.get("confidence_score")
        if confidence is not None and (confidence < 0.0 or confidence > 1.0):
            self.logger.warning(f"Invalid confidence score: {confidence}")
            response["confidence_score"] = None
        
        return response
    
    async def _dsl_to_ast(self, dsl_content: str) -> AST:
        """Convert DSL string to AST."""
        tokens = self.tokenizer.tokenize(dsl_content)
        ast = self.ast_builder.build_ast(tokens)
        return ast
    
    def _ast_to_workflow_plan(self, ast: AST, plan: WorkflowPlan, network_context: NetworkContext) -> None:
        """Convert AST to workflow plan nodes and edges."""
        node_counter = 0
        edge_counter = 0
        
        for ast_node in ast.nodes:
            nodes, edges = self._convert_ast_node(
                ast_node, 
                network_context, 
                node_counter, 
                edge_counter
            )
            
            plan.nodes.extend(nodes)
            plan.edges.extend(edges)
            
            node_counter += len(nodes)
            edge_counter += len(edges)
    
    def _convert_ast_node(
        self, 
        ast_node: ASTNode, 
        network_context: NetworkContext,
        node_start_id: int,
        edge_start_id: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Convert AST node to workflow nodes and edges."""
        nodes = []
        edges = []
        
        if ast_node.type == NodeType.CALL:
            # Tool execution node
            tool_name = ast_node.tool_name
            best_agent = network_context.get_best_agent_for_tool(tool_name)
            
            nodes.append({
                "id": f"node_{node_start_id}",
                "type": "tool",
                "data": {
                    "tool_name": tool_name,
                    "arguments": ast_node.args,
                    "agent_id": best_agent,
                    "position": {"x": 100, "y": 100 * node_start_id}
                }
            })
            
        elif ast_node.type == NodeType.PARALLEL:
            # Parallel execution node
            nodes.append({
                "id": f"node_{node_start_id}",
                "type": "parallel",
                "data": {
                    "execution_mode": "parallel",
                    "children_count": len(ast_node.children),
                    "position": {"x": 100, "y": 100 * node_start_id}
                }
            })
            
            # Add child nodes
            child_node_id = node_start_id + 1
            for child in ast_node.children:
                child_nodes, child_edges = self._convert_ast_node(
                    child, network_context, child_node_id, edge_start_id
                )
                nodes.extend(child_nodes)
                edges.extend(child_edges)
                
                # Connect parallel node to child
                edges.append({
                    "id": f"edge_{edge_start_id}",
                    "source": f"node_{node_start_id}",
                    "target": f"node_{child_node_id}",
                    "type": "parallel"
                })
                
                child_node_id += len(child_nodes)
                edge_start_id += 1
        
        elif ast_node.type == NodeType.SEQUENCE:
            # Sequence execution node
            nodes.append({
                "id": f"node_{node_start_id}",
                "type": "sequence",
                "data": {
                    "execution_mode": "sequence",
                    "children_count": len(ast_node.children),
                    "position": {"x": 100, "y": 100 * node_start_id}
                }
            })
            
            # Add child nodes with sequential connections
            prev_node_id = f"node_{node_start_id}"
            child_node_id = node_start_id + 1
            
            for child in ast_node.children:
                child_nodes, child_edges = self._convert_ast_node(
                    child, network_context, child_node_id, edge_start_id
                )
                nodes.extend(child_nodes)
                edges.extend(child_edges)
                
                # Connect previous node to current child
                edges.append({
                    "id": f"edge_{edge_start_id}",
                    "source": prev_node_id,
                    "target": f"node_{child_node_id}",
                    "type": "sequence"
                })
                
                prev_node_id = f"node_{child_node_id}"
                child_node_id += len(child_nodes)
                edge_start_id += 1
        
        elif ast_node.type == NodeType.AGENT:
            # Agent selection node
            agent_id = ast_node.args.get("agent_id")
            nodes.append({
                "id": f"node_{node_start_id}",
                "type": "agent",
                "data": {
                    "agent_id": agent_id,
                    "agent_capabilities": network_context.agent_capabilities.get(agent_id, []),
                    "position": {"x": 100, "y": 100 * node_start_id}
                }
            })
        
        return nodes, edges
    
    async def validate_plan(self, plan: WorkflowPlan, network_context: NetworkContext) -> List[str]:
        """
        Validate workflow plan for executability.
        
        Args:
            plan: Workflow plan to validate
            network_context: Current network context
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check if all required tools are available
        required_tools = plan.metadata.get("required_tools", [])
        available_tool_names = {tool.get("name") for tool in network_context.available_tools}
        
        for tool in required_tools:
            if tool not in available_tool_names:
                errors.append(f"Required tool not available: {tool}")
        
        # Check if nodes have valid connections
        node_ids = {node["id"] for node in plan.nodes}
        for edge in plan.edges:
            if edge["source"] not in node_ids:
                errors.append(f"Edge source not found: {edge['source']}")
            if edge["target"] not in node_ids:
                errors.append(f"Edge target not found: {edge['target']}")
        
        # Check for circular dependencies
        if self._has_circular_dependencies(plan):
            errors.append("Workflow contains circular dependencies")
        
        return errors
    
    def _has_circular_dependencies(self, plan: WorkflowPlan) -> bool:
        """Check if workflow has circular dependencies using DFS."""
        # Build adjacency list
        graph = {}
        for node in plan.nodes:
            graph[node["id"]] = []
        
        for edge in plan.edges:
            source, target = edge["source"], edge["target"]
            if source in graph:
                graph[source].append(target)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    return True
        
        return False