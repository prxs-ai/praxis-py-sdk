from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import pickle

from tiktok_captcha_solver import SeleniumSolver

from tik_tok_package.log import log


class LoginPage:
    def __init__(self, driver: webdriver.Chrome, sadcaptcha: SeleniumSolver):
        self.driver = driver
        self.sadcaptcha = sadcaptcha

    def open_page(self):
        """Method to open the login page"""
        # try:
        self.driver.get("https://www.tiktok.com/login/phone-or-email/email")
        # except Exception as e:
        #     log.error(f"Error while open login page: {e}")

    def accept_cookies(self):
        """Method for accepting cookies"""
        try:
            log.info("Waiting for the cookie banner to load...")
            time.sleep(2)
            shadow_host = self.driver.find_element(By.CSS_SELECTOR, "body > tiktok-cookie-banner")
            shadow_root = shadow_host.shadow_root
            button = shadow_root.find_element(By.CSS_SELECTOR, "div > div.button-wrapper > button:nth-child(2)")
            button.click()
            log.info("Cookies accepted")
        except Exception as e:
            log.error(f"error while accepting cookies: {e}")

    def login(self, username: str, password: str):
        """Login method"""
        # try:
        log.info("Waiting for the login page to load...")
        username_field = self.driver.find_element(By.NAME, 'username')
        password_field = self.driver.find_element(By.CSS_SELECTOR, 'input.tiktok-wv3bkt-InputContainer')
        login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-e2e="login-button"]')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()

        time.sleep(5)  # Ожидаем переход на другую страницу или успешный логин
        log.info("Login successful, waiting for the page to load...")
        # except Exception as e:
        #     log.error(f"Error while login: {e}")

    def go_to_upload_page(self):
        """Method to go to the upload page after login"""
        # try:
        self.driver.get("https://www.tiktok.com/upload")
        # except Exception as e:
        #     log.error(f"Error while go to upload page: {e}")


    def save_cookies(self):
        filename= "cookies.pkl"
        log.info(f"Saving cookies into {filename}")
        with open(filename, "wb") as f:
            pickle.dump(self.driver.get_cookies(), f)

    def try_to_load_cookies(self):
        filename = "cookies.pkl"
        log.info(f"Loading cookies from {filename}")
        # try:
        with open(filename, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                self.driver.add_cookie(cookie)
        log.info("Cookies loaded successfully")
        return True
        # except FileNotFoundError:
        #     log.error(f"File {filename} not found. Cookies not loaded.")
        #     return False