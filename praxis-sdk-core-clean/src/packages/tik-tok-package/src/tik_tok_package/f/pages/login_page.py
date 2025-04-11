from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


class LoginPage:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def open_page(self):
        """Метод для открытия страницы логина"""
        try:
            self.driver.get("https://www.tiktok.com/login/phone-or-email/email")
        except Exception as e:
            print(f"Ошибка при открытии страницы логина: {e}")

    def accept_cookies(self):
        """Метод для принятия условий использования"""
        try:
            print("Ожидание загрузки страницы и принятия условий использования...")
            shadow_host = self.driver.find_element(By.CSS_SELECTOR, "body > tiktok-cookie-banner")
            shadow_root = shadow_host.shadow_root
            button = shadow_root.find_element(By.CSS_SELECTOR, "div > div.button-wrapper > button:nth-child(2)")
            button.click()
            print("Условия использования приняты.")
        except Exception as e:
            print(f"Ошибка при принятии условий: {e}")

    def login(self, username: str, password: str):
        """Метод для логина"""
        try:
            print("Ожидание загрузки страницы логина...")
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.CSS_SELECTOR, 'input.tiktok-wv3bkt-InputContainer')
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-e2e="login-button"]')

            username_field.send_keys(username)
            password_field.send_keys(password)
            login_button.click()

            time.sleep(5)  # Ожидаем переход на другую страницу или успешный логин
            print("Логин выполнен успешно.")
        except Exception as e:
            print(f"Ошибка при логине: {e}")

    def go_to_upload_page(self):
        """Переход на страницу загрузки видео"""
        try:
            self.driver.get("https://www.tiktok.com/upload")
        except Exception as e:
            print(f"Ошибка при переходе на страницу загрузки: {e}")