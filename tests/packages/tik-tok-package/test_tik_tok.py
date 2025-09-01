import pytest
from unittest.mock import MagicMock, patch
from selenium import webdriver
from tik_tok_package.commands.captcha_solver import handle_captcha
from tik_tok_package.pages.login_page import LoginPage
from tik_tok_package.pages.scroll_page import ScrollPage
from tik_tok_package.pages.upload_page import UploadPage
from tik_tok_package.pages.user_profile_page import UserProfilePage
from tik_tok_package.pages.user_video_page import UserVideoPage
from tik_tok_package.main import TikTokBot
import os
import pickle
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By


# Фикстуры
@pytest.fixture
def mock_driver():
    driver = MagicMock(spec=webdriver.Chrome)
    driver.get = MagicMock()
    driver.find_element = MagicMock()
    driver.current_url = "https://www.tiktok.com/"
    driver.get_cookies = MagicMock(return_value=[{"name": "test_cookie", "value": "test"}])
    driver.add_cookie = MagicMock()
    driver.execute_script = MagicMock()
    yield driver


@pytest.fixture
def mock_sadcaptcha():
    sadcaptcha = MagicMock()
    sadcaptcha.solve_captcha_if_present = MagicMock()
    yield sadcaptcha


@pytest.fixture
def mock_log():
    with patch("tik_tok_package.log.log") as mock_log:
        yield mock_log


# Тесты для captcha_solver
def test_handle_captcha_with_sadcaptcha(mock_driver, mock_sadcaptcha, mock_log):
    class TestClass:
        def __init__(self):
            self.sadcaptcha = mock_sadcaptcha

        @handle_captcha
        def test_method(self, *args, **kwargs):
            return "success"

    obj = TestClass()
    result = obj.test_method("arg1", kwarg1="value1")

    assert result == "success"
    mock_sadcaptcha.solve_captcha_if_present.assert_called_once()
    mock_log.info.assert_any_call("[TestClass] Запуск метода: test_method")
    mock_log.debug.assert_called_with("[TestClass.test_method] Аргументы: args=('arg1',), kwargs={'kwarg1': 'value1'}")
    mock_log.info.assert_any_call("[TestClass.test_method] Метод успешно завершён.")


def test_handle_captcha_with_driver_parent(mock_driver, mock_sadcaptcha, mock_log):
    class TestClass:
        def __init__(self):
            self.driver = MagicMock()
            self.driver._parent_instance = MagicMock()
            self.driver._parent_instance.sadcaptcha = mock_sadcaptcha

        @handle_captcha
        def test_method(self):
            return "success"

    obj = TestClass()
    result = obj.test_method()

    assert result == "success"
    mock_sadcaptcha.solve_captcha_if_present.assert_called_once()
    mock_log.warning.assert_not_called()


def test_handle_captcha_no_sadcaptcha(mock_driver, mock_log):
    class TestClass:
        def __init__(self):
            self.driver = MagicMock()
            self.driver._parent_instance = None

        @handle_captcha
        def test_method(self):
            return "success"

    obj = TestClass()
    result = obj.test_method()

    assert result == "success"
    mock_log.warning.assert_called_with("[TestClass.test_method] Атрибут _parent_instance отсутствует у driver.")


def test_handle_captcha_method_exception(mock_sadcaptcha, mock_log):
    class TestClass:
        def __init__(self):
            self.sadcaptcha = mock_sadcaptcha

        @handle_captcha
        def test_method(self):
            raise ValueError("Test error")

    obj = TestClass()
    with pytest.raises(ValueError, match="Test error"):
        obj.test_method()
    mock_log.exception.assert_called_with("[TestClass.test_method] Ошибка при выполнении метода: Test error")


# Тесты для login_page
def test_login_page_init(mock_driver, mock_sadcaptcha):
    page = LoginPage(mock_driver, mock_sadcaptcha)
    assert page.driver == mock_driver
    assert page.sadcaptcha == mock_sadcaptcha


