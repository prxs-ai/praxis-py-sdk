import os

from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

from tiktok_captcha_solver import SeleniumSolver

from tik_tok_package.log import log


class UploadPage:
    def __init__(self, driver: webdriver.Chrome, sadcaptcha: SeleniumSolver):
        self.driver = driver
        self.sadcaptcha = sadcaptcha

    def open_page(self):
        """Method to open the upload page"""
        try:
            log.info("Waiting for the upload page to load...")
            self.driver.get("https://www.tiktok.com/tiktokstudio/upload?from=webapp")
            time.sleep(3)
        except Exception as e:
            log.error(f"Error while open upload page: {e}")

    def upload_video(self, video_path: str):
        """Method for uploading a video"""
        try:
            absolute_path = os.path.abspath(video_path)
            file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')

            # Указываем путь к файлу для загрузки
            file_input.send_keys(absolute_path)

            # Ждем некоторое время для загрузки
            time.sleep(3)

        except Exception as e:
            log.error(f"Error while upload video: {e}")

    def add_description(self, description: str):
        """Method for adding a description to the video"""
        try:
            caption_input = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
            caption_input.click()

            # Очищаем (если нужно)
            caption_input.send_keys(Keys.CONTROL + "a")
            caption_input.send_keys(Keys.BACKSPACE)

            caption_input.send_keys(description)
        except Exception as e:
            log.error(f"Error while adding description for video: {e}")

    def toggle_autor_rules(self):
        """Method for accepting copyright rules"""
        try:
            log.info("Check for accepting copyright rules...")
            autor_rule_button = self.driver.find_element(By.XPATH, '//div[1]/div[6]/div/div/div/div[2]/div')
            autor_rule_button.click()
            for _ in range(60):
                try:
                    self.driver.find_element(By.CSS_SELECTOR, 'div.jsx-478649263.tool-tip.success')
                    log.info("Check autor rules exist...")
                    break
                except NoSuchElementException:
                    log.info("Check autor rules...")
                    time.sleep(1)
            else:
                log.info("⚠️ Autor rules not found, check manually.")
        except Exception as e:
            log.error(f"Error while cheking {e}")

    def click_post_button(self):
        """Method for clicking the post button"""
        try:
            log.info("Upload video...")
            post_button = self.driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div[2]/div/div/div/div[4]/div/button[1]')
            post_button.click()
            log.info("Completed video upload, check manually. If the video is not uploaded, check the error message in the console. If the video is uploaded, you can close the browser.")
        except Exception as e:
            log.error(f"Error while upload video: {e}")
