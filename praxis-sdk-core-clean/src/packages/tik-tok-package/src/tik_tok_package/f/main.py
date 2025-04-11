from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bot import TikTokBot


def run_bot(username: str, password: str, video_path: str):
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    bot = TikTokBot(driver)
    bot.login_and_upload(username, password, video_path)

    driver.quit()

if __name__ == "__main__":
    username = "valebtinbest@gmail.com"
    password = "|yR2mZtbc;hjS/T"
    video_path = "ex.mp4"

    run_bot(username, password, video_path)
