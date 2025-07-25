import uuid
from typing import Any, Final, Optional

import ray
from ray import workflow
from ray.runtime_env import RuntimeEnv
from loguru import logger

from praxis_sdk.agents import abc
from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.exceptions import WorkflowExecutionError, ConfigurationError
from praxis_sdk.agents.models import Workflow, WorkflowStep
from praxis_sdk.agents.orchestration.config import BasicWorkflowConfig
from praxis_sdk.agents.orchestration.utils import get_workflows_from_files
from praxis_sdk.agents.utils import get_entry_points


@ray.remote
def generate_request_id() -> str:
    """Generate a unique idempotency token for workflow execution."""
    return uuid.uuid4().hex


class DAGRunner(abc.AbstractWorkflowRunner):
    """Enhanced DAG runner with improved error handling and resource management."""
    
    def __init__(self, config: BasicWorkflowConfig) -> None:
        """Initialize DAG runner with configuration validation.
        
        Args:
            config: Workflow configuration
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not isinstance(config, BasicWorkflowConfig):
            raise ConfigurationError("Invalid workflow configuration provided")
            
        self.config = config
        self._daemon_started = False

    def reconfigure(self, config: dict[str, Any]) -> None:
        """Reconfigure the agent with new settings.

        Args:
            config: New configuration settings
            
        Raises:
            ConfigurationError: If configuration update fails
        """
        try:
            self.config = BasicWorkflowConfig(**config)
            logger.info("DAG runner reconfigured successfully")
        except Exception as e:
            raise ConfigurationError(f"Failed to reconfigure DAG runner: {e}") from e

    @classmethod
    def start_daemon(cls, include_failed: bool = False) -> None:
        """Start the workflow daemon process.
        
        Args:
            include_failed: Whether to include failed workflows in daemon
        """
        try:
            logger.info("Starting workflow daemon...")
            # In Ray workflows, the daemon is managed by Ray itself
            # This is a placeholder for any daemon-specific initialization
            logger.info("Workflow daemon started successfully")
        except Exception as e:
            logger.error(f"Failed to start workflow daemon: {e}")
            raise WorkflowExecutionError(f"Daemon startup failed: {e}") from e

    @classmethod
    def stop_daemon(cls) -> None:
        """Stop the workflow daemon process with proper cleanup."""
        try:
            logger.info("Stopping workflow daemon...")
            
            # Cancel all running workflows
            try:
                active_workflows = workflow.list_all(status="RUNNING")
                cancelled_count = 0
                
                for workflow_id, _ in active_workflows:
                    try:
                        workflow.cancel(workflow_id)
                        cancelled_count += 1
                        logger.debug(f"Cancelled workflow: {workflow_id}")
                    except Exception as e:
                        logger.warning(f"Failed to cancel workflow {workflow_id}: {e}")
                        
                if cancelled_count > 0:
                    logger.info(f"Cancelled {cancelled_count} running workflows")
                else:
                    logger.info("No running workflows to cancel")
                    
            except Exception as e:
                logger.error(f"Failed to list/cancel active workflows: {e}")
                
            logger.info("Workflow daemon stopped")
            
        except Exception as e:
            logger.error(f"Error during daemon shutdown: {e}")
            raise WorkflowExecutionError(f"Daemon shutdown failed: {e}") from e

    def run_background_workflows(self) -> None:
        """Run static workflows in the workflow runner engine with error handling."""
        try:
            logger.info("Starting background workflows...")
            workflow_definitions = get_workflows_from_files()
            
            if not workflow_definitions:
                logger.info("No workflow definitions found")
                return
                
            executed_count = 0
            
            for workflow_name, workflow_dict in workflow_definitions.items():
                try:
                    workflow_instance = Workflow(**workflow_dict)
                    
                    # Check if workflow should be executed
                    if (workflow_instance.id in self.config.WORKFLOWS_TO_RUN and 
                        self.config.WORKFLOWS_TO_RUN[workflow_instance.id].enabled):
                        
                        logger.info(f"Executing background workflow: {workflow_name}")
                        self.run(workflow_instance, async_mode=True)
                        executed_count += 1
                        
                    else:
                        logger.debug(f"Skipping disabled workflow: {workflow_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to execute background workflow '{workflow_name}': {e}")
                    # Continue with other workflows
                    
            logger.info(f"Started {executed_count} background workflows")
            
        except Exception as e:
            logger.error(f"Failed to run background workflows: {e}")
            raise WorkflowExecutionError(f"Background workflow execution failed: {e}") from e

    async def list_workflows(self, status: Optional[str] = None) -> dict[str, Any]:
        """List workflows with enhanced error handling and metadata retrieval.
        
        Args:
            status: Optional status filter for workflows
            
        Returns:
            Dictionary of workflow metadata keyed by workflow ID
            
        Raises:
            WorkflowExecutionError: If workflow listing fails
        """
        try:
            logger.debug(f"Listing workflows with status filter: {status}")
            workflow_metadata = {}
            
            # Get workflows based on status filter
            if status:
                workflows = workflow.list_all(status=status)
            else:
                workflows = workflow.list_all()
                
            for workflow_id, workflow_info in workflows:
                try:
                    metadata = workflow.get_metadata(workflow_id)
                    workflow_metadata[workflow_id] = metadata
                except Exception as e:
                    logger.warning(f"Failed to get metadata for workflow {workflow_id}: {e}")
                    # Include basic info even if metadata retrieval fails
                    workflow_metadata[workflow_id] = {
                        "error": f"Metadata unavailable: {e}",
                        "workflow_info": workflow_info
                    }
                    
            logger.info(f"Retrieved metadata for {len(workflow_metadata)} workflows")
            return workflow_metadata
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            raise WorkflowExecutionError(f"Workflow listing failed: {e}") from e

    def create_step(self, step: WorkflowStep) -> tuple[Any, dict[str, Any]]:
        """Create a remote function for a workflow step with proper runtime environment.
        
        This method creates a Ray remote function that can execute a workflow step
        with the required dependencies and environment variables. It handles tool
        loading through entry points and sets up proper error handling.
        
        Args:
            step: The WorkflowStep configuration to create a remote function for
            
        Returns:
            Tuple of (remote_function, step_args) ready for execution
            
        Raises:
            WorkflowExecutionError: If step creation fails
        """
        if not isinstance(step, WorkflowStep):
            raise WorkflowExecutionError("Invalid workflow step provided")
            
        try:
            # Create runtime environment with dependencies and environment variables
            pip_dependencies = []
            if step.tool and hasattr(step.tool, 'render_pip_dependency'):
                pip_dependencies.append(step.tool.render_pip_dependency())
                
            runtime_env = RuntimeEnv(
                pip=pip_dependencies, 
                env_vars=step.env_vars or {}
            )

            @ray.workflow.options(checkpoint=True)
            @ray.remote(
                runtime_env=runtime_env,
                max_retries=self.config.WORKFLOW_STEP_MAX_RETRIES,
                retry_exceptions=True,
            )
            def get_tool_entrypoint_wrapper(*args, **kwargs):
                """Wrapper function to load and execute tool with proper error handling."""
                try:
                    # Get entry points for tools
                    entry_points_list = get_entry_points(EntrypointGroup.TOOL_ENTRYPOINT.group_name)
                    entry_points_dict = {ep.name: ep for ep in entry_points_list}
                    
                    # Load the specific tool
                    tool_name = step.tool.package_name
                    if tool_name not in entry_points_dict:
                        raise EntryPointError(f"Tool '{tool_name}' not found in entry points")
                        
                    tool = entry_points_dict[tool_name].load()
                    
                    # Execute tool with runtime environment
                    return workflow.continuation(
                        tool.options(runtime_env=RuntimeEnv(env_vars=step.env_vars or {})).bind(*args, **kwargs)
                    )
                    
                except Exception as e:
                    logger.error(f"Tool execution failed for step {step.name}: {e}")
                    raise WorkflowExecutionError(f"Tool execution failed: {e}") from e

            return get_tool_entrypoint_wrapper, step.args
            
        except Exception as e:
            raise WorkflowExecutionError(f"Failed to create workflow step '{step.name}': {e}") from e

    async def run(self, dag_spec: Workflow, context: Any = None, async_mode: bool = False) -> Any:
        """Run the DAG using Ray Workflows."""
        steps = {}

        for step in dag_spec.steps:
            steps[step.task_id] = self.create_step(step)

        if not steps:
            from praxis_sdk.agents.exceptions import WorkflowExecutionError
            raise WorkflowExecutionError("Workflow cannot be empty - at least one step is required")

        last_task_id = list(steps.keys())[-1]

        @ray.remote
        def workflow_executor(request_id: str) -> Any:
            step_results = {}

            for task_id, (task, task_args) in sorted(steps.items()):
                result = task.bind(**task_args)
                step_results[task_id] = result

                if task_id == last_task_id:
                    return workflow.continuation(result)

            last_result = list(step_results.values())[-1] if step_results else None
            return workflow.continuation(last_result)

        func = workflow.run
        if async_mode:
            func = workflow.run_async

        return func(
            workflow_executor.bind(generate_request_id.bind()),
            workflow_id=dag_spec.id,
            metadata={"dag_spec": dag_spec.model_dump()},
        )


# Constants
DEFAULT_WORKFLOW_ID_PREFIX: Final[str] = "dag-"

def dag_runner(config: BasicWorkflowConfig) -> DAGRunner:
    """Factory function to create a DAGRunner instance."""
    return DAGRunner(config)
