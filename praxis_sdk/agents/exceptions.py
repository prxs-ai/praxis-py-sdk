"""Custom exceptions for the Praxis SDK agents module."""


class AgentException(Exception):
    """Base exception for agent-related errors."""
    pass


class WorkflowExecutionError(AgentException):
    """Raised when workflow execution fails."""
    pass


class P2PConnectionError(AgentException):
    """Raised when P2P connection fails."""
    pass


class ConfigurationError(AgentException):
    """Raised when agent configuration is invalid."""
    pass


class PromptBuildingError(AgentException):
    """Raised when prompt building fails."""
    pass


class EntryPointError(AgentException):
    """Raised when entry point loading fails."""
    pass


class ToolExecutionError(AgentException):
    """Raised when tool execution fails."""
    pass


class MemoryClientError(AgentException):
    """Raised when memory client operations fail."""
    pass


class DomainKnowledgeError(AgentException):
    """Raised when domain knowledge operations fail."""
    pass


class AIRegistryError(AgentException):
    """Raised when AI registry operations fail."""
    pass