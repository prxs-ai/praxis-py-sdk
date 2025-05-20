from selenium import webdriver

from selenium.webdriver.common.by import By
import time

from tiktok_captcha_solver import SeleniumSolver

from tik_tok_package.commands.captcha_solver import handle_captcha
from tik_tok_package.log import log


class UserProfilePage:
    def __init__(self, driver: webdriver.Chrome, sadcaptcha: SeleniumSolver):
        self.driver = driver
        self.sadcaptcha = sadcaptcha


    def open_page(self, url):
        """Method for opening the user profile page"""
        self.driver.get(url)
        log.info(f"Opening user profile page: {url}")
        time.sleep(1)
        log.info("Waiting for the page to load...")
        self.sadcaptcha.solve_captcha_if_present()


    def follow_user(self, follow : bool=True):
        """Method for following a user"""
        log.info("Waiting for the follow button to load...")
        # try:

        # if follow is True and is_already_followed is True:
        #     log.info("Already followed")
        #     return
        # elif follow is False and is_already_followed is False:
        #     log.info("Already unfollowed")
        #     return
        button_locator = self.driver.find_element(By.CSS_SELECTOR, 'button[data-e2e="follow-button"]')
        button_locator.click()
        time.sleep(3)
        # except Exception as e:
        #     log.error(f"Error while following a user: {e}")
    @handle_captcha
    def verify_captcha(self):
        """Method for verifying captcha"""
        ...
