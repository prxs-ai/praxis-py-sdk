import time

from pages.login_page import LoginPage
from pages.scroll_page import ScrollPage
from pages.upload_page import UploadPage


class TikTokBot:
    def __init__(self, driver):
        self.driver = driver
        self.login_page = LoginPage(driver)
        self.scroll_page = ScrollPage(driver)
        self.upload_page = UploadPage(driver)

    def login_and_upload(self, username: str, password: str, video_path: str):
        self.login_page.open_page()
        time.sleep(5)
        self.login_page.accept_cookies()
        self.login_page.login(username, password)
        time.sleep(10)  # TODO: капча
        self.scroll_page.accept_policy()
        self.upload_page.open_page()

        self.upload_page.upload_video(video_path)
        self.upload_page.add_description("Тестовое описание")
        self.upload_page.toggle_autor_rules()
        self.upload_page.click_post_button()
        time.sleep(123)
