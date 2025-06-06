import pytest
from unittest.mock import AsyncMock, patch
from ai_tools.main import check_answer_is_needed, create_comment_to_message
import logging
from loguru import logger

import sys
import os


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPEN_AI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "test-embedding-model")



@pytest.fixture(autouse=True)
def setup_logging():
    logger.remove()
    logger.add(lambda msg: logging.info(msg), format="{message}")


@pytest.mark.asyncio
async def test_check_answer_is_needed_true():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = "true"
        result = await check_answer_is_needed("test message", "Twitter")
        assert result is True
        mock_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_answer_is_needed_false():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = "false"
        result = await check_answer_is_needed("test message", "Twitter")
        assert result is False


@pytest.mark.asyncio
async def test_check_answer_is_needed_case_insensitive():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = "tRuE"
        result = await check_answer_is_needed("test message", "Twitter")
        assert result is True


@pytest.mark.asyncio
async def test_create_comment_to_message_success():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        test_response = "Test response"
        mock_request.return_value = test_response
        result = await create_comment_to_message("test message", "Twitter")
        assert result == test_response
        mock_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_comment_to_message_empty_input():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = ""
        result = await create_comment_to_message("", "Twitter")
        assert result == ""


@pytest.mark.asyncio
async def test_check_answer_is_needed_with_exception():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = Exception("API error")
        result = await check_answer_is_needed("test message", "Twitter")
        assert result is False


@pytest.mark.asyncio
async def test_create_comment_to_message_with_exception():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = Exception("API error")
        result = await create_comment_to_message("test message", "Twitter")
        assert result == ""


@pytest.mark.parametrize("social_type", ["Twitter", "Facebook", "Instagram", "LinkedIn"])
@pytest.mark.asyncio
async def test_different_social_types(social_type):
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = "true"
        result = await check_answer_is_needed("test message", social_type)
        assert result is True


@pytest.mark.asyncio
async def test_temperature_settings():
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = "true"
        await check_answer_is_needed("test", "Twitter")
        _, kwargs = mock_request.call_args
        assert kwargs.get('temperature') == 1.1

        mock_request.reset_mock()
        mock_request.return_value = "response"
        await create_comment_to_message("test", "Twitter")
        _, kwargs = mock_request.call_args
        assert kwargs.get('temperature') == 1.0


def test_logging_output(caplog):
    with patch('send_openai_request.main.send_openai_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = "Test response"

        async def test_fn():
            return await create_comment_to_message("test", "Twitter")

        assert "Created answer on comment" in caplog.text
