from typing import Any, Union

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from praxis_sdk.agents.abc import AbstractChatResponse, AbstractExecutor
from praxis_sdk.agents.exceptions import ConfigurationError
from praxis_sdk.agents.langchain.config import BasicLangChainConfig, LangChainConfigWithLangfuse
from praxis_sdk.agents.prompt.parser import AgentOutputPlanParser


class ChatResponse(AbstractChatResponse):
    """Enhanced chat response with session UUID tracking."""
    session_uuid: str


class LangChainExecutor(AbstractExecutor):
    """LangChain-based executor with improved error handling and code reuse."""
    
    def __init__(self, config: BasicLangChainConfig | LangChainConfigWithLangfuse) -> None:
        """Initialize executor with configuration and optional Langfuse callbacks.
        
        Args:
            config: LangChain configuration instance
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not isinstance(config, (BasicLangChainConfig, LangChainConfigWithLangfuse)):
            raise ConfigurationError("Invalid configuration type provided")
            
        self.config = config
        self._callbacks: list = []
        
        if self.config.langfuse_enabled:
            self._init_langfuse_callback()

    def _init_langfuse_callback(self) -> None:
        """Initialize Langfuse callback handler with proper error handling."""
        try:
            from langfuse.callback import CallbackHandler

            self._callbacks.append(
                CallbackHandler(
                    public_key=self.config.langfuse_public_key.get_secret_value(),
                    secret_key=self.config.langfuse_secret_key.get_secret_value(),
                    host=self.config.langfuse_host,
                )
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Langfuse callback: {e}") from e

    def _create_agent(self) -> ChatOpenAI:
        """Create and configure ChatOpenAI agent instance.
        
        Returns:
            Configured ChatOpenAI instance
            
        Raises:
            ConfigurationError: If agent creation fails
        """
        try:
            return ChatOpenAI(
                callbacks=self._callbacks,
                model=self.config.openai_api_model
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to create ChatOpenAI agent: {e}") from e

    def _execute_chain(
        self, 
        prompt: PromptTemplate, 
        output_parser: Any, 
        agent: ChatOpenAI | None = None,
        **kwargs: Any
    ) -> Any:
        """Execute a LangChain with standardized error handling.
        
        Args:
            prompt: The prompt template to use
            output_parser: Output parser to process results
            agent: Optional pre-configured agent (creates new if None)
            **kwargs: Additional arguments for chain invocation
            
        Returns:
            Chain execution result
            
        Raises:
            RuntimeError: If chain execution fails
        """
        if agent is None:
            agent = self._create_agent()
            
        try:
            chain = prompt | agent | output_parser
            return chain.invoke(input=kwargs)
        except Exception as e:
            raise RuntimeError(f"Chain execution failed: {e}") from e

    def generate_plan(self, prompt: PromptTemplate, **kwargs: Any) -> str:
        """Generate execution plan with tool binding support.
        
        Args:
            prompt: Plan generation prompt template
            **kwargs: Additional context including available_functions
            
        Returns:
            Generated plan as string
        """
        agent = self._create_agent()
        output_parser = StrOutputParser()
        
        # Handle tool binding for plan generation
        if "available_functions" in kwargs and kwargs["available_functions"]:
            try:
                agent = agent.bind_tools(
                    tools=[tool.openai_function_spec for tool in kwargs["available_functions"]]
                )
                output_parser = AgentOutputPlanParser(tools=kwargs["available_functions"])
                
                # Convert tools to human-readable format for prompt
                kwargs["available_functions"] = "\n".join(
                    tool.render_function_spec() for tool in kwargs["available_functions"]
                )
            except Exception as e:
                raise RuntimeError(f"Failed to bind tools for plan generation: {e}") from e

        return self._execute_chain(prompt, output_parser, agent, **kwargs)

    def chat(self, prompt: PromptTemplate, **kwargs: Any) -> str:
        """Generate chat response.
        
        Args:
            prompt: Chat prompt template
            **kwargs: Additional context for chat generation
            
        Returns:
            Chat response as string
        """
        return self._execute_chain(prompt, StrOutputParser(), **kwargs)

    def classify_intent(self, prompt: PromptTemplate, **kwargs: Any) -> str:
        """Classify user intent from input.
        
        Args:
            prompt: Intent classification prompt template
            **kwargs: Additional context for intent classification
            
        Returns:
            Classified intent as string
        """
        return self._execute_chain(prompt, StrOutputParser(), **kwargs)

    def reconfigure(self, prompt: PromptTemplate, **kwargs: Any) -> dict[str, Any]:
        """Generate configuration updates.
        
        Args:
            prompt: Reconfiguration prompt template
            **kwargs: Additional context for reconfiguration
            
        Returns:
            Configuration updates as dictionary
        """
        return self._execute_chain(prompt, JsonOutputParser(), **kwargs)


def agent_executor(config: BasicLangChainConfig | LangChainConfigWithLangfuse):
    return LangChainExecutor(config=config)
