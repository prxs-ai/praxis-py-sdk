"""LLM client implementation with OpenAI API support."""

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ..config import LLMConfig


class LLMClient:
    """LLM client for OpenAI API with retry logic and streaming support."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client: AsyncOpenAI | None = None
        self._initialized = False

    async def initialize(self):
        """Initialize LLM client."""
        if self._initialized:
            return

        try:
            # Normalize timeout (accept "30s", 30, "15")
            timeout_val = self.config.timeout
            if isinstance(timeout_val, str):
                t = timeout_val.strip().lower()
                if t.endswith("ms"):
                    timeout_val = max(0.001, float(t[:-2]) / 1000.0)
                elif t.endswith("s"):
                    timeout_val = float(t[:-1])
                else:
                    # treat bare number string as seconds
                    timeout_val = float(t)

            # Log sanitized settings without secrets
            logger.info(
                f"LLM init: provider=openai, model={self.config.model}, base_url={self.config.base_url or 'https://api.openai.com/v1'}, api_key_set={bool(self.config.api_key)}, timeout={timeout_val}, retries={self.config.max_retries}"
            )

            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=timeout_val,
                max_retries=self.config.max_retries,
            )

            # Test connection
            await self.client.models.list()

            self._initialized = True
            logger.success(f"LLM client initialized with model: {self.config.model}")

        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> ChatCompletion:
        """Create a chat completion with optional function calling.

        Args:
            messages: Chat messages
            tools: Available tools for function calling
            tool_choice: Tool selection mode ("auto", "none", or specific tool)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            Chat completion response

        """
        if not self._initialized:
            await self.initialize()

        # Use config defaults if not specified
        temperature = (
            temperature if temperature is not None else self.config.temperature
        )
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            # Debug logging for LLM request
            try:
                tool_count = len(tools) if tools else 0
                first_names = []
                if tools:
                    for t in tools[:5]:
                        if isinstance(t, dict):
                            fn = (
                                t.get("function", {}).get("name")
                                if "function" in t
                                else t.get("name")
                            )
                            if fn:
                                first_names.append(fn)
                logger.info(
                    f"🧠 LLM request: model={self.config.model}, messages={len(messages)}, tools={tool_count}, tool_choice={tool_choice}"
                )
                if first_names:
                    logger.debug(f"   🔧 First tools: {first_names}")
                if messages:
                    # Log last user message snippet
                    last_user = next(
                        (m for m in reversed(messages) if m.get("role") == "user"), None
                    )
                    if last_user:
                        content = str(last_user.get("content", ""))
                        logger.debug(
                            f"   📨 User: {content[:120]}{'...' if len(content) > 120 else ''}"
                        )
            except Exception:
                pass

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )

            try:
                msg = response.choices[0].message
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    logger.info(f"🛠️  LLM tool calls: {len(msg.tool_calls)}")
                    for i, tc in enumerate(msg.tool_calls, 1):
                        try:
                            name = tc.function.name
                            args = tc.function.arguments
                            logger.info(
                                f"   [{i}] {name} args={args[:200] if isinstance(args, str) else args}"
                            )
                        except Exception:
                            pass
                else:
                    logger.info("💬 LLM response without tool calls")
            except Exception:
                pass

            return response

        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise

    async def simple_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Simple text completion without function calling.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self.chat_completion(
            messages=messages, temperature=temperature, max_tokens=max_tokens
        )

        return response.choices[0].message.content or ""

    async def function_calling(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Execute function calling based on prompt.

        Args:
            prompt: User prompt
            tools: Available tools
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Function call results

        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append(
                {
                    "role": "system",
                    "content": "You are a helpful assistant that executes functions based on user requests.",
                }
            )

        messages.append({"role": "user", "content": prompt})

        response = await self.chat_completion(
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        message = response.choices[0].message

        if message.tool_calls:
            return {
                "has_tool_calls": True,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in message.tool_calls
                ],
                "content": message.content,
            }
        return {"has_tool_calls": False, "content": message.content}

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """Stream a chat completion.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Yields:
            Streamed response chunks

        """
        if not self._initialized:
            await self.initialize()

        temperature = (
            temperature if temperature is not None else self.config.temperature
        )
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error in stream completion: {e}")
            raise

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the configured model."""
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "initialized": self._initialized,
        }
