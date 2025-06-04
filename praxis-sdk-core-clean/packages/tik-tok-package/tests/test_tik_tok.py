import pickle
from unittest.mock import mock_open

import pytest
from tik_tok_package.bot import TikTokBot
from tik_tok_package.log import log


@pytest.fixture
def tiktok_bot(mocker):
    mocker.patch("undetected_chromedriver.Chrome")
    mocker.patch("tik_tok_package.bot.SeleniumSolver")
    bot = TikTokBot(api_key="test_api_key", session_name="test_session", headless=False)
    yield bot
    bot.quit()


@pytest.fixture
def mock_subprocess(mocker):
    return mocker.patch("subprocess.run")


@pytest.mark.asyncio
async def test_init(tiktok_bot, mocker):
    mocker.patch("os.path.exists", return_value=False)
    assert tiktok_bot.session_name == "test_session"
    assert tiktok_bot.cookies_path == "sessions/test_session_cookies.pkl"
    assert tiktok_bot.driver is not None
    assert tiktok_bot.sadcaptcha is not None
    tiktok_bot.driver.get.assert_any_call("https://www.tiktok.com/")


@pytest.mark.asyncio
async def test_ensure_chrome_installed_linux(tiktok_bot, mock_subprocess, mocker):
    mocker.patch("platform.system", return_value="Linux")
    mock_subprocess.return_value.stdout = "/usr/bin/google-chrome\n"
    result = tiktok_bot._ensure_chrome_installed()
    assert result == "/usr/bin/google-chrome"
    mock_subprocess.assert_any_call(
        "which google-chrome", capture_output=True, shell=True, text=True
    )


@pytest.mark.asyncio
async def test_ensure_chrome_installed_unsupported_os(tiktok_bot, mocker):
    mocker.patch("platform.system", return_value="Windows")
    result = tiktok_bot._ensure_chrome_installed()
    assert result is None


@pytest.mark.asyncio
async def test_get_settings(tiktok_bot):
    options = tiktok_bot._get_settings()
    assert "--disable-setuid-sandbox" in options.arguments
    assert "--disable-extensions" in options.arguments


