import json
from functools import lru_cache
from typing import Any

import pydantic
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from praxis_sdk.agents.exceptions import ConfigurationError


class RelayService(BaseSettings):
    """Configuration for the relay service connection."""
    host: str = pydantic.Field(default="relay-service.dev.prxs.ai/", description="Host for relay service")
    port: int = pydantic.Field(default=80, ge=1, le=65535, description="Port for relay service")
    schema: str = pydantic.Field(default="https://", description="https:// or http://")
    
    @field_validator("schema")
    @classmethod
    def validate_schema(cls, value: str) -> str:
        """Validate that schema is either http:// or https://.
        
        Args:
            value: Schema value to validate
            
        Returns:
            Validated schema value
            
        Raises:
            ValueError: If schema is not http:// or https://
        """
        if value not in ("http://", "https://"):
            raise ValueError("Schema must be either 'http://' or 'https://'")
        return value
    
    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        """Validate host is not empty and properly formatted.
        
        Args:
            value: Host value to validate
            
        Returns:
            Validated host value
            
        Raises:
            ValueError: If host is empty or invalid
        """
        if not value or not value.strip():
            raise ValueError("Host cannot be empty")
        return value.strip()

    @property
    def url(self) -> str:
        """Generate the complete URL for the relay service.
        
        Returns:
            Complete URL for the relay service
        """
        try:
            if (self.schema == "https://" and self.port == 443) or (self.schema == "http://" and self.port == 80):
                return f"{self.schema}{self.host}"
            return f"{self.schema}{self.host}:{self.port}"
        except Exception as e:
            raise ConfigurationError(f"Failed to generate relay service URL: {e}") from e


class BasicAgentConfig(BaseSettings):
    """Basic configuration settings for an agent instance."""
    system_prompt: str = "Act as a helpful assistant. You are given a task to complete."
    agents: dict[str, str] = pydantic.Field(default_factory=dict)

    # Libp2p configuration
    registry_http_url: str = pydantic.Field("http://localhost:8081")
    registry_relay_peer_id: str = pydantic.Field("12D3KooWL1N7R2UDf9bVeyP6QR2hR7F1qXSkX5cv3H5Xz7N4L7kE")
    registry_relay_multiaddr_template: str = pydantic.Field("/ip4/127.0.0.1/tcp/4001/p2p/{}")
    agent_p2p_listen_addr: str = pydantic.Field("/ip4/0.0.0.0/tcp/0")
    agent_name: str = pydantic.Field("base-agent", min_length=1)
    
    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, value: str) -> str:
        """Validate system prompt is not empty.
        
        Args:
            value: System prompt to validate
            
        Returns:
            Validated system prompt
            
        Raises:
            ValueError: If system prompt is empty
        """
        if not value or not value.strip():
            raise ValueError("System prompt cannot be empty")
        return value.strip()
    
    @field_validator("registry_http_url")
    @classmethod
    def validate_registry_url(cls, value: str) -> str:
        """Validate registry HTTP URL format.
        
        Args:
            value: URL to validate
            
        Returns:
            Validated URL
            
        Raises:
            ValueError: If URL format is invalid
        """
        if not value.startswith(("http://", "https://")):
            raise ValueError("Registry HTTP URL must start with http:// or https://")
        return value

    relay_service: RelayService = RelayService()  # type: ignore

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    def __str__(self) -> str:
        """Serialize the config to a pretty JSON string for prompt usage.
        
        Returns:
            JSON string representation of the configuration
            
        Raises:
            ConfigurationError: If serialization fails
        """
        try:
            return json.dumps(self.model_dump(), indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to serialize configuration: {e}") from e


@lru_cache
def get_agent_config(**kwargs: Any) -> BasicAgentConfig:
    """Get cached agent configuration instance.
    
    Args:
        **kwargs: Configuration parameters to pass to BasicAgentConfig
        
    Returns:
        Cached BasicAgentConfig instance
        
    Raises:
        ConfigurationError: If configuration creation fails
    """
    try:
        return BasicAgentConfig(**kwargs)
    except Exception as e:
        raise ConfigurationError(f"Failed to create agent configuration: {e}") from e
