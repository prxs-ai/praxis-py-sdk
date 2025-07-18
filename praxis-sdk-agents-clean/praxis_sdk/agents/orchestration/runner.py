import uuid
from typing import Any

import ray
from ray import workflow
from ray.runtime_env import RuntimeEnv

from praxis_sdk.agents import abc
from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.models import Workflow, WorkflowStep
from praxis_sdk.agents.orchestration.config import BasicWorkflowConfig
from praxis_sdk.agents.orchestration.utils import get_workflows_from_files
from praxis_sdk.agents.utils import get_entry_points


@ray.remote
def generate_request_id() -> str:
    # Generate a unique idempotency token.
    return uuid.uuid4().hex


class DAGRunner(abc.AbstractWorkflowRunner):
    def __init__(self, config: BasicWorkflowConfig):
        self.config = config

    def reconfigure(self, config: dict[str, Any]) -> None:
        """Reconfigure the agent with new settings.

        Args:
            config: New configuration settings

        """
        self.config = BasicWorkflowConfig(**config)

    @classmethod
    def start_daemon(cls: "DAGRunner", include_failed=False) -> None:
        """Start the workflow daemon process."""
        pass

    @classmethod
    def stop_daemon(cls: "DAGRunner") -> None:
        """Stop the workflow daemon process."""
        # TODO(team): Stop all workflows  # https://github.com/project/issues/124
        pass

    def run_background_workflows(
        self,
    ) -> None:
        """Run static workflows in the workflow runner engine."""
        workflow_definitions = get_workflows_from_files()

        for _, workflow_dict in workflow_definitions.items():
            workflow_instance = Workflow(**workflow_dict)
            if workflow_instance.id in self.config.WORKFLOWS_TO_RUN and self.config.WORKFLOWS_TO_RUN[workflow_instance.id].enabled:
                self.run(workflow_instance, async_mode=True)

    async def list_workflows(self, status: str | None = None):
        workflow_metadata = {}
        for workflow_id, _ in workflow.list_all(status):
            workflow_metadata[workflow_id] = workflow.get_metadata(workflow_id)
        return workflow_metadata

    def create_step(self, step: WorkflowStep):
        """Create a remote function for a workflow step with proper runtime environment.
        
        This method creates a Ray remote function that can execute a workflow step
        with the required dependencies and environment variables. It handles tool
        loading through entry points and sets up proper error handling.
        
        Args:
            step: The WorkflowStep configuration to create a remote function for
            
        Returns:
            Tuple of (remote_function, step_args) ready for execution
        """
        runtime_env = RuntimeEnv(pip=[step.tool.render_pip_dependency()], env_vars=step.env_vars)

        @ray.workflow.options(checkpoint=True)
        @ray.remote(
            runtime_env=runtime_env,
            max_retries=self.config.WORKFLOW_STEP_MAX_RETRIES,
            retry_exceptions=True,
        )
        def get_tool_entrypoint_wrapper(*args, **kwargs):
            entry_points = get_entry_points(EntrypointGroup.TOOL_ENTRYPOINT)
            try:
                tool = entry_points[step.tool.package_name].load()
            except KeyError as exc:
                raise ValueError(f"Tool {step.tool.package_name} not found in entry points") from exc
            return workflow.continuation(
                tool.options(runtime_env=RuntimeEnv(env_vars=step.env_vars)).bind(*args, **kwargs)
            )

        return get_tool_entrypoint_wrapper, step.args

    async def run(self, dag_spec: Workflow, context: Any = None, async_mode: bool = False) -> Any:
        """Run the DAG using Ray Workflows."""
        steps = {}

        for step in dag_spec.steps:
            steps[step.task_id] = self.create_step(step)

        if not steps:
            raise ValueError("Workflow cannot be empty - at least one step is required")

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


def dag_runner(config: BasicWorkflowConfig) -> DAGRunner:
    return DAGRunner(config)
