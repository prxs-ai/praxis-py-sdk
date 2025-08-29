check_answer_is_needed_prompt = '''Analyze the following tweet and determine if it warrants a response. Consider factors such as direct questions, mentions, requests for help, controversial statements, or engagement-seeking content. Provide a brief explanation for your decision.

Tweet: {social_media_type}

Should this tweet be replied to? (Yes/No)
Reasoning: [Your explanation]'''

create_comment_to_message_prompt = """Generate a professional, engaging, and concise reply to the following tweet, maintaining the original context while representing an AI agent project. The tone should be helpful, friendly, and aligned with promoting AI innovation. If the tweet is a question, provide a clear answer; if it’s a discussion, add value with insights or examples. Avoid overly promotional language unless directly relevant.

Tweet to reply to: {social_media_type}

Guidelines:

Keep it under 280 characters.

Use emojis sparingly (1 max) if appropriate.

If unsure, ask clarifying questions instead of guessing.

Reference the project subtly (e.g., ‘In our work with AI agents…’). Project description - {PROJECT_DESCRIPTION}.
"""
