import logging

from infrastructure.configs.constants import PROJECT_DESCRIPTION
from infrastructure.prompts.comments import check_answer_is_needed_prompt, create_comment_to_message_prompt
from services.ai_connectors.openai_client import send_openai_request

from services.shared.models.social_media import SocialMediaType

logger = logging.getLogger(__name__)


async def check_answer_is_needed(message: str, social_media_type: SocialMediaType) -> bool:
    prompt = check_answer_is_needed_prompt.format(social_media_type)
    messages = [
        {
            "role": "system",
            "content": prompt,
        },
        {
            "role": "user",
            "content": message,
        },
    ]
    result = await send_openai_request(messages=messages, temperature=1.1)
    # logging.info(f"Check answer is needed: {result=} {messages=} {social_media_type=}")
    return "true" in result.lower()


async def create_comment_to_message(
        message: str,
        social_media_type: SocialMediaType,
) -> str:
    prompt = create_comment_to_message_prompt.format(social_media_type, PROJECT_DESCRIPTION)
    messages = [
        {
            "role": "system",
            "content": prompt,
        },
        {
            "role": "user",
            "content": f"<conversation>{message}<conversation>",
        },
    ]
    result = await send_openai_request(messages=messages, temperature=1.0)

    logging.info(f"Created answer on comment: {result=} {messages=}")
    return result
