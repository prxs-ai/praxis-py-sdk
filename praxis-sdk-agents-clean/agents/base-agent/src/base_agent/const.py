from enum import Enum


class EntrypointGroup(str, Enum):
    AGENT_ENTRYPOINT = "agent.entrypoint"

    AGENT_PROMPT_CONFIG_ENTRYPOINT = "agent.prompt.config"
    AGENT_PROMPT_ENTRYPOINT = "agent.prompt.entrypoint"

    AGENT_EXECUTOR_CONFIG_ENTRYPOINT = "agent.executor.config"
    AGENT_EXECUTOR_ENTRYPOINT = "agent.executor.entrypoint"

    AGENT_WORKFLOW_CONFIG_ENTRYPOINT = "agent.workflow.config"
    AGENT_WORKFLOW_ENTRYPOINT = "agent.workflow.entrypoint"

    def __str__(self):
        return self.value

    @property
    def group_name(self):
        return str(self)
