import os, time, requests, urllib.parse
from concurrent.futures import ThreadPoolExecutor
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
FOLDER = "ads_high_speed"
MAX_WORKERS = 10  # Số lượng video tải cùng lúc (Tăng tốc nằm ở đây)

def download_task(v_url, sub_text, count):
    """Hàm xử lý tải file chạy trong thread riêng"""
    try:
        video_path = f"{FOLDER}/ad_{count}.mp4"
        text_path = f"{FOLDER}/ad_{count}.txt"
        
        # Tải video/audio
        clean_url = v_url.replace("&amp;", "&")
        response = requests.get(clean_url, timeout=30)
        
        if response.status_code == 200:
            with open(video_path, "wb") as f:
                f.write(response.content)
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(sub_text)
            print(f"✅ Đã xong bộ {count}")
    except Exception as e:
        print(f"❌ Lỗi bộ {count}: {e}")

def crawl_high_speed(keyword):
    if not os.path.exists(FOLDER): os.makedirs(FOLDER)

    options = Options()
    options.add_argument("--headless") # Chạy ẩn cho nhanh
    options.add_argument("window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)
    
    q = urllib.parse.quote(keyword)
    url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&q={q}&country=VN&media_type=video"

    seen_videos = set()
    tasks = []
    count = 0

    try:
        print(f"🚀 Khởi động luồng tải siêu tốc cho từ khóa: {keyword}")
        driver.get(url)
        
        # Dùng ThreadPool để quản lý việc tải
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for i in range(SCROLL_COUNT):
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'xh8yej3')]")))
                cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'xh8yej3')]")
                
                for card in cards:
                    try:
                        video_tag = card.find_element(By.TAG_NAME, "video")
                        v_url = video_tag.get_attribute("src")
                        
                        if v_url and v_url not in seen_videos and not v_url.startswith("blob:"):
                            seen_videos.add(v_url)
                            count += 1
                            
                            # Lấy text nhanh
                            try:
                                sub_text = card.find_element(By.XPATH, ".//div[@style='white-space: pre-wrap;']").text
                            except:
                                sub_text = "No Sub"

                            # Đẩy việc tải vào hàng chờ đa luồng (Không đợi tải xong mới cuộn tiếp)
                            executor.submit(download_task, v_url, sub_text, count)
                            
                    except: continue

                # Cuộn xuống để load thêm card mới
                driver.execute_script("window.scrollBy(0, 3000);")
                print(f"⬇️ Đang cuộn trang lần {i+1}...")
                time.sleep(3) 

    finally:
        driver.quit()
        print(f"\n⚡ Đã gửi toàn bộ lệnh tải. Đang chờ các luồng hoàn tất...")

if __name__ == "__main__":
    start_time = time.time()
    crawl_high_speed(KEYWORD)
    print(f"⏱️ Tổng thời gian: {time.time() - start_time:.2f} giây")