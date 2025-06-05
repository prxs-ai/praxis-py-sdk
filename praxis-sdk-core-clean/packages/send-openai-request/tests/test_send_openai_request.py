import pytest
from unittest.mock import AsyncMock, patch
from openai import RateLimitError


with patch("send_openai_request.config.Settings") as mock_settings:
    return_value = AsyncMock(
        infrastructure=AsyncMock(
            OPENAI_API_KEY="test-api-key",
            OPEN_AI_MODEL="gpt-test-model",
            OPENAI_EMBEDDING_MODEL="embedding-test-model"
        )
    )
    with patch("send_openai_request.main.client") as mock_openai:
        from send_openai_request.main import client, send_openai_request, get_embedding


@pytest.fixture
def mock_openai_client():
    with patch("send_openai_request.main.AsyncOpenAI") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.chat.completions.create = AsyncMock()
        mock_instance.embeddings.create = AsyncMock()
        yield mock_instance


@pytest.mark.asyncio
async def test_send_openai_request_success(mock_openai_client):
    test_messages = [{"role": "user", "content": "Hello"}]
    test_response = AsyncMock()
    test_response.choices = [AsyncMock(message=AsyncMock(content="Test response"))]
    mock_openai_client.chat.completions.create.return_value = test_response

    result = await send_openai_request(messages=test_messages)

    assert result == "Test response"
    mock_openai_client.chat.completions.create.assert_awaited_once_with(
        model="gpt-test-model",
        messages=test_messages,
        temperature=1,
        timeout=20
    )


@pytest.mark.asyncio
async def test_send_openai_request_rate_limit(mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded")

    with pytest.raises(RateLimitError):
        await send_openai_request(messages=[{"role": "user", "content": "Hello"}])

    assert mock_openai_client.chat.completions.create.await_count == 3


@pytest.mark.asyncio
async def test_get_embedding_success(mock_openai_client):
    test_text = "test text"
    test_embedding = [0.1, 0.2, 0.3]
    test_response = AsyncMock()
    test_response.data = [AsyncMock(embedding=test_embedding)]
    mock_openai_client.embeddings.create.return_value = test_response

    result = await get_embedding(text=test_text)

    assert result == test_embedding
    mock_openai_client.embeddings.create.assert_awaited_once_with(
        model="embedding-test-model",
        input=test_text
    )


@pytest.mark.asyncio
async def test_get_embedding_rate_limit(mock_openai_client):
    mock_openai_client.embeddings.create.side_effect = RateLimitError("Rate limit exceeded")

    with pytest.raises(RateLimitError):
        await get_embedding(text="test text")

    assert mock_openai_client.embeddings.create.await_count == 3


@pytest.mark.asyncio
async def test_send_openai_request_custom_params(mock_openai_client):
    test_messages = [{"role": "user", "content": "Hello"}]
    test_response = AsyncMock()
    test_response.choices = [AsyncMock(message=AsyncMock(content="Test response"))]
    mock_openai_client.chat.completions.create.return_value = test_response

    result = await send_openai_request(
        messages=test_messages,
        temperature=0.5,
        model="custom-model"
    )

    assert result == "Test response"
    mock_openai_client.chat.completions.create.assert_awaited_once_with(
        model="custom-model",
        messages=test_messages,
        temperature=0.5,
        timeout=20
    )


@pytest.mark.asyncio
async def test_send_openai_request_empty_messages():
    with patch("send_openai_request.main.get_settings") as mock_settings:
        mock_settings.return_value = AsyncMock(
            OPENAI_API_KEY="test-api-key",
            OPEN_AI_MODEL="gpt-test-model"
        )
        with patch("send_openai_request.main.AsyncOpenAI") as mock_client:
            with pytest.raises(ValueError, match="Messages list cannot be empty"):
                await send_openai_request(messages=[])


@pytest.mark.asyncio
async def test_send_openai_request_invalid_temperature_low():
    with patch("send_openai_request.main.get_settings"):
        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            await send_openai_request(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=-0.1
            )


@pytest.mark.asyncio
async def test_send_openai_request_invalid_temperature_high():
    with patch("send_openai_request.main.get_settings"):
        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            await send_openai_request(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=2.1
            )


@pytest.mark.asyncio
async def test_send_openai_request_api_connection_error():
    with patch("send_openai_request.main.get_settings") as mock_settings:
        mock_settings.return_value = AsyncMock(
            OPENAI_API_KEY="test-api-key",
            OPEN_AI_MODEL="gpt-test-model"
        )
        with patch("send_openai_request.main.AsyncOpenAI") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.chat.completions.create.side_effect = APIConnectionError("Connection failed")

            with pytest.raises(APIConnectionError):
                await send_openai_request(messages=[{"role": "user", "content": "Hello"}])

            assert mock_instance.chat.completions.create.await_count == 3


# Дополнительные тесты для get_embedding
@pytest.mark.asyncio
async def test_get_embedding_empty_string():
    with patch("send_openai_request.main.get_settings") as mock_settings:
        mock_settings.return_value = AsyncMock(
            OPENAI_API_KEY="test-api-key",
            OPENAI_EMBEDDING_MODEL="embedding-test-model"
        )
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await get_embedding(text="")


@pytest.mark.asyncio
async def test_get_embedding_api_connection_error():
    with patch("send_openai_request.main.get_settings") as mock_settings:
        mock_settings.return_value = AsyncMock(
            OPENAI_API_KEY="test-api-key",
            OPENAI_EMBEDDING_MODEL="embedding-test-model"
        )
        with patch("send_openai_request.main.AsyncOpenAI") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.embeddings.create.side_effect = APIConnectionError("Connection failed")

            with pytest.raises(APIConnectionError):
                await get_embedding(text="test text")

            assert mock_instance.embeddings.create.await_count == 3


@pytest.mark.asyncio
async def test_get_embedding_long_text_truncation():
    with patch("send_openai_request.main.get_settings") as mock_settings:
        mock_settings.return_value = AsyncMock(
            OPENAI_API_KEY="test-api-key",
            OPENAI_EMBEDDING_MODEL="embedding-test-model"
        )
        with patch("send_openai_request.main.AsyncOpenAI") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.embeddings.create = AsyncMock()
            test_embedding = [0.1, 0.2, 0.3]
            test_response = AsyncMock()
            test_response.data = [AsyncMock(embedding=test_embedding)]
            mock_instance.embeddings.create.return_value = test_response

            long_text = "a" * 10000  # Длинный текст
            result = await get_embedding(text=long_text)

            assert result == test_embedding
            called_with = mock_instance.embeddings.create.call_args[1]
            assert len(called_with["input"]) <= 8192  # Проверяем обрезку текста


# Тест для проверки дефолтных значений
@pytest.mark.asyncio
async def test_send_openai_request_default_values():
    with patch("send_openai_request.main.get_settings") as mock_settings:
        mock_settings.return_value = AsyncMock(
            OPENAI_API_KEY="test-api-key",
            OPEN_AI_MODEL="gpt-test-model"
        )
        with patch("send_openai_request.main.AsyncOpenAI") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.chat.completions.create = AsyncMock()
            test_response = AsyncMock()
            test_response.choices = [AsyncMock(message=AsyncMock(content="Test response"))]
            mock_instance.chat.completions.create.return_value = test_response

            await send_openai_request(messages=[{"role": "user", "content": "Hello"}])

            called_with = mock_instance.chat.completions.create.call_args[1]
            assert called_with["temperature"] == 1
            assert called_with["model"] == "gpt-test-model"