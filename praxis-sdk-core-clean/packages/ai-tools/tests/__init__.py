from unittest.mock import AsyncMock, patch

import pytest
from ai_tools.main import check_answer_is_needed, create_comment_to_message
from infra_configs.constants import PROJECT_DESCRIPTION
from loguru import logger
from social_media_schemas.main import SocialMediaType


@pytest.fixture
def mock_settings():
    class MockSettings:
        check_answer_is_needed_prompt = "Check if {0} comment needs a reply: {1}"
        create_comment_to_message_prompt = (
            "Create a reply for {0} comment about {1}: {2}"
        )

    return MockSettings()


@pytest.mark.asyncio
async def test_check_answer_is_needed_true(mocker):
    mocker.patch(
        "send_openai_request.check_answer_is_needed_prompt",
        "Check if {0} comment needs a reply",
    )
    mocker.patch(
        "send_openai_request.send_openai_request", AsyncMock(return_value="True")
    )
    mocker.patch.object(logger, "info")

    result = await check_answer_is_needed("Test message", SocialMediaType.TWITTER)
    assert result is True
    send_openai_request.assert_called_once_with(
        messages=[
            {"role": "system", "content": "Check if TWITTER comment needs a reply"},
            {"role": "user", "content": "Test message"},
        ],
        temperature=1.1,
    )
    logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_check_answer_is_needed_false(mocker):
    mocker.patch(
        "send_openai_request.check_answer_is_needed_prompt",
        "Check if {0} comment needs a reply",
    )
    mocker.patch(
        "send_openai_request.send_openai_request", AsyncMock(return_value="False")
    )
    mocker.patch.object(logger, "info")

    result = await check_answer_is_needed("Test message", SocialMediaType.TWITTER)
    assert result is False
    send_openai_request.assert_called_once_with(
        messages=[
            {"role": "system", "content": "Check if TWITTER comment needs a reply"},
            {"role": "user", "content": "Test message"},
        ],
        temperature=1.1,
    )
    logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_create_comment_to_message(mocker):
    mocker.patch(
        "send_openai_request.create_comment_to_message_prompt",
        "Create a reply for {0} comment about {1}",
    )
    mocker.patch(
        "send_openai_request.send_openai_request",
        AsyncMock(return_value="Generated reply"),
    )
    mocker.patch.object(logger, "info")

    result = await create_comment_to_message("Test message", SocialMediaType.TWITTER)
    assert result == "Generated reply"
    send_openai_request.assert_called_once_with(
        messages=[
            {
                "role": "system",
                "content": f"Create a reply for TWITTER comment about {PROJECT_DESCRIPTION}",
            },
            {"role": "user", "content": "<conversation>Test message<conversation>"},
        ],
        temperature=1.0,
    )
    logger.info.assert_called_once_with(
        "Created answer on comment: result='Generated reply' messages=[{'role': 'system', 'content': 'Create a reply for TWITTER comment about N/A'}, {'role': 'user', 'content': '<conversation>Test message<conversation>'}]"
    )
