from typing import Any

from jinja2 import Environment, TemplateError
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

from praxis_sdk.agents.abc import AbstractPromptBuilder
from praxis_sdk.agents.exceptions import PromptBuildingError, ConfigurationError
from praxis_sdk.agents.prompt.config import BasicPromptConfig
from praxis_sdk.agents.prompt.const import FINISH_ACTION, HANDOFF_ACTION
from praxis_sdk.agents.prompt.utils import get_environment


class PromptBuilder(AbstractPromptBuilder):
    """Enhanced prompt builder with improved error handling and validation."""
    
    def __init__(self, config: BasicPromptConfig, jinja2_env: Environment) -> None:
        """Initialize prompt builder with configuration and Jinja2 environment.
        
        Args:
            config: Prompt configuration
            jinja2_env: Jinja2 environment for template rendering
            
        Raises:
            ConfigurationError: If configuration or environment is invalid
        """
        if not isinstance(config, BasicPromptConfig):
            raise ConfigurationError("Invalid prompt configuration provided")
            
        if not isinstance(jinja2_env, Environment):
            raise ConfigurationError("Invalid Jinja2 environment provided")
            
        self.config = config
        self.jinja2_env = jinja2_env
        
    def _render_template(self, template_name: str, **kwargs: Any) -> str:
        """Safely render a Jinja2 template with error handling.
        
        Args:
            template_name: Name of the template to render
            **kwargs: Template variables
            
        Returns:
            Rendered template string
            
        Raises:
            PromptBuildingError: If template rendering fails
        """
        try:
            template = self.jinja2_env.get_template(template_name)
            return template.render(**kwargs)
        except TemplateError as e:
            raise PromptBuildingError(f"Template rendering failed for '{template_name}': {e}") from e
        except Exception as e:
            raise PromptBuildingError(f"Unexpected error rendering template '{template_name}': {e}") from e

    def generate_plan_prompt(self, *args: Any, system_prompt: str, **kwargs: Any) -> ChatPromptTemplate:
        """Generate a planning prompt with enhanced error handling.
        
        Args:
            *args: Positional arguments (unused but kept for interface compatibility)
            system_prompt: System prompt content
            **kwargs: Additional keyword arguments
            
        Returns:
            ChatPromptTemplate for plan generation
            
        Raises:
            PromptBuildingError: If prompt generation fails
        """
        try:
            # Render system message template
            system_message = self._render_template(
                self.config.system_prompt_template,
                system_prompt=system_prompt
            )
            
            # Render examples template
            examples = self._render_template(
                self.config.generate_plan_examples_template,
                finish_action=FINISH_ACTION,
                handoff_action=HANDOFF_ACTION
            )
            
            # Render human message template
            human_message = self._render_template(
                self.config.chat_template,
                finish_action=FINISH_ACTION,
                handoff_action=HANDOFF_ACTION,
                examples=examples,
                **kwargs
            )
            
            return ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_message),
                HumanMessagePromptTemplate.from_template(human_message),
            ])
            
        except PromptBuildingError:
            raise
        except Exception as e:
            raise PromptBuildingError(f"Failed to generate plan prompt: {e}") from e

    def generate_chat_prompt(
        self, *args: Any, system_prompt: str, user_prompt: str, context: str, **kwargs: Any
    ) -> ChatPromptTemplate:
        """Generate a chat prompt with enhanced error handling.
        
        Args:
            *args: Positional arguments (unused but kept for interface compatibility)
            system_prompt: System prompt content
            user_prompt: User's message content
            context: Conversation context
            **kwargs: Additional keyword arguments
            
        Returns:
            ChatPromptTemplate for chat interaction
            
        Raises:
            PromptBuildingError: If prompt generation fails
        """
        try:
            # Render system message template
            system_message = self._render_template(
                self.config.system_prompt_template,
                system_prompt=system_prompt
            )
            
            # Render human message template
            human_message = self._render_template(
                self.config.chat_template,
                context=context,
                user_message=user_prompt,
                **kwargs
            )
            
            return ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_message),
                HumanMessagePromptTemplate.from_template(human_message),
            ])
            
        except PromptBuildingError:
            raise
        except Exception as e:
            raise PromptBuildingError(f"Failed to generate chat prompt: {e}") from e

    def generate_intent_classifier_prompt(
        self, *args: Any, system_prompt: str, user_prompt: str, **kwargs: Any
    ) -> ChatPromptTemplate:
        """Generate an intent classification prompt with enhanced error handling.
        
        Args:
            *args: Positional arguments (unused but kept for interface compatibility)
            system_prompt: System prompt content
            user_prompt: User's message to classify
            **kwargs: Additional keyword arguments
            
        Returns:
            ChatPromptTemplate for intent classification
            
        Raises:
            PromptBuildingError: If prompt generation fails
        """
        try:
            # Render system message template
            system_message = self._render_template(
                self.config.system_prompt_template,
                system_prompt=system_prompt
            )
            
            # Render examples template
            examples = self._render_template(self.config.intent_classifier_examples_template)
            
            # Render human message template
            human_message = self._render_template(
                self.config.intent_classifier_template,
                user_message=user_prompt,
                examples=examples,
                **kwargs
            )
            
            return ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_message),
                HumanMessagePromptTemplate.from_template(human_message),
            ])
            
        except PromptBuildingError:
            raise
        except Exception as e:
            raise PromptBuildingError(f"Failed to generate intent classifier prompt: {e}") from e

    def generate_reconfigure_prompt(
        self, *args: Any, system_prompt: str, user_prompt: str, existing_config: str, **kwargs: Any
    ) -> ChatPromptTemplate:
        """Generate a reconfiguration prompt with enhanced error handling.
        
        Args:
            *args: Positional arguments (unused but kept for interface compatibility)
            system_prompt: System prompt content
            user_prompt: User's reconfiguration request
            existing_config: Current configuration to update
            **kwargs: Additional keyword arguments
            
        Returns:
            ChatPromptTemplate for configuration updates
            
        Raises:
            PromptBuildingError: If prompt generation fails
        """
        try:
            # Render system message template
            system_message = self._render_template(
                self.config.system_prompt_template,
                system_prompt=system_prompt
            )
            
            # Render examples template
            examples = self._render_template(self.config.update_config_examples_template)
            
            # Render human message template
            human_message = self._render_template(
                self.config.update_config_template,
                user_message=user_prompt,
                existing_config=existing_config,
                examples=examples,
                **kwargs
            )
            
            return ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_message),
                HumanMessagePromptTemplate.from_template(human_message),
            ])
            
        except PromptBuildingError:
            raise
        except Exception as e:
            raise PromptBuildingError(f"Failed to generate reconfigure prompt: {e}") from e


def prompt_builder(config: BasicPromptConfig) -> PromptBuilder:
    """Factory function to create a PromptBuilder instance.
    
    Args:
        config: Prompt configuration
        
    Returns:
        Configured PromptBuilder instance
        
    Raises:
        ConfigurationError: If builder creation fails
    """
    try:
        jinja2_env = get_environment(config.template_path)
        return PromptBuilder(config, jinja2_env)
    except Exception as e:
        raise ConfigurationError(f"Failed to create prompt builder: {e}") from e
