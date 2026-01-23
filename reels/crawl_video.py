import os, time, requests, urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CẤU HÌNH ---
KEYWORD = "mỹ phẩm"
SCROLL_COUNT = 5
FOLDER = "ads_output_final"

def crawl_fixed_v5(keyword):
    if not os.path.exists(FOLDER): os.makedirs(FOLDER)

    options = Options()
    # Nếu vẫn lỗi, ông hãy bỏ dòng --headless đi để nhìn nó chạy cho chắc
    options.add_argument("--headless") 
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15) # Đợi tối đa 15s cho mỗi phần tử
    
    q = urllib.parse.quote(keyword)
    url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&q={q}&country=VN&media_type=video"

    try:
        print(f"🚀 Đang thọc sâu vào hệ thống... Chờ nó load nhé!")
        driver.get(url)
        
        seen_videos = set()
        count = 0

        for i in range(SCROLL_COUNT):
            # Đợi cho đến khi ít nhất 1 cái card quảng cáo hiện ra
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'xh8yej3')]")))
            cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'xh8yej3')]")
            
            for card in cards:
                try:
                    # 1. Lấy Video
                    video_tag = card.find_element(By.TAG_NAME, "video")
                    v_url = video_tag.get_attribute("src")
                    
                    if v_url and v_url not in seen_videos:
                        seen_videos.add(v_url)
                        count += 1

                        # 2. Lấy Subtitle (Dùng nhiều Xpath dự phòng)
                        sub_text = "No Sub"
                        possible_xpaths = [
                            ".//div[@style='white-space: pre-wrap;']",
                            ".//div[contains(@class, 'x11i5rnm')]", # Class phổ biến của text
                            ".//span[contains(@class, 'x8t9esn')]"
                        ]
                        
                        for xpath in possible_xpaths:
                            try:
                                element = card.find_element(By.XPATH, xpath)
                                if element.text.strip():
                                    sub_text = element.text
                                    break
                            except: continue

                        # 3. Tải ngay
                        clean_url = v_url.replace("&amp;", "&")
                        response = requests.get(clean_url, timeout=20)
                        
                        with open(f"{FOLDER}/ad_{count}.mp4", "wb") as f: f.write(response.content)
                        with open(f"{FOLDER}/ad_{count}.txt", "w", encoding="utf-8") as f: f.write(sub_text)
                        
                        print(f"✅ Đã hốt bộ {count} | Sub: {sub_text[:20]}...")
                except: continue

            # Cuộn trang và nghỉ để Meta không nghi ngờ
            driver.execute_script("window.scrollBy(0, 1500);")
            time.sleep(4)

    finally:
        driver.quit()
        print(f"\n⚡ Xong! {count} bộ nằm gọn trong '{FOLDER}'")

if __name__ == "__main__":
    crawl_fixed_v5(KEYWORD)