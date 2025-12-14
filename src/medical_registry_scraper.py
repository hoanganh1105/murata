import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from utils import MurataLogger, BrowserFactory

class MedicalRegistryScraper:
    """
    Component of Murata System.
    Fetches official medical technical categories/procedures from Medinet.
    Acts as the 'Knowledge Base' for detecting violations.
    """
    
    BASE_URL = "https://tracuu.medinet.org.vn/"

    def __init__(self, driver_path=None):
        self.logger = MurataLogger.setup("MedicalRegistryScraper")
        # Pass None to driver_path to let webdriver_manager handle it
        self.driver = BrowserFactory.create_chrome_driver(headless=True, driver_path=driver_path)

    def fetch_technical_categories(self, max_records=20000):
        """
        Scrapes the table of medical techniques.
        """
        self.driver.get(self.BASE_URL)
        self.logger.info(f"Accessing {self.BASE_URL}...")

        try:
            # FIX 1: Dùng JavaScript click cho nút Tìm kiếm ban đầu
            search_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, ".//button[contains(@class, 'btn-dmkt')]"))
            )
            self.driver.execute_script("arguments[0].click();", search_btn)
            
            # Cuộn trang để load table
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        except TimeoutException:
            self.logger.error("Failed to find the search button on Medinet.")
            return []

        collected_data = []
        
        while len(collected_data) < max_records:
            try:
                # Chờ bảng hiện ra
                rows = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
                )
                
                self.logger.info(f"Scraping page... Current records: {len(collected_data)}")

                # Lấy dữ liệu từng dòng
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    row_data = [cell.text for cell in cells if cell.text]
                    
                    # Dữ liệu thực tế có 6 cột (tính cả STT), ta bỏ cột đầu (STT) thì còn 5 cột
                    if len(row_data) > 1:
                        collected_data.append(row_data[1:]) 

                # Logic chuyển trang (Pagination)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                try:
                    next_btn = self.driver.find_element(By.ID, "next_pag_grid")
                    
                    # Kiểm tra xem nút Next có bị disable không (hết trang)
                    if "disabled" in next_btn.get_attribute("class"):
                        self.logger.info("Reached the last page.")
                        break
                    
                    # FIX 2: Dùng JavaScript click cho nút Next Page (Tránh lỗi ElementClickIntercepted)
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    
                    time.sleep(3) # Chờ bảng load lại
                except:
                    self.logger.info("No next button found or end of pages.")
                    break

            except StaleElementReferenceException:
                self.logger.warning("Stale element detected, retrying page...")
                continue
            except Exception as e:
                self.logger.error(f"Error during scraping: {e}")
                break
        
        return collected_data

    def save_data(self, data, filename="murata_knowledge_base.xlsx"):
        if not data:
            self.logger.warning("No data found to save.")
            return

        # FIX 3: Cập nhật header cho khớp với 5 cột dữ liệu thực tế
        # Dự đoán cấu trúc: Mã, Tên Chương, Tên Kỹ Thuật, Phân Tuyến/Ghi chú, Trạng thái
        column_headers = ['Code', 'Chapter Name', 'Technique Name', 'Category/Level', 'Status']
        
        # Phòng hờ trường hợp số cột thay đổi bất ngờ, dùng dynamic columns
        if len(data[0]) != len(column_headers):
            self.logger.warning(f"Column mismatch! Data has {len(data[0])} cols, Header has {len(column_headers)}. Adjusting...")
            column_headers = [f"Col_{i+1}" for i in range(len(data[0]))]

        df = pd.DataFrame(data, columns=column_headers)
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Standard_Categories", index=False)
        self.logger.info(f"Knowledge base saved to {filename}")

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    scraper = MedicalRegistryScraper()
    try:
        # Chạy test với 50 bản ghi trước
        data = scraper.fetch_technical_categories(max_records=50) 
        scraper.save_data(data)
    finally:
        scraper.close()