import os
from typing import Any

import yaml

from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def determine_workflow_path(workflows_dir="workflows") -> str:
    # always exists
    candidate = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT)
    pkg_path, _ = candidate.value.split(":", 1)

    # the workflows should be in the root of the package
    package_name = pkg_path.split(".")[0]

    # Get the package location on filesystem
    package = __import__(package_name)
    package_dir = str(package.__path__[0])

    return os.path.join(package_dir, workflows_dir)


def get_workflow_files() -> list[str]:
    workflow_dir = determine_workflow_path()
    workflow_files = []

    # Recursively find all yaml/yml files
    for root, _, files in os.walk(workflow_dir):
        for file in files:
            if file.endswith((".yaml", ".yml")):
                workflow_files.append(os.path.join(root, file))

    return workflow_files


def get_workflows_from_files() -> dict[str, dict[str, Any]]:
    wf_dict = {}
    for wf in get_workflow_files():
        try:
            wf_dict[wf] = parse_workflow_file(wf)
        except Exception as e:
            print("Failed to load workflow file %s: %s", wf, e)
            continue
    return wf_dict


def parse_workflow_file(wf_file) -> dict[str, Any]:
    with open(wf_file) as f:
        return yaml.safe_load(f)
