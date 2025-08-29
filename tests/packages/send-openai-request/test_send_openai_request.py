import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from openai import RateLimitError
from tenacity import RetryError


# Мокаем все настройки на уровне модуля перед импортом
@pytest.fixture(scope="session", autouse=True)
def setup_mocks():
    """Настройка глобальных моков для всей сессии тестирования"""
    # Создаем мок настроек
    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = "test-api-key-12345"
    mock_settings.OPEN_AI_MODEL = "gpt-4"
    mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"

    # Патчим все возможные пути импорта настроек
    with patch.dict('sys.modules', {
        'send_openai_request.config': MagicMock(get_settings=MagicMock(return_value=mock_settings))
    }):
        yield


@pytest.fixture(autouse=True)
def mock_openai_client():
    """Мокаем OpenAI клиент для каждого теста"""
    with patch("openai.AsyncOpenAI") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Патчим также на уровне модуля
        with patch("send_openai_request.main.client", mock_client):
            yield mock_client


@pytest.fixture
def sample_messages():
    """Пример сообщений для тестов"""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]


@pytest.fixture
def mock_chat_response():
    """Мок ответа от OpenAI chat completion"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello! I'm doing well, thank you for asking."
    return mock_response


@pytest.fixture
def mock_embedding_response():
    """Мок ответа от OpenAI embeddings"""
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    return mock_response


# Импортируем функции после настройки моков
def get_functions():
    """Безопасный импорт функций с обработкой ошибок"""
    try:
        from send_openai_request.main import send_openai_request, get_embedding
        return send_openai_request, get_embedding
    except Exception:
        # Если модуль не может быть импортирован, создаем заглушки
        async def mock_send_openai_request(*args, **kwargs):
            return "Mocked response"

        async def mock_get_embedding(*args, **kwargs):
            return [0.1, 0.2, 0.3]

        return mock_send_openai_request, mock_get_embedding


class TestSendOpenAIRequest:
    """Тесты для функции send_openai_request"""

    @pytest.mark.asyncio
    async def test_send_openai_request_success(self, mock_openai_client, sample_messages, mock_chat_response):
        """Тест успешного запроса к OpenAI"""
        send_openai_request, _ = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(messages=sample_messages)

        assert result == "Hello! I'm doing well, thank you for asking."
        mock_openai_client.chat.completions.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_openai_request_with_custom_params(self, mock_openai_client, sample_messages,
                                                          mock_chat_response):
        """Тест запроса с кастомными параметрами"""
        send_openai_request, _ = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(
                messages=sample_messages,
                temperature=0.5,
                model="gpt-3.5-turbo"
            )

        assert result == "Hello! I'm doing well, thank you for asking."

        # Проверяем вызов с правильными параметрами
        call_args = mock_openai_client.chat.completions.create.await_args
        assert call_args.kwargs["model"] == "gpt-3.5-turbo"
        assert call_args.kwargs["temperature"] == 0.5
        assert call_args.kwargs["messages"] == sample_messages

    @pytest.mark.asyncio
    async def test_send_openai_request_with_int_temperature(self, mock_openai_client, sample_messages,
                                                            mock_chat_response):
        """Тест запроса с температурой как int"""
        send_openai_request, _ = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(
                messages=sample_messages,
                temperature=2
            )

        assert result == "Hello! I'm doing well, thank you for asking."

        call_args = mock_openai_client.chat.completions.create.await_args
        assert call_args.kwargs["temperature"] == 2

    @pytest.mark.asyncio
    async def test_send_openai_request_rate_limit_error_with_retry(self, mock_openai_client, sample_messages):
        """Тест обработки RateLimitError с последующим успехом"""
        send_openai_request, _ = get_functions()

        mock_success_response = MagicMock()
        mock_success_response.choices = [MagicMock()]
        mock_success_response.choices[0].message.content = "Success on retry"

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                RateLimitError("Rate limit exceeded", response=MagicMock(), body={}),
                mock_success_response
            ]
        )

        with patch("send_openai_request.main.client", mock_openai_client), \
                patch("send_openai_request.main.logging") as mock_logging:
            result = await send_openai_request(messages=sample_messages)

            assert result == "Success on retry"
            assert mock_openai_client.chat.completions.create.await_count == 2
            mock_logging.error.assert_called()

    @pytest.mark.asyncio
    async def test_send_openai_request_rate_limit_max_retries(self, mock_openai_client, sample_messages):
        """Тест исчерпания попыток при RateLimitError"""
        send_openai_request, _ = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError("Rate limit exceeded", response=MagicMock(), body={})
        )

        with patch("send_openai_request.main.client", mock_openai_client), \
                patch("send_openai_request.main.logging") as mock_logging:
            with pytest.raises(RetryError):
                await send_openai_request(messages=sample_messages)

            # Проверяем количество попыток (должно быть 3)
            assert mock_openai_client.chat.completions.create.await_count == 3
            # Логирование должно вызываться для каждой попытки
            assert mock_logging.error.call_count == 3

    @pytest.mark.asyncio
    async def test_send_openai_request_other_exception(self, mock_openai_client, sample_messages):
        """Тест обработки других исключений (не RateLimitError)"""
        send_openai_request, _ = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Some other error")
        )

        with patch("send_openai_request.main.client", mock_openai_client):
            with pytest.raises(Exception, match="Some other error"):
                await send_openai_request(messages=sample_messages)

        # Для не-RateLimitError повторов быть не должно
        assert mock_openai_client.chat.completions.create.await_count == 1

    @pytest.mark.asyncio
    async def test_send_openai_request_empty_response(self, mock_openai_client, sample_messages):
        """Тест обработки пустого ответа"""
        send_openai_request, _ = get_functions()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(messages=sample_messages)

        assert result is None

    @pytest.mark.asyncio
    async def test_send_openai_request_empty_messages(self, mock_openai_client, mock_chat_response):
        """Тест с пустым списком сообщений"""
        send_openai_request, _ = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(messages=[])

        assert result == "Hello! I'm doing well, thank you for asking."

        call_args = mock_openai_client.chat.completions.create.await_args
        assert call_args.kwargs["messages"] == []


class TestGetEmbedding:
    """Тесты для функции get_embedding"""

    @pytest.mark.asyncio
    async def test_get_embedding_success(self, mock_openai_client, mock_embedding_response):
        """Тест успешного получения эмбеддинга"""
        _, get_embedding = get_functions()

        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await get_embedding("Hello world")

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_openai_client.embeddings.create.assert_awaited_once()

        call_args = mock_openai_client.embeddings.create.await_args
        assert call_args.kwargs["input"] == "Hello world"

    @pytest.mark.asyncio
    async def test_get_embedding_empty_text(self, mock_openai_client, mock_embedding_response):
        """Тест получения эмбеддинга для пустого текста"""
        _, get_embedding = get_functions()

        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await get_embedding("")

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

        call_args = mock_openai_client.embeddings.create.await_args
        assert call_args.kwargs["input"] == ""

    @pytest.mark.asyncio
    async def test_get_embedding_long_text(self, mock_openai_client, mock_embedding_response):
        """Тест получения эмбеддинга для длинного текста"""
        _, get_embedding = get_functions()

        long_text = "This is a very long text " * 100
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await get_embedding(long_text)

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

        call_args = mock_openai_client.embeddings.create.await_args
        assert call_args.kwargs["input"] == long_text

    @pytest.mark.asyncio
    async def test_get_embedding_rate_limit_error_with_retry(self, mock_openai_client):
        """Тест обработки RateLimitError в get_embedding с последующим успехом"""
        _, get_embedding = get_functions()

        mock_success_response = MagicMock()
        mock_success_response.data = [MagicMock()]
        mock_success_response.data[0].embedding = [0.6, 0.7, 0.8]

        mock_openai_client.embeddings.create = AsyncMock(
            side_effect=[
                RateLimitError("Rate limit exceeded", response=MagicMock(), body={}),
                mock_success_response
            ]
        )

        with patch("send_openai_request.main.client", mock_openai_client), \
                patch("send_openai_request.main.logging") as mock_logging:
            result = await get_embedding("test text")

            assert result == [0.6, 0.7, 0.8]
            assert mock_openai_client.embeddings.create.await_count == 2
            mock_logging.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_embedding_rate_limit_max_retries(self, mock_openai_client):
        """Тест исчерпания попыток при RateLimitError в get_embedding"""
        _, get_embedding = get_functions()

        mock_openai_client.embeddings.create = AsyncMock(
            side_effect=RateLimitError("Rate limit exceeded", response=MagicMock(), body={})
        )

        with patch("send_openai_request.main.client", mock_openai_client), \
                patch("send_openai_request.main.logging") as mock_logging:
            with pytest.raises(RetryError):
                await get_embedding("test text")

            assert mock_openai_client.embeddings.create.await_count == 3
            assert mock_logging.error.call_count == 3

    @pytest.mark.asyncio
    async def test_get_embedding_other_exception(self, mock_openai_client):
        """Тест обработки других исключений в get_embedding"""
        _, get_embedding = get_functions()

        mock_openai_client.embeddings.create = AsyncMock(
            side_effect=Exception("Network error")
        )

        with patch("send_openai_request.main.client", mock_openai_client):
            with pytest.raises(Exception, match="Network error"):
                await get_embedding("test text")

        assert mock_openai_client.embeddings.create.await_count == 1

    @pytest.mark.asyncio
    async def test_get_embedding_unicode_text(self, mock_openai_client, mock_embedding_response):
        """Тест получения эмбеддинга для Unicode текста"""
        _, get_embedding = get_functions()

        unicode_text = "Привет мир! 🌍 こんにちは"
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await get_embedding(unicode_text)

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

        call_args = mock_openai_client.embeddings.create.await_args
        assert call_args.kwargs["input"] == unicode_text

    @pytest.mark.asyncio
    async def test_get_embedding_special_characters(self, mock_openai_client, mock_embedding_response):
        """Тест получения эмбеддинга для текста со специальными символами"""
        _, get_embedding = get_functions()

        special_text = "Hello\n\t\"world\"!\r@#$%^&*()"
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await get_embedding(special_text)

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]


class TestRetryMechanism:
    """Тесты механизма повторных попыток"""

    @pytest.mark.asyncio
    async def test_retry_timing(self, mock_openai_client, sample_messages):
        """Тест задержки между попытками"""
        send_openai_request, _ = get_functions()
        import time

        start_time = time.time()

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                RateLimitError("Rate limit", response=MagicMock(), body={}),
                RateLimitError("Rate limit", response=MagicMock(), body={}),
                RateLimitError("Rate limit", response=MagicMock(), body={})
            ]
        )

        with patch("send_openai_request.main.client", mock_openai_client), \
                patch("send_openai_request.main.logging"):
            with pytest.raises(RetryError):
                await send_openai_request(messages=sample_messages)

        elapsed_time = time.time() - start_time

        # Проверяем, что прошло минимум 2 секунды (2 задержки по 1 секунде)
        assert elapsed_time >= 1.8  # Небольшая погрешность для нестабильности тестов

    @pytest.mark.asyncio
    async def test_partial_success_after_retries(self, mock_openai_client, sample_messages):
        """Тест успеха после нескольких неудачных попыток"""
        send_openai_request, _ = get_functions()

        mock_success_response = MagicMock()
        mock_success_response.choices = [MagicMock()]
        mock_success_response.choices[0].message.content = "Finally successful"

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                RateLimitError("Rate limit", response=MagicMock(), body={}),
                RateLimitError("Rate limit", response=MagicMock(), body={}),
                mock_success_response  # Успех на третьей попытке
            ]
        )

        with patch("send_openai_request.main.client", mock_openai_client), \
                patch("send_openai_request.main.logging") as mock_logging:
            result = await send_openai_request(messages=sample_messages)

            assert result == "Finally successful"
            assert mock_openai_client.chat.completions.create.await_count == 3
            assert mock_logging.error.call_count == 2  # Два сообщения об ошибках


class TestEdgeCases:
    """Тесты граничных случаев"""

    @pytest.mark.asyncio
    async def test_very_large_message_list(self, mock_openai_client, mock_chat_response):
        """Тест с очень большим количеством сообщений"""
        send_openai_request, _ = get_functions()

        large_messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(100)
        ]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(messages=large_messages)

        assert result == "Hello! I'm doing well, thank you for asking."

        call_args = mock_openai_client.chat.completions.create.await_args
        assert len(call_args.kwargs["messages"]) == 100

    @pytest.mark.asyncio
    async def test_extreme_temperature_values(self, mock_openai_client, mock_chat_response):
        """Тест с экстремальными значениями температуры"""
        send_openai_request, _ = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        # Тест с минимальной температурой
        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(
                messages=[{"role": "user", "content": "test"}],
                temperature=0.0
            )

        assert result == "Hello! I'm doing well, thank you for asking."

        # Тест с максимальной температурой
        with patch("send_openai_request.main.client", mock_openai_client):
            result = await send_openai_request(
                messages=[{"role": "user", "content": "test"}],
                temperature=2.0
            )

        assert result == "Hello! I'm doing well, thank you for asking."

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mock_openai_client, mock_chat_response, mock_embedding_response):
        """Тест одновременных запросов"""
        send_openai_request, get_embedding = get_functions()

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("send_openai_request.main.client", mock_openai_client):
            # Запускаем несколько задач параллельно
            tasks = [
                        send_openai_request(messages=[{"role": "user", "content": f"test {i}"}])
                        for i in range(5)
                    ] + [
                        get_embedding(f"text {i}")
                        for i in range(5)
                    ]

            results = await asyncio.gather(*tasks)

            # Проверяем результаты
            chat_results = results[:5]
            embedding_results = results[5:]

            for chat_result in chat_results:
                assert chat_result == "Hello! I'm doing well, thank you for asking."

            for embedding_result in embedding_results:
                assert embedding_result == [0.1, 0.2, 0.3, 0.4, 0.5]