def test_open_page(mock_driver, mock_sadcaptcha):
    page = LoginPage(mock_driver, mock_sadcaptcha)
    page.open_page()
    mock_driver.get.assert_called_with("https://www.tiktok.com/login/phone-or-email/email")


def test_accept_cookies(mock_driver, mock_sadcaptcha, mock_log):
    shadow_host = MagicMock()
    shadow_root = MagicMock()
    button = MagicMock()
    mock_driver.find_element.return_value = shadow_host
    shadow_host.shadow_root = shadow_root
    shadow_root.find_element.return_value = button

    page = LoginPage(mock_driver, mock_sadcaptcha)
    page.accept_cookies()

    mock_log.info.assert_any_call("Waiting for the cookie banner to load...")
    mock_log.info.assert_any_call("Cookies accepted")
    button.click.assert_called_once()


def test_save_cookies(mock_driver, mock_sadcaptcha, tmp_path, mock_log):
    filename = tmp_path / "cookies.pkl"
    page = LoginPage(mock_driver, mock_sadcaptcha)
    page.save_cookies()

    mock_log.info.assert_called_with(f"Saving cookies into {filename}")
    with open(filename, "rb") as f:
        saved_cookies = pickle.load(f)
    assert saved_cookies == mock_driver.get_cookies.return_value


def test_try_to_load_cookies_success(mock_driver, mock_sadcaptcha, tmp_path, mock_log):
    filename = tmp_path / "cookies.pkl"
    cookies = [{"name": "test_cookie", "value": "test"}]
    with open(filename, "wb") as f:
        pickle.dump(cookies, f)

    page = LoginPage(mock_driver, mock_sadcaptcha)
    result = page.try_to_load_cookies()

    assert result is True
    mock_driver.add_cookie.assert_called_with(cookies[0])
    mock_log.info.assert_called_with("Cookies loaded successfully")


def test_try_to_load_cookies_file_not_found(mock_driver, mock_sadcaptcha, mock_log):
    page = LoginPage(mock_driver, mock_sadcaptcha)
    result = page.try_to_load_cookies()

    assert result is False
    mock_log.error.assert_called_with("File cookies.pkl not found. Cookies not loaded.")


# Тесты для scroll_page
def test_scroll_page_init(mock_driver, mock_sadcaptcha):
    page = ScrollPage(mock_driver, mock_sadcaptcha)
    assert page.driver == mock_driver
    assert page.sadcaptcha == mock_sadcaptcha


def test_accept_policy(mock_driver, mock_sadcaptcha, mock_log):
    button = MagicMock()
    mock_driver.find_element.return_value = button

    page = ScrollPage(mock_driver, mock_sadcaptcha)
    page.accept_policy()

    button.click.assert_called_once()
    mock_log.info.assert_any_call("Policy accepted")


def test_wait_for_open_scroll_page_timeout(mock_driver, mock_sadcaptcha, mock_log):
    mock_driver.current_url = "https://www.tiktok.com/other"
    with patch("time.time", side_effect=[0, 10, 20, 30, 60]):  # Имитация таймаута
        page = ScrollPage(mock_driver, mock_sadcaptcha)
        page.wait_for_open_scroll_page()

    mock_log.info.assert_any_call("Current URL: https://www.tiktok.com/other")


def test_wait_for_open_scroll_page_success(mock_driver, mock_sadcaptcha, mock_log):
    mock_driver.current_url = "https://www.tiktok.com/foryou"
    with patch("time.time", return_value=0):
        page = ScrollPage(mock_driver, mock_sadcaptcha)
        page.wait_for_open_scroll_page()

    mock_log.info.assert_any_call("Current URL: https://www.tiktok.com/foryou")


# Тесты для upload_page
def test_upload_page_init(mock_driver, mock_sadcaptcha):
    page = UploadPage(mock_driver, mock_sadcaptcha)
    assert page.driver == mock_driver
    assert page.sadcaptcha == mock_sadcaptcha


