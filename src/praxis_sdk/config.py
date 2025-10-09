"""Comprehensive configuration system for Praxis Python SDK."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from loguru import logger
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from praxis_sdk.keyring_manager import get_keyring_manager


class SecurityConfig(BaseModel):
    """Security configuration for P2P and API."""

    use_noise: bool = True
    noise_key: str | None = None
    tls_cert_path: str | None = None
    tls_key_path: str | None = None
    api_key: str | None = None

    def model_post_init(self, __context):
        """Post-initialization hook to load sensitive values from keyring."""
        keyring_mgr = get_keyring_manager()

        if self.noise_key is None:
            self.noise_key = keyring_mgr.get_credential(
                "NOISE_KEY", fallback_env="NOISE_KEY"
            )

        if self.api_key is None:
            self.api_key = keyring_mgr.get_credential("API_KEY", fallback_env="API_KEY")

        super().model_post_init(__context) if hasattr(
            super(), "model_post_init"
        ) else None


class P2PConfig(BaseModel):
    """P2P networking configuration."""

    enabled: bool = True
    port: int = 9000
    host: str = "0.0.0.0"
    keystore_path: str = "./keys"
    peer_discovery: bool = True
    mdns_service: str = "praxis-p2p-mcp"
    connection_timeout: int = 30
    max_peers: int = 50
    protocols: list[str] = Field(
        default_factory=lambda: [
            "/praxis/mcp/1.0.0",
            "/praxis/card/1.0.0",
            "/praxis/tool/1.0.0",
            "/praxis/a2a/1.0.0",
        ]
    )
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    bootstrap_nodes: list[str] = Field(default_factory=list)

    # Additional worker config compatibility
    rendezvous: str | None = None
    enable_mdns: bool | None = None
    enable_dht: bool | None = None
    enable_relay: bool | None = None
    discovery_interval: int = 30
    secure: bool | None = None
    listen_addresses: list[str] = Field(default_factory=list)
    announce_addresses: list[str] = Field(default_factory=list)
    discovery: dict[str, Any] | None = None
    protocol_version: str = "0.3.0"
    capabilities: list[str] = Field(default_factory=list)

    @field_validator("enable_mdns", mode="before")
    @classmethod
    def sync_mdns_config(cls, v, info: ValidationInfo):
        """Sync enable_mdns with peer_discovery for compatibility."""
        if v is None and "peer_discovery" in info.data:
            return info.data["peer_discovery"]
        return v if v is not None else True


class MCPServerConfig(BaseModel):
    """Configuration for an individual MCP server."""

    name: str
    command: list[str]
    args: list[str] | None = None
    env: dict[str, str] | None = None
    enabled: bool = True
    timeout: int = 30
    restart_on_failure: bool = True


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration."""

    enabled: bool = True
    port: int = 3001
    servers: list[MCPServerConfig] = Field(default_factory=list)
    filesystem_enabled: bool = True
    filesystem_root: str = "/app/shared"
    auto_discovery: bool = True
    discovery_ports: list[int] = Field(default_factory=lambda: [3000, 3001, 3002])
    # New: explicit external endpoints with optional headers/tokens
    # Format examples:
    # - {"name": "filesystem", "url": "http://localhost:3002", "headers": {"Authorization": "Bearer ..."}}
    # - {"url": "http://localhost:3030"}
    external_endpoints: list[dict[str, Any]] = Field(default_factory=list)
    limits: dict[str, Any] | None = None
    log_level: str = "info"


