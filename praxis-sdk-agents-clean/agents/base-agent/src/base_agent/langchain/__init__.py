from base_agent.langchain.config import get_langchain_config
from base_agent.langchain.executor import LangChainExecutor


def agent_executor(*args, **kwargs):
    return LangChainExecutor(config=get_langchain_config())
