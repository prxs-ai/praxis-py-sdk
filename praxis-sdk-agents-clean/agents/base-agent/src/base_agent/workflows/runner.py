import uuid
from typing import Any

import ray
from ray import workflow
from ray.runtime_env import RuntimeEnv

from base_agent.config import BasicAgentConfig, get_agent_config
from base_agent.models import Task
from base_agent.utils import get_entry_points


@ray.remote
def generate_request_id() -> str:
    # Generate a unique idempotency token.
    return uuid.uuid4().hex


def get_tool_entrypoint(group_name: str, tool_name: str):
    entry_points = get_entry_points(group_name)
    try:
        return entry_points[tool_name].load()
    except KeyError as exc:
        raise ValueError(f"Tool {tool_name} not found in entry points") from exc

class DAGRunner:
    def __init__(self, config: BasicAgentConfig):
        self.config = config
        self.steps = {}

    def create_step(self, task: Task):
        """Creates a remote function for a step"""

        @ray.remote(runtime_env=RuntimeEnv(pip=[f"{task.tool.name}=={task.tool.version}"]))
        def get_tool_entrypoint_wrapper():
            return get_tool_entrypoint(self.config.group_name, task.tool.name)

        return get_tool_entrypoint_wrapper()


    def run(self, dag_spec: dict[int, Task]) -> Any:
        """Runs the DAG using Ray Workflows"""
        # Create remote functions for each step
        for _, task in dag_spec.items():
            self.steps[task.task_id] = self.create_step(task)

        @ray.remote
        def workflow_executor(request_id: str) -> Any:
            step_results = {}

            # Execute steps in order, handling dependencies
            for _, task in dag_spec.items():
                name = task.name
                deps = task.dependencies

                # Gather inputs from dependencies
                inputs = task.args
                if deps:
                    inputs = {dep: step_results[dep] for dep in deps if dep in step_results}

                # Execute step with dependencies
                step_func = self.steps[name]
                result = step_func.bind(*inputs)

                # If this isn't the last step, use workflow.continuation
                if task.task_id != dag_spec[-1].task_id:
                    step_results[name] = result
                else:
                    return workflow.continuation(result)

        return workflow.run(workflow_executor.bind(generate_request_id.bind()))


def dag_runner() -> DAGRunner:
    return DAGRunner(get_agent_config())
