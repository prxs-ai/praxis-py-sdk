from loguru import logger


async def check_answer_is_needed(message: str, social_media_type) -> bool:
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
            "content": f"<conversation>{message}<conversation>",
        },
    ]
    result = await send_openai_request(messages=messages, temperature=1.0)

    logger.info(f"Created answer on comment: {result=} {messages=}")
    return result
