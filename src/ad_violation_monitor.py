import time
import random
import re
import emoji
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import MurataLogger, BrowserFactory

class AdViolationMonitor:
    """
    Component of Murata System.
    Monitors Facebook Ads Library for potentially violating advertisements.
    """
    
    ADS_LIB_URL = "https://www.facebook.com/ads/library/"

    def __init__(self, headless=False, proxy=None, driver_path=None): 
        # headless=False để bạn xem quá trình chạy
        self.logger = MurataLogger.setup("AdViolationMonitor")
        self.driver = BrowserFactory.create_chrome_driver(headless, proxy, driver_path)

    def clean_text(self, text):
        """Removes emojis and non-printable characters."""
        if not text: return ""
        text = emoji.replace_emoji(text, "")
        text = re.sub(r'[\u0000-\u001F\u007F]+', '', text)
        return text.strip()

    def select_category_and_search(self, keyword):
        """Hàm xử lý logic chọn menu và tìm kiếm"""
        self.driver.get(self.ADS_LIB_URL)
        time.sleep(3)

        # --- BƯỚC 1: MỞ MENU HẠNG MỤC ---
        self.logger.info("Step 1: Trying to open 'Ad Category' menu...")
        try:
            cat_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Ad category') or contains(text(), 'Hạng mục')]/parent::div"))
            )
            cat_btn.click()
            time.sleep(1.5)
        except Exception as e:
            self.logger.error(f"Failed to click category button: {e}")
            return False

        # --- BƯỚC 2: CHỌN 'ALL ADS' ---
        self.logger.info("Step 2: Selecting 'All Ads'...")
        try:
            all_ads = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'All ads') or contains(text(), 'Tất cả quảng cáo')]"))
            )
            all_ads.click()
            time.sleep(1.5)
        except Exception as e:
            self.logger.error(f"Failed to select 'All Ads': {e}")
            return False

        # --- BƯỚC 3: NHẬP TỪ KHÓA ---
        self.logger.info(f"Step 3: Searching for '{keyword}'...")
        try:
            search_box = self.driver.find_element(By.XPATH, ".//input[@type='search']")
            search_box.click() 
            search_box.clear()
            search_box.send_keys(keyword)
            time.sleep(0.5)
            search_box.send_keys(Keys.RETURN)
            
            # QUAN TRỌNG: Chờ lâu hơn chút để quảng cáo load hết
            self.logger.info("Waiting 7s for results to load...")
            time.sleep(7) 
            return True
        except Exception as e:
            self.logger.error(f"Search box error: {e}")
            return False

    def scan_for_keywords(self, keyword, max_posts=50):
        if not self.select_category_and_search(keyword):
            self.logger.error("Could not setup search. Aborting.")
            return []

        collected_ads = []
        unique_ids = set()
        scroll_attempts = 0
        
        self.logger.info("Starting to scan results...")
        
        while len(collected_ads) < max_posts and scroll_attempts < 5:
            try:
                # --- CHIẾN THUẬT V4: TÌM BẰNG NHIỀU DẤU HIỆU ---
                
                # 1. Tìm tất cả các thẻ chứa text "ID: " (Dấu hiệu nhận biết ID quảng cáo)
                # Dấu chấm (.) trong xpath nghĩa là tìm text bên trong thẻ đó
                potential_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'ID: ')]")
                
                # 2. Nếu không thấy, tìm thẻ chứa text "Launched in" hoặc "Bắt đầu chạy"
                if not potential_elements:
                     potential_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Launched in') or contains(text(), 'Bắt đầu chạy')]")
                
                if not potential_elements:
                    self.logger.warning(f"No ads markers found visible on screen yet. Scroll attempt {scroll_attempts+1}/5")

                found_new_in_batch = False
                
                for el in potential_elements:
                    if len(collected_ads) >= max_posts:
                        break
                    
                    try:
                        # Từ cái dấu hiệu (ID text), ta lần ngược lên cha (ancestor) để lấy cả cái hộp quảng cáo
                        # Ta tìm thẻ <div> bao ngoài gần nhất mà có chứa nhiều chữ (đó chính là nội dung)
                        ad_card = el.find_element(By.XPATH, "./ancestor::div[contains(@class, 'x')][1]")
                        
                        # Lấy toàn bộ text trong card
                        raw_text = ad_card.text
                        
                        # --- TRÍCH XUẤT ID ---
                        # Cố gắng tìm chuỗi "ID: 12345678" trong text
                        ad_id = "Unknown"
                        id_match = re.search(r"ID:\s*(\d+)", raw_text)
                        if id_match:
                            ad_id = id_match.group(1)
                        else:
                            # Nếu không thấy ID, dùng tạm hash của nội dung để làm ID (tránh trùng)
                            ad_id = str(hash(raw_text[:50]))

                        if ad_id in unique_ids: 
                            continue

                        # --- LẤY NỘI DUNG SẠCH ---
                        clean_content = self.clean_text(raw_text)
                        
                        # --- LẤY ẢNH ---
                        images = [img.get_attribute("src") for img in ad_card.find_elements(By.TAG_NAME, "img")]
                        
                        unique_ids.add(ad_id)
                        collected_ads.append({
                            "Keyword": keyword,
                            "Ad ID": ad_id,
                            "Ad Content": clean_content[:500], # Lấy 500 ký tự đầu
                            "Images": str(images[:2]), 
                            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        found_new_in_batch = True
                        print(f"--> [CAPTURED] Ad ID: {ad_id}")
                        
                    except Exception as inner_e:
                        continue 

                # Scroll logic
                if found_new_in_batch:
                    scroll_attempts = 0 
                else:
                    scroll_attempts += 1
                
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(4, 7))

            except Exception as e:
                self.logger.error(f"Global error during extraction: {e}")
                break

        self.logger.info(f"Finished. Total ads found: {len(collected_ads)}")
        return collected_ads

    def save_report(self, data, filename="murata_violation_report.xlsx"):
        if not data:
            self.logger.info("No data to save.")
            return

        df = pd.DataFrame(data)
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Suspected_Violations", index=False)
        self.logger.info(f"Report saved to {filename}")

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    monitor = AdViolationMonitor(headless=False)
    try:
        keywords = ["cam kết chữa khỏi"] 
        all_data = []
        for kw in keywords:
            data = monitor.scan_for_keywords(kw, max_posts=20)
            all_data.extend(data)
        monitor.save_report(all_data)
    finally:
        monitor.close()