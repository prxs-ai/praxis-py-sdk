from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import pydantic

from base_agent.models import AgentModel, ToolModel, Workflow


class AbstractAgentCard(pydantic.BaseModel):
    """Abstract interface for agent cards."""

    ...


class AbstractAgentSkill(pydantic.BaseModel):
    """Abstract interface for agent skills."""

    ...


class AbstractAgentParamsModel(pydantic.BaseModel):
    """Abstract interface for agent params model."""

    ...


class AbstractAgentInputModel(pydantic.BaseModel):
    """Abstract interface for agent intput model"""

    ...


class AbstractAgentOutputModel(pydantic.BaseModel):
    """Abstract interface for agennt output model"""

    ...


class BaseAgentInputModel(AbstractAgentInputModel): ...


class BaseAgentOutputModel(AbstractAgentOutputModel): ...


class AbstractExecutor(ABC):
    """Abstract interface for agent execution engines."""

    @abstractmethod
    def generate_plan(self, prompt: Any, **kwargs) -> Workflow:
        """Generate a plan based on a prompt and additional parameters.

        Args:
            prompt: The prompt to use for planning
            **kwargs: Additional parameters to use in planning

        Returns:
            A dictionary mapping step IDs to Task objects representing the plan
        """
        pass


class AbstractPromptBuilder(ABC):
    """Abstract interface for prompt building components."""

    @abstractmethod
    def generate_plan_prompt(self, *args, **kwargs) -> Any:
        """Generate a prompt for plan generation.

        Args:
            *args: Positional arguments for prompt generation
            **kwargs: Keyword arguments for prompt generation

        Returns:
            A prompt object that can be used by an executor
        """
        pass


class AbstractWorkflowRunner(ABC):
    """Abstract interface for workflow execution engines."""

    @abstractmethod
    def run(
        self,
        plan: Workflow,
        context: AbstractAgentInputModel | None = None,
    ) -> AbstractAgentOutputModel:
        """Execute a workflow plan.

        Args:
            plan: A dictionary mapping step IDs to Task objects

        Returns:
            The result of executing the plan
        """
        pass

    @classmethod
    @abstractmethod
    def start_daemon(cls) -> None:
        """Start the workflow runner engine."""
        pass

    @classmethod
    @abstractmethod
    def stop_daemon(cls) -> None:
        """Stop the workflow runner engine."""
        pass

    @abstractmethod
    def run_background_workflows(self, *args, **kwargs) -> None:
        """Run static workflows in the workflow runner engine."""
        pass

    @abstractmethod
    async def list_workflows(self, *args, **kwargs) -> None:
        """List all workflows in the workflow runner engine."""
        pass

    @abstractmethod
    def reconfigure(self, config: dict[str, Any]) -> None:
        """Reconfigure the agent with new settings.

        Args:
            config: New configuration settings
        """
        pass


class AbstractAgent(ABC):
    """Abstract base class for agent implementations."""

    @abstractmethod
    async def handle(
        self,
        goal: str,
        plan: Workflow | None = None,
        context: AbstractAgentInputModel | None = None,
    ) -> AbstractAgentOutputModel:
        """Handle an incoming request.

        Args:
            goal: The goal to achieve
            plan: An optional existing plan to use or modify
            context: An optional input schema for the agent

        Returns:
            The result of achieving the goal
        """
        pass

    @abstractmethod
    def get_most_relevant_agents(self, goal: str) -> list[AgentModel]:
        """Find the most relevant agents for a goal.

        Args:
            goal: The goal to achieve

        Returns:
            A list of the most relevant agents for the goal
        """
        pass

    @abstractmethod
    def get_most_relevant_tools(self, goal: str) -> list[ToolModel]:
        """Find the most relevant tools for a goal.

        Args:
            goal: The goal to achieve

        Returns:
            A list of the most relevant tools for the goal
        """
        pass

    @abstractmethod
    def generate_plan(
        self, goal: str, agents: Sequence[AgentModel], tools: Sequence[ToolModel], plan: dict | None = None
    ) -> Workflow:
        """Generate a plan for achieving a goal.

        Args:
            goal: The goal to achieve
            agents: Available agents to use in the plan
            tools: Available tools to use in the plan
            plan: An optional existing plan to use or modify

        Returns:
            A dictionary mapping step IDs to Task objects representing the plan
        """
        pass

    @abstractmethod
    def run_workflow(self, plan: Workflow) -> Any:
        """Execute a workflow plan.

        Args:
            plan: A dictionary mapping step IDs to Task objects

        Returns:
            The result of executing the plan
        """
        pass

    @abstractmethod
    def reconfigure(self, config: dict[str, Any]) -> None:
        """Reconfigure the agent with new settings.

        Args:
            config: New configuration settings
        """
        pass

    @abstractmethod
    async def handoff(self, endpoint: str, goal: str, plan: dict) -> Any:
        """Hand off execution to another agent.

        Args:
            endpoint: The endpoint of the agent to hand off to
            goal: The goal to achieve
            plan: The plan to execute

        Returns:
            The result from the agent that was handed off to
        """
        pass
