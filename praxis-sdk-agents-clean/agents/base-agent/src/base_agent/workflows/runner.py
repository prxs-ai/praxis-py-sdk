import uuid
import os
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
        def get_tool_entrypoint_wrapper(*args, **kwargs):
            return get_tool_entrypoint(self.config.group_name, task.tool.name)(*args, **kwargs)

        return get_tool_entrypoint_wrapper

    def run(self, dag_spec: dict[int, Task]) -> Any:
        """Runs the DAG using Ray Workflows"""
        # Create remote functions for each step
        for step_id, task in dag_spec.items():
            self.steps[task.task_id] = self.create_step(task)

        @ray.remote
        def workflow_executor(request_id: str) -> Any:
            step_results = {}

            # Find the last task to know when to return the final result
            last_task_id = max(dag_spec.keys())
            
            # Execute steps in order, handling dependencies
            for step_id, task in sorted(dag_spec.items()):
                task_id = task.task_id
                deps = task.dependencies

                # Gather inputs from dependencies
                inputs = task.args if isinstance(task.args, list) else [task.args] if task.args is not None else []
                
                if deps:
                    dep_results = {}
                    for dep in deps:
                        if dep in step_results:
                            dep_results[dep] = step_results[dep]
                    
                    # If we have dependency results, use them as inputs
                    if dep_results:
                        inputs = list(dep_results.values())

                # Execute step with dependencies
                step_func = self.steps[task_id]
                result = step_func.bind(*inputs)

                # Store result for dependencies
                step_results[task_id] = result
                
                # If this is the last step, return its result
                if step_id == last_task_id:
                    return workflow.continuation(result)

            # Return the last result as a fallback
            last_result = list(step_results.values())[-1] if step_results else None
            return workflow.continuation(last_result)

        # Start the workflow with options for durability
        return workflow.run(
            workflow_executor.bind(generate_request_id.bind()),
            workflow_id=f"dag-{uuid.uuid4().hex[:8]}",  # Unique ID for each workflow
            metadata={"dag_spec": str(dag_spec.keys())}  # Store metadata for debugging
        )


def dag_runner() -> DAGRunner:
    return DAGRunner(get_agent_config())
