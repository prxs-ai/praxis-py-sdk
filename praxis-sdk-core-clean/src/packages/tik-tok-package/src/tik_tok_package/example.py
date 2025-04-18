
from main import TikTokBot


def run_bot(username: str, password: str, api_key: str):
    bot = TikTokBot(api_key=api_key)
    bot.login(username, password)
    # bot.upload_video("example", '/example/path/to/video.mp4')
    # bot.like_video(video_url="https://www.tiktok.com/@seveenteenhats/video/7494472620843207953?q=car&t=1744970971108")
    # bot.follow_user(user_url="https://www.tiktok.com/@denisdzapshba005")
    bot.comment_on_video(
        video_url="https://www.tiktok.com/@mini_lolik/video/7491613049669897527",
        comment="Hello world!"
    )
    bot.quit()


if __name__ == "__main__":
    # Example usage
    username = ""
    password = ""
    api_key = ""
    run_bot(username, password, api_key )
