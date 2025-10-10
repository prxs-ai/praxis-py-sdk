"""Specialized OpenAI client for workflow planning and natural language processing."""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ..config import LLMConfig
from .prompts import ErrorRecoveryPrompts, WorkflowPrompts, format_prompt


@dataclass
class WorkflowPlan:
    """Represents a generated workflow plan."""

    id: str
    description: str
    dsl: str
    agents_used: list[str]
    estimated_time: int
    confidence: float
    metadata: dict[str, Any]
    created_at: datetime


@dataclass
class AgentSelection:
    """Represents an agent selection result."""

    selected_agent: str
    reason: str
    alternatives: list[str]
    confidence: float


@dataclass
class NetworkContext:
    """Network context for workflow planning."""

    available_agents: list[dict[str, Any]]
    available_tools: list[dict[str, Any]]
    network_load: str
    agent_capabilities: dict[str, list[str]]
    tool_routing: dict[str, list[str]]


class WorkflowPlannerClient:
    """Specialized OpenAI client for intelligent workflow planning.

    This client focuses on:
    - Converting natural language to DSL workflows
    - Agent selection and routing optimization
    - Workflow plan validation and optimization
    - Error recovery and troubleshooting
    """

    def __init__(self, api_key: str, model: str = "gpt-4", temperature: float = 0.1):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.client: AsyncOpenAI | None = None
        self._initialized = False

        # Track planning statistics
        self.stats = {
            "plans_generated": 0,
            "successful_plans": 0,
            "failed_plans": 0,
            "average_confidence": 0.0,
            "total_processing_time": 0.0,
        }

    async def initialize(self):
        """Initialize the OpenAI client."""
        if self._initialized:
            return

        try:
            self.client = AsyncOpenAI(api_key=self.api_key, timeout=30.0, max_retries=3)

            # Test connection
            await self.client.models.list()
            self._initialized = True

            logger.success(
                f"Workflow planner client initialized with model: {self.model}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize workflow planner client: {e}")
            raise

    async def generate_workflow_from_natural_language(
        self, user_request: str, network_context: NetworkContext, max_retries: int = 2
    ) -> WorkflowPlan:
        """Generate a workflow plan from natural language description.

        Args:
            user_request: User's natural language request
            network_context: Current network state and capabilities
            max_retries: Maximum retry attempts for failed generations

        Returns:
            WorkflowPlan object with generated DSL and metadata

        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()
        plan_id = f"plan_{int(start_time.timestamp())}"

        try:
            # Build context for prompt
            context = {
                "user_request": user_request,
                "available_agents": self._format_agents(
                    network_context.available_agents
                ),
                "available_tools": self._format_tools(network_context.available_tools),
                "agent_count": len(network_context.available_agents),
                "tool_count": len(network_context.available_tools),
                "network_load": network_context.network_load,
            }

            # Format prompt
            formatted_prompt = format_prompt(
                WorkflowPrompts.WORKFLOW_GENERATION, context
            )

            # Generate plan
            response = await self._make_completion_request(
                system_prompt=formatted_prompt["system_prompt"],
                user_prompt=formatted_prompt["user_prompt"],
                max_tokens=1500,
            )

            # Parse response
            plan_data = await self._parse_workflow_response(response)

            # Create workflow plan
            processing_time = (datetime.now() - start_time).total_seconds()

            plan = WorkflowPlan(
                id=plan_id,
                description=plan_data.get("description", "Generated workflow"),
                dsl=plan_data.get("dsl", ""),
                agents_used=plan_data.get("agents_used", []),
                estimated_time=plan_data.get("estimated_time", 0),
                confidence=plan_data.get("confidence", 0.8),
                metadata={
                    "user_request": user_request,
                    "processing_time": processing_time,
                    "model": self.model,
                    "network_context": {
                        "agent_count": len(network_context.available_agents),
                        "tool_count": len(network_context.available_tools),
                        "network_load": network_context.network_load,
                    },
                },
                created_at=start_time,
            )

            # Update statistics
            self.stats["plans_generated"] += 1
            self.stats["successful_plans"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["average_confidence"] = (
                self.stats["average_confidence"] * (self.stats["plans_generated"] - 1)
                + plan.confidence
            ) / self.stats["plans_generated"]

            logger.success(
                f"Generated workflow plan {plan_id} in {processing_time:.2f}s"
            )
            return plan

        except Exception as e:
            self.stats["failed_plans"] += 1
            logger.error(f"Failed to generate workflow plan: {e}")

            if max_retries > 0:
                logger.info(
                    f"Retrying workflow generation ({max_retries} attempts left)"
                )
                await asyncio.sleep(1)  # Brief delay before retry
                return await self.generate_workflow_from_natural_language(
                    user_request, network_context, max_retries - 1
                )

            raise

    async def select_optimal_agent(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        available_agents: list[dict[str, Any]],
        task_priority: str = "medium",
    ) -> AgentSelection:
        """Select the optimal agent for executing a specific tool.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Tool arguments
            available_agents: List of available agents with capabilities
            task_priority: Task priority level

        Returns:
            AgentSelection with recommended agent and alternatives

        """
        if not self._initialized:
            await self.initialize()

        try:
            context = {
                "tool_name": tool_name,
                "tool_args": json.dumps(tool_args),
                "task_priority": task_priority,
                "agent_details": self._format_agent_details(available_agents),
            }

            formatted_prompt = format_prompt(WorkflowPrompts.AGENT_SELECTION, context)

            response = await self._make_completion_request(
                system_prompt=formatted_prompt["system_prompt"],
                user_prompt=formatted_prompt["user_prompt"],
                max_tokens=500,
            )

            selection_data = await self._parse_json_response(response)

            return AgentSelection(
                selected_agent=selection_data.get("selected_agent", ""),
                reason=selection_data.get("reason", "No reason provided"),
                alternatives=selection_data.get("alternatives", []),
                confidence=selection_data.get("confidence", 0.5),
            )

        except Exception as e:
            logger.error(f"Failed to select optimal agent: {e}")
            # Fallback to first available agent with the tool
            fallback_agent = self._find_agent_with_tool(tool_name, available_agents)
            return AgentSelection(
                selected_agent=fallback_agent or "default",
                reason="Fallback selection due to LLM failure",
                alternatives=[],
                confidence=0.3,
            )

    async def optimize_workflow_plan(
        self,
        original_dsl: str,
        optimization_goal: str = "performance",
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Optimize an existing workflow plan.

        Args:
            original_dsl: Original DSL workflow
            optimization_goal: Optimization target (performance, reliability, cost)
            constraints: Optimization constraints

        Returns:
            Optimization result with improved DSL and analysis

        """
        if not self._initialized:
            await self.initialize()

        if constraints is None:
            constraints = {
                "max_execution_time": 10,
                "available_resources": "normal",
                "error_tolerance": "medium",
            }

        try:
            context = {
                "original_dsl": original_dsl,
                "optimization_goal": optimization_goal,
                "max_execution_time": constraints.get("max_execution_time", 10),
                "available_resources": constraints.get("available_resources", "normal"),
                "error_tolerance": constraints.get("error_tolerance", "medium"),
                "network_state": "normal",  # Could be dynamic
            }

            formatted_prompt = format_prompt(WorkflowPrompts.PLAN_OPTIMIZATION, context)

            response = await self._make_completion_request(
                system_prompt=formatted_prompt["system_prompt"],
                user_prompt=formatted_prompt["user_prompt"],
                max_tokens=1000,
            )

            return await self._parse_json_response(response)

        except Exception as e:
            logger.error(f"Failed to optimize workflow plan: {e}")
            return {
                "optimized_dsl": original_dsl,
                "changes_made": [],
                "performance_impact": "No optimization applied due to error",
                "risks": [f"Optimization failed: {str(e)}"],
            }

    async def analyze_execution_error(
        self,
        error_message: str,
        failed_workflow: str,
        execution_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze workflow execution errors and suggest recovery strategies.

        Args:
            error_message: The error that occurred
            failed_workflow: The workflow that failed
            execution_context: Context of the failed execution

        Returns:
            Error analysis with recovery suggestions

        """
        if not self._initialized:
            await self.initialize()

        try:
            context = {
                "error_message": error_message,
                "failed_workflow": failed_workflow,
                "execution_context": json.dumps(execution_context),
                "system_state": "normal",  # Could be dynamic
            }

            formatted_prompt = format_prompt(
                ErrorRecoveryPrompts.ERROR_ANALYSIS, context
            )

            response = await self._make_completion_request(
                system_prompt=formatted_prompt["system_prompt"],
                user_prompt=formatted_prompt["user_prompt"],
                max_tokens=800,
            )

            return await self._parse_json_response(response)

        except Exception as e:
            logger.error(f"Failed to analyze execution error: {e}")
            return {
                "root_cause": "analysis_failed",
                "recovery_strategy": "manual_intervention",
                "workflow_modifications": [],
                "retry_feasible": False,
                "alternative_approach": "Contact system administrator",
            }

    async def _make_completion_request(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1000
    ) -> str:
        """Make a chat completion request to OpenAI."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},  # Force JSON response
        )

        return response.choices[0].message.content or ""

    async def _parse_workflow_response(self, response: str) -> dict[str, Any]:
        """Parse workflow generation response."""
        try:
            data = json.loads(response)

            # Validate required fields
            required_fields = ["dsl", "description"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Set defaults for optional fields
            data.setdefault("agents_used", [])
            data.setdefault("estimated_time", 5)
            data.setdefault("confidence", 0.8)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse workflow response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {response}")

    async def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse general JSON response from LLM."""
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {response}")

    def _format_agents(self, agents: list[dict[str, Any]]) -> str:
        """Format agents list for prompt."""
        if not agents:
            return "No agents available"

        formatted = []
        for agent in agents:
            agent_id = agent.get("id", "unknown")
            capabilities = agent.get("capabilities", [])
            load = agent.get("load", "unknown")

            formatted.append(f"- {agent_id}: {', '.join(capabilities)} (load: {load})")

        return "\n".join(formatted)

    def _format_tools(self, tools: list[dict[str, Any]]) -> str:
        """Format tools list for prompt."""
        if not tools:
            return "No tools available"

        formatted = []
        for tool in tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "No description")

            formatted.append(f"- {name}: {description}")

        return "\n".join(formatted)

    def _format_agent_details(self, agents: list[dict[str, Any]]) -> str:
        """Format detailed agent information for agent selection."""
        if not agents:
            return "No agents available"

        formatted = []
        for agent in agents:
            agent_info = [
                f"ID: {agent.get('id', 'unknown')}",
                f"Capabilities: {', '.join(agent.get('capabilities', []))}",
                f"Load: {agent.get('load', 'unknown')}",
                f"Status: {agent.get('status', 'unknown')}",
                f"Location: {agent.get('location', 'unknown')}",
            ]

            formatted.append("\n".join(agent_info))

        return "\n\n".join(formatted)

    def _find_agent_with_tool(
        self, tool_name: str, agents: list[dict[str, Any]]
    ) -> str | None:
        """Find first agent that has the specified tool."""
        for agent in agents:
            capabilities = agent.get("capabilities", [])
            if tool_name in capabilities:
                return agent.get("id")
        return None

    def get_statistics(self) -> dict[str, Any]:
        """Get planning statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_plans"] / max(self.stats["plans_generated"], 1)
            ),
            "initialized": self._initialized,
            "model": self.model,
        }
