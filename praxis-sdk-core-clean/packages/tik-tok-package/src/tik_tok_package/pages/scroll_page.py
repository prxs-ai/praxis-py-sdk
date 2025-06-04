import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from tiktok_captcha_solver import SeleniumSolver

from tik_tok_package.commands.captcha_solver import handle_captcha
from tik_tok_package.log import log


class ScrollPage:
    def __init__(self, driver: webdriver.Chrome, sadcaptcha: SeleniumSolver):
        self.driver = driver
        self.sadcaptcha = sadcaptcha

    def accept_policy(self):
        """Method for accepting the privacy policy."""
        # try:
        log.info("Waiting for the privacy policy to load...")
        button_locator = self.driver.find_element(
            By.XPATH, "/html/body/div[1]/div[9]/div/div/div[2]/div/button/div/div"
        )
        button_locator.click()
        log.info("Policy accepted")
        # except Exception as e:
        #     log.error(f"Error while accepting policy")

    @handle_captcha
    def wait_for_open_scroll_page(self):
        """Method for waiting for the scroll page to open."""
        start_time = time.time()
        timeout = 60  # seconds
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            log.info(f"Current URL: {current_url}")
            if "https://www.tiktok.com/foryou" in current_url:
                break
            time.sleep(1)