@pytest.mark.asyncio
async def test_load_cookies_exists(tiktok_bot, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mock_cookies = [{"name": "test", "value": "value"}]
    mocker.patch("builtins.open", mock_open(read_data=pickle.dumps(mock_cookies)))
    tiktok_bot._load_cookies()
    tiktok_bot.driver.add_cookie.assert_called_once_with(
        {"name": "test", "value": "value"}
    )


@pytest.mark.asyncio
async def test_load_cookies_not_exists(tiktok_bot, mocker):
    mocker.patch("os.path.exists", return_value=False)
    tiktok_bot._load_cookies()
    tiktok_bot.driver.add_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_save_cookies(tiktok_bot, mocker):
    mock_cookies = [{"name": "test", "value": "value"}]
    tiktok_bot.driver.get_cookies.return_value = mock_cookies
    mocker.patch("os.makedirs")
    mock_file = mock_open()
    mocker.patch("builtins.open", mock_file)
    tiktok_bot._save_cookies()
    mock_file().write.assert_called_once_with(pickle.dumps(mock_cookies))


@pytest.mark.asyncio
async def test_is_logged_in_true(tiktok_bot):
    tiktok_bot.driver.current_url = "https://www.tiktok.com/upload"
    assert tiktok_bot.is_logged_in() is True
    tiktok_bot.driver.get.assert_called_with("https://www.tiktok.com/upload")


@pytest.mark.asyncio
async def test_is_logged_in_false(tiktok_bot):
    tiktok_bot.driver.current_url = "https://www.tiktok.com/login"
    assert tiktok_bot.is_logged_in() is False


@pytest.mark.asyncio
async def test_login_not_logged_in(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot, "is_logged_in", return_value=False)
    mocker.patch.object(tiktok_bot.login_page, "open_page")
    mocker.patch.object(tiktok_bot.login_page, "accept_cookies")
    mocker.patch.object(tiktok_bot.login_page, "login")
    mocker.patch.object(tiktok_bot.scroll_page, "wait_for_open_scroll_page")
    mocker.patch.object(tiktok_bot, "_save_cookies")
    mocker.patch("time.sleep")

    tiktok_bot.login("user", "pass")
    tiktok_bot.login_page.open_page.assert_called_once()
    tiktok_bot.login_page.accept_cookies.assert_called_once()
    tiktok_bot.login_page.login.assert_called_once_with("user", "pass")
    tiktok_bot.scroll_page.wait_for_open_scroll_page.assert_called_once()
    tiktok_bot._save_cookies.assert_called_once()


@pytest.mark.asyncio
async def test_login_already_logged_in(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot, "is_logged_in", return_value=True)
    mocker.patch.object(tiktok_bot.login_page, "login")
    tiktok_bot.login("user", "pass")
    tiktok_bot.login_page.login.assert_not_called()


@pytest.mark.asyncio
async def test_upload_video(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot.upload_page, "open_page")
    mocker.patch.object(tiktok_bot.scroll_page, "accept_policy")
    mocker.patch.object(tiktok_bot.upload_page, "upload_video")
    mocker.patch.object(tiktok_bot.upload_page, "add_description")
    mocker.patch.object(tiktok_bot.upload_page, "toggle_autor_rules")
    mocker.patch.object(tiktok_bot.upload_page, "click_post_button")
    mocker.patch("time.sleep")

    tiktok_bot.upload_video("desc", "path/to/video.mp4")
    assert tiktok_bot.upload_page.open_page.call_count == 2
    tiktok_bot.scroll_page.accept_policy.assert_called_once()
    tiktok_bot.upload_page.upload_video.assert_called_once_with("path/to/video.mp4")
    tiktok_bot.upload_page.add_description.assert_called_once_with("desc")
    tiktok_bot.upload_page.toggle_autor_rules.assert_called_once()
    tiktok_bot.upload_page.click_post_button.assert_called_once()


@pytest.mark.asyncio
async def test_like_video_with_url(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot.user_video_page, "open_page")
    mocker.patch.object(tiktok_bot.user_video_page, "like_video")
    mocker.patch.object(tiktok_bot.user_video_page, "verify_captcha")

    tiktok_bot.like_video(video_url="https://www.tiktok.com/@user/video/123")
    tiktok_bot.user_video_page.open_page.assert_called_once_with(
        "https://www.tiktok.com/@user/video/123"
    )
    tiktok_bot.user_video_page.like_video.assert_called_once()
    tiktok_bot.user_video_page.verify_captcha.assert_called_once()


@pytest.mark.asyncio
async def test_like_video_with_username_and_id(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot.user_video_page, "open_page")
    mocker.patch.object(tiktok_bot.user_video_page, "like_video")
    mocker.patch.object(tiktok_bot.user_video_page, "verify_captcha")
    mocker.patch.object(log, "info")

    tiktok_bot.like_video(username="user", video_id="123")
    tiktok_bot.user_video_page.open_page.assert_called_once_with(
        "https://www.tiktok.com/@user/video/123"
    )
    tiktok_bot.user_video_page.like_video.assert_called_once()
    tiktok_bot.user_video_page.verify_captcha.assert_called_once()
    log.info.assert_called_once_with(
        "[!] Username should start with '@'. Adding '@' to user"
    )


@pytest.mark.asyncio
async def test_like_video_missing_params(tiktok_bot, mocker):
    mocker.patch.object(log, "info")
    with pytest.raises(
        ValueError,
        match="If 'video_url' is not provided, both 'username' and 'video_id' must be provided.",
    ):
        tiktok_bot.like_video()
    log.info.assert_called_once()


@pytest.mark.asyncio
async def test_follow_user_with_url(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot.user_profile_page, "open_page")
    mocker.patch.object(tiktok_bot.user_profile_page, "follow_user")

    tiktok_bot.follow_user(user_url="https://www.tiktok.com/@user")
    tiktok_bot.user_profile_page.open_page.assert_called_once_with(
        "https://www.tiktok.com/@user"
    )
    tiktok_bot.user_profile_page.follow_user.assert_called_once_with(follow=True)


@pytest.mark.asyncio
async def test_follow_user_with_username(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot.user_profile_page, "open_page")
    mocker.patch.object(tiktok_bot.user_profile_page, "follow_user")
    mocker.patch.object(log, "info")

    tiktok_bot.follow_user(username="user")
    tiktok_bot.user_profile_page.open_page.assert_called_once_with(
        "https://www.tiktok.com/@user"
    )
    tiktok_bot.user_profile_page.follow_user.assert_called_once_with(follow=True)
    log.info.assert_called_once_with(
        "[!] Username should start with '@'. Adding '@' to user"
    )


@pytest.mark.asyncio
async def test_follow_user_missing_params(tiktok_bot, mocker):
    mocker.patch.object(log, "info")
    with pytest.raises(
        ValueError, match="If 'user_url' is not provided, 'username' must be provided."
    ):
        tiktok_bot.follow_user()
    log.info.assert_called_once()


@pytest.mark.asyncio
async def test_unfollow_user(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot.user_profile_page, "open_page")
    mocker.patch.object(tiktok_bot.user_profile_page, "follow_user")

    tiktok_bot.unfollow_user(username="user")
    tiktok_bot.user_profile_page.open_page.assert_called_once_with(
        "https://www.tiktok.com/@user"
    )
    tiktok_bot.user_profile_page.follow_user.assert_called_once_with(follow=False)


@pytest.mark.asyncio
async def test_comment_on_video(tiktok_bot, mocker):
    mocker.patch.object(tiktok_bot.user_video_page, "open_page")
    mocker.patch.object(tiktok_bot.user_video_page, "left_comment")
    mocker.patch.object(tiktok_bot.user_video_page, "publish_comment")

    tiktok_bot.comment_on_video(
        "https://www.tiktok.com/@user/video/123", "test comment"
    )
    tiktok_bot.user_video_page.open_page.assert_called_once_with(
        "https://www.tiktok.com/@user/video/123"
    )
    tiktok_bot.user_video_page.left_comment.assert_called_once_with("test comment")
    tiktok_bot.user_video_page.publish_comment.assert_called_once()


@pytest.mark.asyncio
async def test_quit(tiktok_bot, mocker):
    tiktok_bot.quit()
    tiktok_bot.driver.close.assert_called_once()