def test_open_page(mock_driver, mock_sadcaptcha, mock_log):
    page = UploadPage(mock_driver, mock_sadcaptcha)
    page.open_page()

    mock_driver.get.assert_called_with("https://www.tiktok.com/tiktokstudio/upload?from=webapp")
    mock_log.info.assert_called_with("Waiting for the upload page to load...")


def test_upload_video(mock_driver, mock_sadcaptcha, tmp_path, mock_log):
    video_path = tmp_path / "test_video.mp4"
    video_path.write_bytes(b"fake video")
    file_input = MagicMock()
    mock_driver.find_element.return_value = file_input

    page = UploadPage(mock_driver, mock_sadcaptcha)
    page.upload_video(str(video_path))

    file_input.send_keys.assert_called_with(os.path.abspath(str(video_path)))


def test_add_description(mock_driver, mock_sadcaptcha, mock_log):
    caption_input = MagicMock()
    mock_driver.find_element.return_value = caption_input

    page = UploadPage(mock_driver, mock_sadcaptcha)
    page.add_description("Test description")

    caption_input.send_keys.assert_any_call("Test description")


def test_toggle_autor_rules_success(mock_driver, mock_sadcaptcha, mock_log):
    autor_rule_button = MagicMock()
    success_tip = MagicMock()
    mock_driver.find_element.side_effect = [autor_rule_button, success_tip]

    page = UploadPage(mock_driver, mock_sadcaptcha)
    page.toggle_autor_rules()

    autor_rule_button.click.assert_called_once()
    mock_log.info.assert_any_call("Check autor rules exist...")


def test_toggle_autor_rules_timeout(mock_driver, mock_sadcaptcha, mock_log):
    autor_rule_button = MagicMock()
    mock_driver.find_element.side_effect = [autor_rule_button, MagicMock(side_effect=Exception("No element"))]

    page = UploadPage(mock_driver, mock_sadcaptcha)
    page.toggle_autor_rules()

    mock_log.info.assert_any_call("⚠️ Autor rules not found, check manually.")


def test_click_post_button(mock_driver, mock_sadcaptcha, mock_log):
    post_button = MagicMock()
    mock_driver.find_element.return_value = post_button

    page = UploadPage(mock_driver, mock_sadcaptcha)
    page.click_post_button()

    post_button.click.assert_called_once()
    mock_log.info.assert_any_call("Completed video upload, check manually...")


# Тесты для user_profile_page
def test_user_profile_page_init(mock_driver, mock_sadcaptcha):
    page = UserProfilePage(mock_driver, mock_sadcaptcha)
    assert page.driver == mock_driver
    assert page.sadcaptcha == mock_sadcaptcha


def test_open_page(mock_driver, mock_sadcaptcha, mock_log):
    page = UserProfilePage(mock_driver, mock_sadcaptcha)
    page.open_page("https://www.tiktok.com/@testuser")

    mock_driver.get.assert_called_with("https://www.tiktok.com/@testuser")
    mock_log.info.assert_any_call("Opening user profile page: https://www.tiktok.com/@testuser")
    mock_sadcaptcha.solve_captcha_if_present.assert_called_once()


def test_follow_user(mock_driver, mock_sadcaptcha, mock_log):
    button = MagicMock()
    mock_driver.find_element.return_value = button

    page = UserProfilePage(mock_driver, mock_sadcaptcha)
    page.follow_user(follow=True)

    button.click.assert_called_once()
    mock_log.info.assert_any_call("Waiting for the follow button to load...")


def test_verify_captcha(mock_driver, mock_sadcaptcha):
    page = UserProfilePage(mock_driver, mock_sadcaptcha)
    page.verify_captcha()
    mock_sadcaptcha.solve_captcha_if_present.assert_called_once()


# Тесты для user_video_page
def test_user_video_page_init(mock_driver, mock_sadcaptcha):
    page = UserVideoPage(mock_driver, mock_sadcaptcha)
    assert page.driver == mock_driver
    assert page.sadcaptcha == mock_sadcaptcha