class LLMConfig(BaseModel):
    """LLM client configuration."""

    enabled: bool = True
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int | str = 60
    max_retries: int = 3
    function_calling: dict[str, Any] | None = None
    caching: dict[str, Any] | None = None
    rate_limiting: dict[str, Any] | None = None

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v):
        if v is None or v == "":
            keyring_mgr = get_keyring_manager()
            v = keyring_mgr.get_credential(
                "OPENAI_API_KEY", fallback_env="OPENAI_API_KEY"
            )
        return v

    def model_post_init(self, __context):
        """Post-initialization hook to ensure API key is loaded from keyring or environment."""
        if self.api_key is None or self.api_key == "":
            keyring_mgr = get_keyring_manager()
            self.api_key = keyring_mgr.get_credential(
                "OPENAI_API_KEY", fallback_env="OPENAI_API_KEY"
            )
        super().model_post_init(__context) if hasattr(
            super(), "model_post_init"
        ) else None


class ToolConfig(BaseModel):
    """Configuration for a single tool."""

    name: str
    description: str
    engine: str = "dagger"  # dagger, mcp, builtin
    command: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    timeout: int = 300
    enabled: bool = True


class DaggerConfig(BaseModel):
    """Dagger execution engine configuration."""

    enabled: bool = True
    socket_path: str | None = None
    timeout: int = 600
    max_concurrent: int = 5


class HTTPConfig(BaseModel):
    """HTTP server configuration."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(default=8080)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("port", mode="before")
    @classmethod
    def validate_port(cls, v):
        # Always check environment variable first
        env_port = os.getenv("HTTP_PORT")
        if env_port:
            return int(env_port)
        # Return provided value or default
        return v if v is not None else 8080


class WebSocketConfig(BaseModel):
    """WebSocket server configuration."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8090


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    websocket_enabled: bool = True
    docs_enabled: bool = True
    health_check_interval: int = 30


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    file_enabled: bool = True
    file_path: str = "logs/praxis.log"
    file_rotation: str = "10 MB"
    file_retention: str = "1 week"
    json_logs: bool = False
    file: str | None = None
    output: str | None = None


class MetricsConfig(BaseModel):
    """Metrics and monitoring configuration."""

    enabled: bool = True
    push_interval: int = 15  # seconds
    remote_write_url: str = "https://monitoring.prxs.ai/prometheus/api/v1/write"
    job_name: str = "praxis-agent"
    basic_auth_username: Optional[str] = None
    basic_auth_password: Optional[str] = None
    additional_labels: Dict[str, str] = Field(default_factory=dict)


class A2ACardEndpoint(BaseModel):
    """A2A card endpoint configuration."""

    type: str
    url: str | None = None
    address: str | None = None


class A2ACardConfig(BaseModel):
    """A2A card configuration."""

    id: str
    name: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    protocols: list[str] = Field(default_factory=list)
    endpoints: list[A2ACardEndpoint] = Field(default_factory=list)


class A2AConfig(BaseModel):
    """A2A protocol configuration."""

    enabled: bool = True
    card: A2ACardConfig | None = None
    discovery: dict[str, Any] | None = None


class ToolParam(BaseModel):
    """Tool parameter configuration."""

    name: str
    type: str
    description: str | None = None
    required: bool | str = False


class ToolEngineSpec(BaseModel):
    """Tool engine specification."""

    image: str | None = None
    command: list[str] | None = None
    address: str | None = None
    mounts: dict[str, str] | None = None
    env_passthrough: list[str] | None = None


class ToolConfigNew(BaseModel):
    """New tool configuration format matching Go SDK."""

    name: str
    description: str
    engine: str = "dagger"
    params: list[ToolParam] = Field(default_factory=list)
    engineSpec: ToolEngineSpec | None = None


class AgentLevelConfig(BaseModel):
    """Agent-level configuration."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    url: str | None = None
    shared_dir: str | None = None
    tools: list[ToolConfigNew] = Field(default_factory=list)
    external_mcp_endpoints: list[str | dict[str, Any]] = Field(default_factory=list)
    external_mcp_servers: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Individual agent configuration."""

    name: str
    description: str = ""
    enabled: bool = True
    tools: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    max_concurrent_tasks: int = 10
    task_timeout: int = 300


