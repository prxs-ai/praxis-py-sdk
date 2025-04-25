import uuid
from typing import Any

import ray
from ray import workflow
from ray.runtime_env import RuntimeEnv

from base_agent import abc
from base_agent.const import EntrypointGroup
from base_agent.models import Task, Workflow
from base_agent.utils import get_entry_points
from base_agent.workflows.config import BasicWorkflowConfig


@ray.remote
def generate_request_id() -> str:
    # Generate a unique idempotency token.
    return uuid.uuid4().hex


class DAGRunner(abc.AbstractWorkflowRunner):
    def __init__(self, config: BasicWorkflowConfig):
        self.config = config

    @classmethod
    def start(cls: "DAGRunner", include_failed = False) -> None:
        workflow.init()
        workflow.resume_all(include_failed)

    @classmethod
    def stop(cls: "DAGRunner") -> None:
        #  TODO: Stop all workflows
        pass

    @classmethod
    def list_workflows(cls: "DAGRunner", status: str | None = None):
        wfs = []
        for wf_id, _ in workflow.list_all(status):
            wfs.append(workflow.get_metadata(wf_id))
        return wfs



    def create_step(self, task: Task):
        """Creates a remote function for a step"""

        @ray.workflow.options(checkpoint=True)
        @ray.remote(
            runtime_env=RuntimeEnv(pip=[f"{task.tool.name}=={task.tool.version}"]),
            max_retries=self.config.WORKFLOW_STEP_MAX_RETRIES,
            retry_exceptions=True,
        )
        def get_tool_entrypoint_wrapper(*args, **kwargs):
            entry_points = get_entry_points(EntrypointGroup.TOOL_ENTRYPOINT)
            try:
                tool = entry_points[task.tool.name].load()
            except KeyError as exc:
                raise ValueError(f"Tool {task.tool.name} not found in entry points") from exc

            return workflow.continuation(tool.bind(*args, **kwargs))

        return get_tool_entrypoint_wrapper, task.args

    def run(self, dag_spec: Workflow, context: Any = None) -> Any:
        """Runs the DAG using Ray Workflows"""
        # Create remote functions for each step
        steps = {}

        for step in dag_spec.steps:
            steps[step.task.task_id] = self.create_step(step.task)
        last_task_id = step.task.task_id

        @ray.remote
        def workflow_executor(request_id: str) -> Any:
            step_results = {}

            # Execute steps in order, handling dependencies
            for task_id, (task, task_args) in sorted(steps.items()):

                # Execute step with dependencies
                result = task.bind(**{a["name"]: a["value"] for a in task_args})

                # Store result for dependencies
                step_results[task_id] = result

                # If this is the last step, return its result
                if task_id == last_task_id:
                    return workflow.continuation(result)

            # Return the last result as a fallback
            last_result = list(step_results.values())[-1] if step_results else None
            return workflow.continuation(last_result)

        # Start the workflow with options for durability
        return workflow.run(
            workflow_executor.bind(generate_request_id.bind()),
            workflow_id=f"dag-{uuid.uuid4().hex[:8]}",  # Unique ID for each workflow
            metadata={"dag_spec": dag_spec.model_dump()},  # Store metadata for debugging
        )


def dag_runner(config: BasicWorkflowConfig) -> DAGRunner:
    return DAGRunner(config)