def test_open_page(mock_driver, mock_sadcaptcha, mock_log):
    page = UserVideoPage(mock_driver, mock_sadcaptcha)
    page.open_page("https://www.tiktok.com/@testuser/video/123")

    mock_driver.get.assert_called_with("https://www.tiktok.com/@testuser/video/123")
    mock_log.info.assert_called_with("Opening user video page: https://www.tiktok.com/@testuser/video/123")


def test_like_video_already_liked(mock_driver, mock_sadcaptcha, mock_log):
    button = MagicMock()
    button.get_attribute.return_value = "true"
    mock_driver.find_element.return_value = button

    page = UserVideoPage(mock_driver, mock_sadcaptcha)
    page.like_video()

    mock_log.info.assert_any_call("Video already liked")
    button.click.assert_not_called()


def test_like_video_not_liked(mock_driver, mock_sadcaptcha, mock_log):
    button = MagicMock()
    button.get_attribute.return_value = "false"
    mock_driver.find_element.return_value = button

    page = UserVideoPage(mock_driver, mock_sadcaptcha)
    page.like_video()

    button.click.assert_called_once()
    mock_log.info.assert_any_call("Video liked")


def test_open_comment_page(mock_driver, mock_sadcaptcha, mock_log):
    button = MagicMock()
    mock_driver.find_element.return_value = button

    page = UserVideoPage(mock_driver, mock_sadcaptcha)
    page.open_comment_page()

    button.click.assert_called_once()
    mock_log.info.assert_called_with("Comment page opened")


def test_left_comment(mock_driver, mock_sadcaptcha, mock_log):
    comment_input = MagicMock()
    with patch("selenium.webdriver.support.wait.WebDriverWait",
               return_value=MagicMock(until=MagicMock(return_value=comment_input))):
        page = UserVideoPage(mock_driver, mock_sadcaptcha)
        page.left_comment("Test comment")

    comment_input.send_keys.assert_any_call("Test comment")
    mock_log.info.assert_called_with("Comment left")


def test_publish_comment(mock_driver, mock_sadcaptcha, mock_log):
    post_button = MagicMock()
    with patch("selenium.webdriver.support.wait.WebDriverWait",
               return_value=MagicMock(until=MagicMock(return_value=post_button))):
        page = UserVideoPage(mock_driver, mock_sadcaptcha)
        page.publish_comment()

    mock_driver.execute_script.assert_called()
    mock_log.info.assert_called_with("Comment published")


def test_slow_typing(mock_driver, mock_sadcaptcha):
    element = MagicMock()
    page = UserVideoPage(mock_driver, mock_sadcaptcha)
    with patch("time.sleep"):
        page.slow_typing(element, "test", delay=0.1)

    assert element.send_keys.call_count == 4  # По одному вызову на символ


# Тесты для main
@pytest.fixture
def mock_uc_chrome():
    with patch("tik_tok_package.main.uc.Chrome") as mock_chrome:
        driver = MagicMock()
        driver.get = MagicMock()
        driver.get_cookies = MagicMock(return_value=[{"name": "test_cookie", "value": "test"}])
        driver.add_cookie = MagicMock()
        mock_chrome.return_value = driver
        yield driver


def test_tiktok_bot_init(mock_uc_chrome, mock_sadcaptcha, tmp_path):
    bot = TikTokBot(api_key="test_api_key", session_name="test_session", headless=False)
    assert bot.session_name == "test_session"
    assert bot.cookies_path == "sessions/test_session_cookies.pkl"
    assert bot.driver == mock_uc_chrome
    assert bot.sadcaptcha == mock_sadcaptcha
    mock_uc_chrome.get.assert_called_with("https://www.tiktok.com/")


