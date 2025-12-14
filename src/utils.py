import logging
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.proxy import Proxy, ProxyType
from webdriver_manager.chrome import ChromeDriverManager # <--- Thư viện mới

class MurataLogger:
    """
    Centralized logging configuration for the Murata System.
    """
    @staticmethod
    def setup(logger_name="MurataSystem"):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
            handlers=[
                logging.FileHandler("murata_system.log", encoding="utf-8"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(logger_name)

class BrowserFactory:
    """
    Factory class to generate configured WebDriver instances.
    """
    @staticmethod
    def get_random_user_agent():
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0 Safari/537.36"
        ]
        return random.choice(user_agents)

    @staticmethod
    def create_chrome_driver(headless=True, proxy=None, driver_path=None):
        """
        Creates a Chrome WebDriver instance with anti-detection headers.
        Auto-manages ChromeDriver version using webdriver_manager.
        """
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--mute-audio")
        options.add_argument("start-maximized")
        options.add_argument(f"user-agent={BrowserFactory.get_random_user_agent()}")

        if proxy:
            proxy_settings = Proxy()
            proxy_settings.proxy_type = ProxyType.MANUAL
            proxy_settings.http_proxy = proxy
            proxy_settings.ssl_proxy = proxy
            options.proxy = proxy_settings

        # CẬP NHẬT QUAN TRỌNG: Tự động cài đặt driver khớp version Chrome
        try:
            service = Service(ChromeDriverManager().install())
        except Exception as e:
            # Fallback nếu máy không có internet để tải driver, dùng driver local (nếu có)
            print(f"Warning: Could not auto-install driver. Error: {e}")
            service = Service(driver_path if driver_path else "chromedriver.exe")

        return webdriver.Chrome(service=service, options=options)