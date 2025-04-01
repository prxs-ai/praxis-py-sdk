import asyncio
import logging
from typing import Optional

from openai import AsyncOpenAI, RateLimitError

from send_openai_request.config import get_settings

settings = get_settings()

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def send_openai_request(
        messages: list,
        temperature: float | int = 1,
        model: str = settings.OPEN_AI_MODEL,
        max_retries: int = 10,
        initial_retry_delay: float = 0.5
) -> Optional[str]:
    """
    Send request to OpenAI with retry mechanism for rate limits.

    Args:
        messages: List of messages for the chat completion
        temperature: Temperature parameter for response generation
        model: OpenAI model to use
        max_retries: Maximum number of retries on rate limit
        initial_retry_delay: Initial delay before retry in seconds (doubles with each retry)
    """
    retry_count = 0
    retry_delay = initial_retry_delay

    while retry_count < max_retries:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=20,
            )
            return response.choices[0].message.content

        except RateLimitError as e:
            retry_count += 1
            if retry_count == max_retries:
                logging.error(f"Rate limit exceeded after {max_retries} retries: {e}")
                raise e

            logging.warning(f"Rate limit hit, attempt {retry_count}/{max_retries}. Waiting {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2

        except Exception as e:
            logging.error(f"Error in OpenAI request: {type(e).__name__}: {str(e)}")
            raise e

    return None


async def get_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding
