import uuid
from typing import Any

import ray
from ray import workflow


@ray.remote
def generate_request_id() -> str:
    # Generate a unique idempotency token.
    return uuid.uuid4().hex


class DAGRunner:
    def __init__(self, dag_spec: dict[str, Any]):
        self.dag_spec = dag_spec
        self.steps = {}

    def create_step(self, step_config: dict[str, Any]):
        """Creates a remote function for a step"""

        @ray.remote
        def step_function(*args, **kwargs):
            # Here you can add actual execution logic based on
            # step_config['project'] or step_config['tool']
            return kwargs.get("input", "default_output")

        return step_function

    def run(self) -> Any:
        """Runs the DAG using Ray Workflows"""
        # Create remote functions for each step
        for step in self.dag_spec["steps"]:
            self.steps[step["name"]] = self.create_step(step)

        @ray.remote
        def workflow_executor(request_id: str) -> Any:
            step_results = {}

            # Execute steps in order, handling dependencies
            for step in self.dag_spec["steps"]:
                name = step["name"]
                deps = step.get("dependencies", [])

                # Gather inputs from dependencies
                inputs = {}
                if deps:
                    inputs = {dep: step_results[dep] for dep in deps if dep in step_results}

                # Execute step with dependencies
                step_func = self.steps[name]
                result = step_func.bind(**inputs)

                # If this isn't the last step, use workflow.continuation
                if name != self.dag_spec["steps"][-1]["name"]:
                    step_results[name] = result
                else:
                    return workflow.continuation(result)

        return workflow.run(workflow_executor.bind(generate_request_id.bind()))
