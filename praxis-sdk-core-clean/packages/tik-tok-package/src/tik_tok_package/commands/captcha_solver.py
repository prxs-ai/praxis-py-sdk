import functools


from tik_tok_package.log import log


def handle_captcha(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        class_name = self.__class__.__name__
        method_name = method.__name__

        log.info(f"[{class_name}] Запуск метода: {method_name}")
        log.debug(f"[{class_name}.{method_name}] Аргументы: args={args}, kwargs={kwargs}")

        try:
            if hasattr(self, "sadcaptcha"):
                # log.info(f"[{class_name}.{method_name}] Обнаружен атрибут sadcaptcha в self.")
                if callable(getattr(self.sadcaptcha, "solve_captcha_if_present", None)):
                    # log.info(f"[{class_name}.{method_name}] Вызов solve_captcha_if_present через self.sadcaptcha.")
                    self.sadcaptcha.solve_captcha_if_present()
                else:
                    log.warning(f"[{class_name}.{method_name}] Атрибут sadcaptcha найден, но метод solve_captcha_if_present не вызываемый.")
            elif hasattr(self, "driver"):
                # log.info(f"[{class_name}.{method_name}] Попытка найти sadcaptcha через driver._parent_instance.")
                parent = getattr(self.driver, "_parent_instance", None)
                if parent:
                    # log.info(f"[{class_name}.{method_name}] Найден _parent_instance: {type(parent).__name__}")
                    if hasattr(parent, "sadcaptcha") and callable(getattr(parent.sadcaptcha, "solve_captcha_if_present", None)):
                        # log.info(f"[{class_name}.{method_name}] Вызов solve_captcha_if_present через driver._parent_instance.sadcaptcha.")
                        parent.sadcaptcha.solve_captcha_if_present()
                    else:
                        log.warning(f"[{class_name}.{method_name}] Метод solve_captcha_if_present не найден в parent.sadcaptcha.")
                else:
                    log.warning(f"[{class_name}.{method_name}] Атрибут _parent_instance отсутствует у driver.")
            else:
                log.warning(f"[{class_name}.{method_name}] Не найден способ добраться до sadcaptcha.")
        except Exception as e:
            log.exception(f"[{class_name}.{method_name}] Ошибка при вызове solve_captcha_if_present: {e}")

        try:
            result = method(self, *args, **kwargs)
            log.info(f"[{class_name}.{method_name}] Метод успешно завершён.")
            return result
        except Exception as e:
            log.exception(f"[{class_name}.{method_name}] Ошибка при выполнении метода: {e}")
            raise

    return wrapper