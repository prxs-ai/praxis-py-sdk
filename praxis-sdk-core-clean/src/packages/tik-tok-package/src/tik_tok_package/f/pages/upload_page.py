import os
from telnetlib import EC

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

from selenium.webdriver.support.wait import WebDriverWait


class UploadPage:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def open_page(self):
        """Метод для открытия страницы загрузки видео"""
        try:
            print("Ожидание загрузки страницы загрузки видео...")
            self.driver.get("https://www.tiktok.com/tiktokstudio/upload?from=webapp")
            time.sleep(3)
        except Exception as e:
            print(f"Ошибка при открытии страницы логина: {e}")

    def upload_video(self, video_path: str):
        """Метод для загрузки видео"""
        try:
            absolute_path = os.path.abspath(video_path)
            file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')

            # Указываем путь к файлу для загрузки
            file_input.send_keys(absolute_path)

            # Ждем некоторое время для загрузки
            time.sleep(3)

        except Exception as e:
            print(f"Ошибка при загрузке видео: {e}")

    def add_description(self, description: str):
        """Метод для добавления описания видео"""
        try:
            caption_input = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
            caption_input.click()

            # Очищаем (если нужно)
            caption_input.send_keys(Keys.CONTROL + "a")
            caption_input.send_keys(Keys.BACKSPACE)

            caption_input.send_keys(description)
        except Exception as e:
            print(f"Ошибка при добавлении описания: {e}")

    def toggle_autor_rules(self):
        """Метод для принятия правил для авторов"""
        try:
            print("Запустить проверку авторских прав...")
            autor_rule_button = self.driver.find_element(By.XPATH, '//div[1]/div[6]/div/div/div/div[2]/div')
            autor_rule_button.click()
            time.sleep(60)
            print("Проверка авторских прав завершена.")
        except Exception as e:
            print(f"Ошибка при принятии правил авторских прав: {e}")

    def click_post_button(self):
        """Метод для клика по кнопке 'Опубликовать'"""
        try:
            print("Запустить публикацию видео...")
            post_button = self.driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div[2]/div/div/div/div[4]/div/button[1]')
            post_button.click()
            print("Видео опубликовано.")
        except Exception as e:
            print(f"Ошибка при публикации видео: {e}")
