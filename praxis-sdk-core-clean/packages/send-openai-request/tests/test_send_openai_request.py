from unittest.mock import AsyncMock

import pytest
from openai import RateLimitError
from send_openai_request import get_embedding, send_openai_request


@pytest.fixture
def mock_openai_client(mocker):
    mock_client = AsyncMock()
    mocker.patch("send_openai_request.client", mock_client)
    return mock_client


@pytest.fixture
def mock_settings():
    class MockSettings:
        OPENAI_API_KEY = "test_key"
        OPEN_AI_MODEL = "gpt-3.5-turbo"
        OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"

    return MockSettings()


@pytest.mark.asyncio
async def test_send_openai_request_success(mock_openai_client, mock_settings, mocker):
    mocker.patch("send_openai_request.get_settings", return_value=mock_settings)
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="test response"))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    result = await send_openai_request(
        messages=[{"role": "user", "content": "test"}], temperature=0.7
    )

    assert result == "test response"
    mock_openai_client.chat.completions.create.assert_called_once_with(
        model=mock_settings.OPEN_AI_MODEL,
        messages=[{"role": "user", "content": "test"}],
        temperature=0.7,
        timeout=20,
    )


@pytest.mark.asyncio
async def test_send_openai_request_rate_limit(
    mock_openai_client, mock_settings, mocker, caplog
):
    mocker.patch("send_openai_request.get_settings", return_value=mock_settings)
    mock_openai_client.chat.completions.create.side_effect = RateLimitError(
        "Rate limit exceeded", None
    )

    with pytest.raises(RateLimitError):
        await send_openai_request(messages=[{"role": "user", "content": "test"}])

    assert mock_openai_client.chat.completions.create.call_count == 3
    assert "Error in OpenAI request: RateLimitError: Rate limit exceeded" in caplog.text


@pytest.mark.asyncio
async def test_get_embedding_success(mock_openai_client, mock_settings, mocker):
    mocker.patch("send_openai_request.get_settings", return_value=mock_settings)
    mock_response = AsyncMock()
    mock_response.data = [AsyncMock(embedding=[0.1, 0.2, 0.3])]
    mock_openai_client.embeddings.create.return_value = mock_response

    result = await get_embedding("test text")

    assert result == [0.1, 0.2, 0.3]
    mock_openai_client.embeddings.create.assert_called_once_with(
        model=mock_settings.OPENAI_EMBEDDING_MODEL, input="test text"
    )


@pytest.mark.asyncio
async def test_get_embedding_rate_limit(
    mock_openai_client, mock_settings, mocker, caplog
):
    mocker.patch("send_openai_request.get_settings", return_value=mock_settings)
    mock_openai_client.embeddings.create.side_effect = RateLimitError(
        "Rate limit exceeded", None
    )

    with pytest.raises(RateLimitError):
        await get_embedding("test text")

    assert mock_openai_client.embeddings.create.call_count == 3
    assert (
        "Error in OpenAI embedding request: RateLimitError: Rate limit exceeded"
        in caplog.text
    )
