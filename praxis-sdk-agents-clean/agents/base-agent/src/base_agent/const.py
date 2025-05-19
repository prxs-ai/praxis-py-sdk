from enum import Enum


class StrEnumMixIn(str, Enum):
    def __str__(self):
        return self.value


class ExtraQuestions(StrEnumMixIn):
    WHICH_SETTINGS = "Which settings would you like to change?"
    WHAT_INFO = "What information should I add to the knowledge base?"


class Intents(StrEnumMixIn):
    CHANGE_SETTINGS = "change_settings"
    ADD_KNOWLEDGE = "add_knowledge"
    CHIT_CHAT = "chit_chat"


    @property
    def all(self) -> set[str]:
        return {self.CHANGE_SETTINGS, self.ADD_KNOWLEDGE, self.CHIT_CHAT}


class EntrypointGroup(StrEnumMixIn):
    AGENT_ENTRYPOINT = "agent.entrypoint"
    TOOL_ENTRYPOINT = "tool.entrypoint"

    AGENT_PROMPT_CONFIG_ENTRYPOINT = "agent.prompt.config"
    AGENT_PROMPT_ENTRYPOINT = "agent.prompt.entrypoint"

    AGENT_EXECUTOR_CONFIG_ENTRYPOINT = "agent.executor.config"
    AGENT_EXECUTOR_ENTRYPOINT = "agent.executor.entrypoint"

    AGENT_WORKFLOW_CONFIG_ENTRYPOINT = "agent.workflow.config"
    AGENT_WORKFLOW_ENTRYPOINT = "agent.workflow.entrypoint"

    AI_REGISTRY_CONFIG_ENTRYPOINT = "ai.registry.config"
    AI_REGISTRY_ENTRYPOINT = "ai.registry.entrypoint"

    DOMAIN_KNOWLEDGE_CONFIG_ENTRYPOINT = "domain.knowledge.config"
    DOMAIN_KNOWLEDGE_ENTRYPOINT = "domain.knowledge.entrypoint"

    MEMORY_CONFIG_ENTRYPOINT = "memory.entrypoint.config"
    MEMORY_ENTRYPOINT = "memory.entrypoint"

    @property
    def group_name(self):
        return str(self)