class PraxisConfig(BaseSettings):
    """Main Praxis SDK configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PRAXIS_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra environment variables
    )

    # Core settings
    environment: str = "development"
    debug: bool = False
    config_file: str | None = None
    data_dir: str = "./data"
    shared_dir: str = "/shared"

    # Component configurations
    p2p: P2PConfig = Field(default_factory=P2PConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    http: HTTPConfig | None = None
    websocket: WebSocketConfig | None = None
    a2a: A2AConfig | None = None
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    dagger: DaggerConfig = Field(default_factory=DaggerConfig)

    # Agent-level configuration (for single agent configs)
    agent: AgentLevelConfig | None = None

    # Agent and tool configurations
    agents: list[AgentConfig] = Field(default_factory=list)
    tools: list[ToolConfig] = Field(default_factory=list)

    # Additional settings
    metrics_enabled: bool = True
    health_checks_enabled: bool = True
    shutdown_timeout: int = 30

    @field_validator("data_dir", "shared_dir", mode="before")
    @classmethod
    def validate_directories(cls, v):
        """Validate directory paths."""
        # Don't create directories during validation
        # They will be created when actually needed
        return v

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        try:
            Path(self.data_dir).mkdir(parents=True, exist_ok=True)
            Path(self.shared_dir).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Ignore if directory is read-only or already exists
            pass

    @classmethod
    def load_from_yaml(cls, yaml_path: str | Path) -> "PraxisConfig":
        """Load configuration from YAML file."""
        yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        try:
            with open(yaml_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            # Start with defaults and override with YAML data
            config_dict = {}

            # Handle component configurations from YAML
            if "p2p" in yaml_data:
                config_dict["p2p"] = yaml_data["p2p"]
            if "mcp" in yaml_data:
                config_dict["mcp"] = yaml_data["mcp"]
            if "llm" in yaml_data:
                config_dict["llm"] = yaml_data["llm"]
            if "api" in yaml_data:
                config_dict["api"] = yaml_data["api"]
            if "http" in yaml_data:
                config_dict["http"] = yaml_data["http"]
            if "websocket" in yaml_data:
                config_dict["websocket"] = yaml_data["websocket"]
            if "a2a" in yaml_data:
                config_dict["a2a"] = yaml_data["a2a"]
            if "logging" in yaml_data:
                config_dict["logging"] = yaml_data["logging"]
            if "dagger" in yaml_data:
                config_dict["dagger"] = yaml_data["dagger"]

            # Handle agent-level configuration
            if "agent" in yaml_data:
                config_dict["agent"] = yaml_data["agent"]

                # Extract tools from agent config if present
                if "tools" in yaml_data["agent"]:
                    config_dict["tools"] = yaml_data["agent"]["tools"]

            # Create config with merged data
            config = cls(**config_dict)

            return config
        except Exception as e:
            logger.error(f"Error loading YAML configuration: {e}")
            raise

    def get_tool_config(self, tool_name: str) -> ToolConfig | None:
        """Get configuration for a specific tool."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def get_agent_config(self, agent_name: str) -> AgentConfig | None:
        """Get configuration for a specific agent."""
        for agent in self.agents:
            if agent.name == agent_name:
                return agent
        return None

    def add_agent(self, agent_config: AgentConfig) -> None:
        """Add or update an agent configuration."""
        # Remove existing agent with same name
        self.agents = [a for a in self.agents if a.name != agent_config.name]
        self.agents.append(agent_config)

    def add_tool(self, tool_config: ToolConfig) -> None:
        """Add or update a tool configuration."""
        # Remove existing tool with same name
        self.tools = [t for t in self.tools if t.name != tool_config.name]
        self.tools.append(tool_config)


def load_config(config_file: str | None = None) -> PraxisConfig:
    """Load configuration from file or environment."""
    if config_file and Path(config_file).exists():
        logger.info(f"Loading configuration from: {config_file}")
        return PraxisConfig.load_from_yaml(config_file)
    logger.info("Using default configuration with environment overrides")
    return PraxisConfig()
