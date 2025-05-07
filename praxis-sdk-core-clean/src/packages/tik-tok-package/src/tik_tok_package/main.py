import os
import time
import pickle
from typing import Optional
import undetected_chromedriver as uc
from tiktok_captcha_solver import SeleniumSolver

from tik_tok_package.log import log
from tik_tok_package.pages.login_page import LoginPage
from tik_tok_package.pages.scroll_page import ScrollPage
from tik_tok_package.pages.upload_page import UploadPage
from tik_tok_package.pages.user_profile_page import UserProfilePage
from tik_tok_package.pages.user_video_page import UserVideoPage


class TikTokBot:
    def __init__(self, api_key: str, session_name: str = "tiktok_session", headless: bool = True,
                 browser_executable_path: Optional[str] = None):
        self.session_name = session_name
        self.cookies_path = f"sessions/{session_name}_cookies.pkl"
        self.driver = uc.Chrome(headless=headless, use_subprocess=False, version_main=135,
                                browser_executable_path=browser_executable_path)
        self.start_time = time.time()
        self.sadcaptcha = SeleniumSolver(
            self.driver,
            api_key,
            mouse_step_size=1,
            mouse_step_delay_ms=10
        )

        self.login_page = LoginPage(self.driver, self.sadcaptcha)
        self.scroll_page = ScrollPage(self.driver, self.sadcaptcha)
        self.upload_page = UploadPage(self.driver, self.sadcaptcha)
        self.user_video_page = UserVideoPage(self.driver, self.sadcaptcha)
        self.user_profile_page = UserProfilePage(self.driver, self.sadcaptcha)

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
        """
        Check if the user is logged in by checking the current URL.
        """
        self.driver.get("https://www.tiktok.com/upload")
        return "login" not in self.driver.current_url.lower()

    def login(self, username: str, password: str):
        """
        Login to TikTok using the provided username and password.
        """
        if not self.is_logged_in():
            self.login_page.open_page()
            self.login_page.accept_cookies()
            self.login_page.login(username, password)
            self.scroll_page.wait_for_open_scroll_page()
            self._save_cookies()
            time.sleep(1)

    def upload_video(self, description: str, video_path: str):
        """
        Upload a video to TikTok with the provided description and video path.
        """
        self.upload_page.open_page()
        self.scroll_page.accept_policy()
        self.upload_page.open_page()
        self.upload_page.upload_video(video_path)
        self.upload_page.add_description(description)
        self.upload_page.toggle_autor_rules()
        self.upload_page.click_post_button()
        time.sleep(10)

    def like_video(self, video_url: Optional[str] = None, video_id: Optional[str] = None,
                   username: Optional[str] = None):
        """
        Like a video on TikTok using the provided video URL or video ID.

        If 'video_url' is not provided, both 'username' and 'video_id' must be provided.
        """
        if video_url is None:
            if username is None or video_id is None:
                log.info(f"[!] If 'video_url' is not provided, both 'username' and 'video_id' must be provided. ")
                raise ValueError("If 'video_url' is not provided, both 'username' and 'video_id' must be provided.")
            if username[0] != "@":
                log.info(f"[!] Username should start with '@'. Adding '@' to {username}")
                username = "@" + username
            video_url = f"https://www.tiktok.com/{username}/video/{video_id}"
        self.user_video_page.open_page(video_url)
        self.user_video_page.like_video()
        self.user_video_page.verify_captcha()

    def follow_user(self, user_url: Optional[str] = None, username: Optional[str] = None, follow_user: bool = True):
        """
        Follow a user on TikTok using the provided user URL or username.

        If 'user_url' is not provided, 'username' must be provided.
        """
        if user_url is None:
            if username is None:
                log.info(f"[!] If 'user_url' is not provided, 'username' must be provided. ")
                raise ValueError("If 'user_url' is not provided, 'username' must be provided.")
            if username[0] != "@":
                log.info(f"[!] Username should start with '@'. Adding '@' to {username}")
                username = "@" + username
            user_url = f"https://www.tiktok.com/{username}"

        self.user_profile_page.open_page(user_url)
        self.user_profile_page.follow_user(follow=follow_user)

    def unfollow_user(self, user_url: Optional[str] = None, username: Optional[str] = None):
        """
        Unfollow a user on TikTok using the provided user URL or username.
        """
        self.follow_user(user_url=user_url, username=username, follow_user=False)

    def comment_on_video(self, video_url: str, comment: str):
        """
        Leave a comment on a TikTok video using the provided video URL and comment text.

        WARNING: This method works only when session live more than 5 minutes.
        """
        # if self.start_time + 300 > time.time():
        #     log.info(f"[!] Session is too young. Please wait more than 5 minutes.")
        #     raise ValueError("Session is too young. Please wait more than 5 minutes.")
        self.user_video_page.open_page(video_url)
        self.user_video_page.open_comment_page()
        self.user_video_page.left_comment(comment)
        self.user_video_page.publish_comment()

    def quit(self):
        """
        Quit the TikTok bot and close the browser.
        """
        self.driver.close()