def test_load_cookies_exists(mock_uc_chrome, mock_sadcaptcha, tmp_path):
    cookies_path = tmp_path / "sessions/test_session_cookies.pkl"
    cookies_path.parent.mkdir()
    with open(cookies_path, "wb") as f:
        pickle.dump([{"name": "test_cookie", "value": "test"}], f)

    bot = TikTokBot(api_key="test_api_key", session_name="test_session", headless=False)
    bot._load_cookies()

    mock_uc_chrome.add_cookie.assert_called()


def test_is_logged_in_true(mock_uc_chrome, mock_sadcaptcha):
    mock_uc_chrome.current_url = "https://www.tiktok.com/upload"
    bot = TikTokBot(api_key="test_api_key", headless=False)
    assert bot.is_logged_in() is True


def test_is_logged_in_false(mock_uc_chrome, mock_sadcaptcha):
    mock_uc_chrome.current_url = "https://www.tiktok.com/login"
    bot = TikTokBot(api_key="test_api_key", headless=False)
    assert bot.is_logged_in() is False



def test_upload_video(mock_uc_chrome, mock_sadcaptcha, tmp_path):
    video_path = tmp_path / "test_video.mp4"
    video_path.write_bytes(b"fake video")
    bot = TikTokBot(api_key="test_api_key", headless=False)
    bot.upload_video("Test description", str(video_path))

    bot.upload_page.open_page.assert_called()
    bot.upload_page.upload_video.assert_called_with(str(video_path))
    bot.upload_page.add_description.assert_called_with("Test description")
    bot.upload_page.toggle_autor_rules.assert_called_once()
    bot.upload_page.click_post_button.assert_called_once()


def test_like_video_with_url(mock_uc_chrome, mock_sadcaptcha, mock_log):
    bot = TikTokBot(api_key="test_api_key", headless=False)
    bot.like_video(video_url="https://www.tiktok.com/@testuser/video/123")

    bot.user_video_page.open_page.assert_called_with("https://www.tiktok.com/@testuser/video/123")
    bot.user_video_page.like_video.assert_called_once()
    bot.user_video_page.verify_captcha.assert_called_once()


def test_like_video_with_username_and_id(mock_uc_chrome, mock_sadcaptcha, mock_log):
    bot = TikTokBot(api_key="test_api_key", headless=False)
    bot.like_video(username="testuser", video_id="123")

    bot.user_video_page.open_page.assert_called_with("https://www.tiktok.com/@testuser/video/123")
    mock_log.info.assert_any_call("[!] Username should start with '@'. Adding '@' to testuser")


def test_follow_user_with_url(mock_uc_chrome, mock_sadcaptcha):
    bot = TikTokBot(api_key="test_api_key", headless=False)
    bot.follow_user(user_url="https://www.tiktok.com/@testuser")

    bot.user_profile_page.open_page.assert_called_with("https://www.tiktok.com/@testuser")
    bot.user_profile_page.follow_user.assert_called_with(follow=True)


def test_unfollow_user_with_username(mock_uc_chrome, mock_sadcaptcha):
    bot = TikTokBot(api_key="test_api_key", headless=False)
    bot.unfollow_user(username="testuser")

    bot.user_profile_page.open_page.assert_called_with("https://www.tiktok.com/@testuser")
    bot.user_profile_page.follow_user.assert_called_with(follow=False)


def test_comment_on_video(mock_uc_chrome, mock_sadcaptcha):
    bot = TikTokBot(api_key="test_api_key", headless=False)
    bot.comment_on_video("https://www.tiktok.com/@testuser/video/123", "Test comment")

    bot.user_video_page.open_page.assert_called_with("https://www.tiktok.com/@testuser/video/123")
    bot.user_video_page.left_comment.assert_called_with("Test comment")
    bot.user_video_page.publish_comment.assert_called_once()


def test_quit(mock_uc_chrome, mock_sadcaptcha):
    bot = TikTokBot(api_key="test_api_key", headless=False)
    bot.quit()
    mock_uc_chrome.close.assert_called_once()
