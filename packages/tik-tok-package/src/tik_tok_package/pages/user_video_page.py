import time

from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from tiktok_captcha_solver import SeleniumSolver

from tik_tok_package.commands.captcha_solver import handle_captcha
from tik_tok_package.log import log


class UserVideoPage:
    def __init__(self, driver: webdriver.Chrome, sadcaptcha: SeleniumSolver):
        self.driver = driver
        self.sadcaptcha = sadcaptcha

    def open_page(self, url):
        """Method for opening the user video page."""
        self.driver.get(url)
        log.info(f"Opening user video page: {url}")
        time.sleep(3)

    def like_video(self):
        """Method for liking a video."""
        # try:
        log.info("Waiting for the like button to load...")
        button_locator = self.driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div[2]/div[2]/div/div[2]/div[1]/div/article[1]/div/section[2]/button[1]",
        )
        is_pressed = button_locator.get_attribute("aria-pressed")
        if is_pressed == "true":
            log.info("Video already liked")
            return
        log.info("Video not liked yet")

        button_locator.click()
        log.info("Video liked")
        time.sleep(3)
        # except Exception as e:
        #     log.error(f"Error while liking video: {e}")

    def open_comment_page(self):
        """Method for opening the comment page."""
        try:  # TODO fix on linux some other ui
            log.info("Waiting for the comment button to load...")
            button_locator = self.driver.find_element(
                By.XPATH,
                "/html/body/div[1]/div[2]/div[2]/div/div[2]/div[1]/div/article[1]/div/section[2]/button[2]",
            )
            button_locator.click()
            log.info("Comment page opened")
            time.sleep(10)
        except Exception as e:
            log.error(f"Error while opening comment page: {e}")

    @handle_captcha
    def left_comment(self, comment: str):
        """Method for leaving a comment on a video."""
        # try:
        log.info("Waiting for the comment input to load...")

        comment_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']")
            )
        )

        # Активируем поле (кликаем в него)
        ActionChains(self.driver).move_to_element(comment_input).click().perform()

        # Медленно печатаем комментарий
        self.slow_typing(comment_input, comment)

        # Можно подождать чуть-чуть
        time.sleep(1)

        # Жмем Enter
        comment_input.send_keys(Keys.ENTER)

        log.info("Comment left")

        # except Exception as e:
        #     log.error(f"Error while leaving a comment: {e}")

    def publish_comment(self):
        """Method for publishing a comment."""
        # try:
        log.info("Waiting for the publish button to load...")
        post_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'div[data-e2e="comment-post"]')
            )
        )

        # Нажимаем
        self.driver.execute_script("arguments[0].click();", post_button)
        log.info("Comment published")
        time.sleep(1)
        # except Exception as e:
        #     log.error(f"Error while publishing comment: {e}")

    def slow_typing(self, element, text, delay=0.1):
        """Печатает текст по одной букве с задержкой."""
        for char in text:
            element.send_keys(char)
            time.sleep(delay)

    @handle_captcha
    def verify_captcha(self):
        """Method for verifying captcha."""
