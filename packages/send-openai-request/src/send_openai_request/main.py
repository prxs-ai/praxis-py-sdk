import logging

from openai import AsyncOpenAI, RateLimitError
from tenacity import retry, stop_after_attempt, wait_fixed

from send_openai_request.config import get_settings

settings = get_settings()

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def send_openai_request(
    messages: list,
    temperature: float = 1,
    model: str = settings.OPEN_AI_MODEL,
) -> str | None:
    """Send request to OpenAI with retry mechanism for rate limits.

    Args:
        messages: List of messages for the chat completion
        temperature: Temperature parameter for response generation
        model: OpenAI model to use

    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            timeout=20,
        )
        return response.choices[0].message.content

    except RateLimitError as e:
        logging.error(f"Error in OpenAI request: {type(e).__name__}: {str(e)}")
        raise e


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def get_embedding(text: str) -> list[float]:
    """Get embedding from OpenAI.

    Args:
        text: Text to get embedding from

    Returns:
        Embedding from OpenAI

    """
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL, input=text
        )
        return response.data[0].embedding
    except RateLimitError as e:
        logging.error(
            f"Error in OpenAI embedding request: {type(e).__name__}: {str(e)}"
        )
        raise e
