from typing import Sequence
from base_agent.models import AgentModel, ToolModel
from base_agent.prompt.parser import AgentOutputPlanParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from base_agent.langchain.config import BasicLangChainConfig, LangChainConfigWithLangfuse


class LangChainExecutor:
    def __init__(self, config: BasicLangChainConfig | LangChainConfigWithLangfuse):
        self.config = config

        self._callbacks = []
        if self.config.langfuse_enabled:
            self._init_langfuse_callback()

    def _init_langfuse_callback(self):
        from langfuse.callback import CallbackHandler

        self._callbacks.append(
            CallbackHandler(
                public_key=self.config.langfuse_public_key.get_secret_value(),
                secret_key=self.config.langfuse_secret_key.get_secret_value(),
                host=self.config.langfuse_host,
            )
        )

    def generate_plan(self, prompt: PromptTemplate, **kwargs):
        agent = ChatOpenAI(callbacks=self._callbacks)
        output_parser = StrOutputParser()
        if 'available_functions' in kwargs:
            agent.bind_tools(tools=[tool.openai_function_spec for tool in kwargs['available_functions']])
            output_parser = AgentOutputPlanParser(tools=kwargs['available_functions'])

        kwargs['available_functions'] = "\n".join([tool.render_openai_function_spec() for tool in kwargs['available_functions']])

        chain = prompt | agent | output_parser

        return chain.invoke(input=kwargs)
