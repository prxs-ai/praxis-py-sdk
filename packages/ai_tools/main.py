from loguru import logger


async def check_answer_is_needed(message: str, social_media_type) -> bool:
    """Check if a message requires a response based on social media type and content.

    Args:
        message: The message text to evaluate
        social_media_type: Type of social media platform

    Returns:
        bool: True if response is needed, False otherwise
    """
    from infra_configs.constants import PROJECT_DESCRIPTION
    from infra_configs.prompt import check_answer_is_needed_prompt, create_comment_to_message_prompt
    from send_openai_request.main import send_openai_request

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
    logger.info(f"Check answer is needed: {result=} {messages=} {social_media_type=}")
    return "true" in result.lower()


async def create_comment_to_message(
        message: str,
        social_media_type,
) -> str:
    """Generate a comment response for a given message and social media type.

    Args:
        message: The original message text
        social_media_type: Type of social media platform

    Returns:
        str: Generated response or None if failed
    """
    from infra_configs.constants import PROJECT_DESCRIPTION
    from infra_configs.prompt import check_answer_is_needed_prompt, create_comment_to_message_prompt
    from send_openai_request.main import send_openai_request

    prompt = create_comment_to_message_prompt.format(social_media_type, PROJECT_DESCRIPTION)
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
    result = await send_openai_request(messages=messages, temperature=1.0)

    logger.info(f"Created answer on comment: {result=} {messages=}")
    return result
