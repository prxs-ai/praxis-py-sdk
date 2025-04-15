import os
import time
import pickle

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from tiktok_captcha_solver import SeleniumSolver

from pages.login_page import LoginPage
from pages.scroll_page import ScrollPage
from pages.upload_page import UploadPage


class TikTokBot:
    def __init__(self, api_key: str, session_name: str = "tiktok_session", headless: bool = False):
        self.session_name = session_name
        self.cookies_path = f"sessions/{session_name}_cookies.pkl"

        # Инициализация драйвера
        options = Options()
        options.add_argument("--start-maximized")
        if headless:
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)

        self.sadcaptcha = SeleniumSolver(
            self.driver,
            api_key,
            mouse_step_size=1,
            mouse_step_delay_ms=10
        )

        self.login_page = LoginPage(self.driver)
        self.scroll_page = ScrollPage(self.driver)
        self.upload_page = UploadPage(self.driver)

        # Попробовать загрузить куки
        self.driver.get("https://www.tiktok.com/")
        self._load_cookies()
        self.driver.get("https://www.tiktok.com/")  # обновим после загрузки

    def _load_cookies(self):
        if os.path.exists(self.cookies_path):
            with open(self.cookies_path, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"[!] Ошибка загрузки cookie: {e}")

    def _save_cookies(self):
        cookies = self.driver.get_cookies()
        os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)
        with open(self.cookies_path, "wb") as f:
            pickle.dump(cookies, f)

    def is_logged_in(self) -> bool:
        self.driver.get("https://www.tiktok.com/upload")
        return "login" not in self.driver.current_url.lower()

    def login(self, username: str, password: str):
        if not self.is_logged_in():
            self.login_page.open_page()
            self.login_page.accept_cookies()
            self.login_page.login(username, password)
            self.sadcaptcha.solve_captcha_if_present()
            self.scroll_page.wait_for_open_scroll_page()
            self._save_cookies()
            time.sleep(1)
        else:
            self.upload_page.open_page()

    def upload_video(self, description: str, video_path: str):
        self.scroll_page.accept_policy()
        self.upload_page.open_page()
        self.upload_page.upload_video(video_path)
        self.upload_page.add_description(description)
        self.upload_page.toggle_autor_rules()
        self.upload_page.click_post_button()
        time.sleep(10)

    def quit(self):
        self.driver.quit()
