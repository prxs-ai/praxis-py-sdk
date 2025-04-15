
from main import TikTokBot


def run_bot(username: str, password: str, video_path: str, api_key: str, description: str):
    bot = TikTokBot(api_key=api_key)
    bot.login(username, password)
    bot.upload_video(description, video_path)
    bot.quit()


if __name__ == "__main__":
    # Example usage
    username = ""
    password = ""
    video_path = ""
    api_key = ""
    description = "Тестовое видео"
    run_bot(username, password, video_path, api_key, description)
