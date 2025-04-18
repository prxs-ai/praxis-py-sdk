from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
import time

from log import log


class UserProfilePage:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def open_page(self, url):
        """Method for opening the user profile page"""
        self.driver.get(url)
        log.info(f"Opening user profile page: {url}")
        time.sleep(3)

    def follow_user(self, follow : bool=True):
        """Method for following a user"""
        try:

            # if follow is True and is_already_followed is True:
            #     log.info("Already followed")
            #     return
            # elif follow is False and is_already_followed is False:
            #     log.info("Already unfollowed")
            #     return
            button_locator = self.driver.find_element(By.CSS_SELECTOR, 'button[data-e2e="follow-button"]')

            button_locator.click()
            time.sleep(5)
        except Exception as e:
            log.error(f"Error while following a user: {e}")

