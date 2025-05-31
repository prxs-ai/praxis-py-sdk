import uuid
from typing import Any

import ray
from ray import workflow
from ray.runtime_env import RuntimeEnv

from base_agent import abc
from base_agent.const import EntrypointGroup
from base_agent.models import Workflow, WorkflowStep
from base_agent.orchestration.config import BasicWorkflowConfig
from base_agent.orchestration.utils import get_workflows_from_files
from base_agent.utils import get_entry_points


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
        workflow.init()
        # workflow.resume_all(include_failed)

    @classmethod
    def stop_daemon(cls: "DAGRunner") -> None:
        #  TODO: Stop all workflows
        pass

    def run_background_workflows(
        self,
    ) -> None:
        """Run static workflows in the workflow runner engine."""
        wfs = get_workflows_from_files()

        for _, wf_dict in wfs.items():
            wf = Workflow(**wf_dict)
            if wf.id in self.config.WORKFLOWS_TO_RUN and self.config.WORKFLOWS_TO_RUN[wf.id].enabled:
                self.run(wf, async_mode=True)

    async def list_workflows(self, status: str | None = None):
        wf_dict = {}
        for wf_id, _ in workflow.list_all(status):
            wf_dict[wf_id] = workflow.get_metadata(wf_id)
        return wf_dict

    def create_step(self, step: WorkflowStep):
        """Creates a remote function for a step"""

        @ray.workflow.options(checkpoint=True)
        @ray.remote(
            runtime_env=RuntimeEnv(pip=[step.tool.render_pip_dependency()], env_vars=step.env_vars),
            max_retries=self.config.WORKFLOW_STEP_MAX_RETRIES,
            retry_exceptions=True,
        )
        def get_tool_entrypoint_wrapper(*args, **kwargs):
            entry_points = get_entry_points(EntrypointGroup.TOOL_ENTRYPOINT)
            try:
                tool = entry_points[step.tool.package_name].load()
            except KeyError as exc:
                raise ValueError(f"Tool {step.tool.package_name} not found in entry points") from exc

            return workflow.continuation(tool.bind(*args, **kwargs))

        return get_tool_entrypoint_wrapper, step.args

    def run(self, dag_spec: Workflow, context: Any = None, async_mode=False) -> Any:
        """Runs the DAG using Ray Workflows"""
        # Create remote functions for each step
        steps = {}

        for step in dag_spec.steps:
            steps[step.task_id] = self.create_step(step)
        last_task_id = step.task_id

        @ray.remote
        def workflow_executor(request_id: str) -> Any:
            step_results = {}

            # Execute steps in order, handling dependencies
            for task_id, (task, task_args) in sorted(steps.items()):
                # Execute step with dependencies
                result = task.bind(**task_args)

                # Store result for dependencies
                step_results[task_id] = result

                # If this is the last step, return its result
                if task_id == last_task_id:
                    return workflow.continuation(result)

            # Return the last result as a fallback
            last_result = list(step_results.values())[-1] if step_results else None
            return workflow.continuation(last_result)

        # Start the workflow with options for durability
        func = workflow.run
        if async_mode:
            func = workflow.run_async

        return func(
            workflow_executor.bind(generate_request_id.bind()),
            workflow_id=dag_spec.id,  # Unique ID for each workflow
            metadata={"dag_spec": dag_spec.model_dump()},  # Store metadata for debugging
        )


def dag_runner(config: BasicWorkflowConfig) -> DAGRunner:
    return DAGRunner(config)
