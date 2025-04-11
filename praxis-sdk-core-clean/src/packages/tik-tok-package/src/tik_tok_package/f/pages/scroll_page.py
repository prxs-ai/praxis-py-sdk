from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


class ScrollPage:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def accept_policy(self):
        """Метод для принятия политики конфиденциальности"""
        try:
            print("Ожидание загрузки страницы и принятия политики конфиденциальности...")
            button_locator = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[9]/div/div/div[2]/div/button/div/div')
            button_locator.click()
            print("Политика конфиденциальности принята.")
        except Exception as e:
            print(f"Ошибка при принятии политики конфиденциальности")