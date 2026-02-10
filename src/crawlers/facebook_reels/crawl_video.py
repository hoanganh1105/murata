import os
import time
from yt_dlp import YoutubeDL
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH ---
FB_EMAIL = ""
FB_PASS = ""

TARGET_LIST = [
    "https://www.facebook.com/profile.php?id=61585278802454&sk=reels_tab",
    "https://www.facebook.com/profile.php?id=61585140699619&sk=reels_tab",
    "https://www.facebook.com/profile.php?id=61582176007959&sk=reels_tab",
]

DOWNLOAD_DIR = "fb_reels_dataset"
COOKIE_FILE = "www.facebook.com_cookies (1).txt" 

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Cấu hình tải video
ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'merge_output_format': 'mp4',
    'cookiefile': COOKIE_FILE 
}

# Khởi tạo Driver
chrome_options = Options()
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def load_cookies_from_txt(file_path):
    cookies = []
    if not os.path.exists(file_path):
        print(f"❌ Không tìm thấy file: {file_path}")
        return cookies
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.startswith('#') and line.strip():
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    cookie = {
                        'domain': parts[0] if parts[0].startswith('.') else f".{parts[0]}",
                        'name': parts[5],
                        'value': parts[6],
                        'path': parts[2],
                        'secure': parts[3].upper() == 'TRUE'
                    }
                    cookies.append(cookie)
    return cookies

def login_with_cookies():
    print(f"🍪 Đang nạp Cookie từ {COOKIE_FILE}...")
    driver.get("https://www.facebook.com")
    time.sleep(3)
    cookies = load_cookies_from_txt(COOKIE_FILE)
    if not cookies: return False
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except: continue
    driver.refresh()
    time.sleep(5)
    return True

def download_video(url):
    start_time = time.time()
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        elapsed = time.time() - start_time
        return True, elapsed
    except Exception as e:
        print(f"⚠️ Lỗi tải {url}: {e}")
        return False, 0

def crawl_target(url):
    print(f"\n🚀 ĐANG XỬ LÝ TRANG: {url}")
    driver.get(url)
    time.sleep(10) # Đợi trang Reels load hẳn

    downloaded_links = set()
    session_times = []
    retry_count = 0
    max_retries = 5 # Số lần cuộn thử nếu không thấy video mới

    while True:
        # Tìm link bằng XPath chuyên dụng cho Reels
        elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/') or contains(@href, '/reels/')]")
        
        new_found_count = 0
        for elem in elements:
            try:
                link = elem.get_attribute("href")
                if link:
                    clean_link = link.split('?')[0].split('&')[0]
                    if clean_link not in downloaded_links:
                        print(f"📥 Đang tải: {clean_link}")
                        success, duration = download_video(clean_link)
                        if success:
                            downloaded_links.add(clean_link)
                            session_times.append(duration)
                            new_found_count += 1
                            print(f"⏱️ Xong trong: {duration:.2f}s")
            except: continue

        # Cơ chế cuộn ép load dữ liệu
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        # Nhích nhẹ lên để kích hoạt trigger load của Facebook
        driver.execute_script("window.scrollBy(0, -500);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5) # Đợi load video mới

        new_height = driver.execute_script("return document.body.scrollHeight")

        # Kiểm tra điều kiện dừng
        if new_height == last_height and new_found_count == 0:
            retry_count += 1
            print(f"🔄 Không thấy video mới, thử lại lần {retry_count}/{max_retries}...")
            if retry_count >= max_retries:
                print(f"🏁 Đã quét cạn kiệt hoặc Facebook dừng load thêm.")
                break
        else:
            retry_count = 0 # Reset nếu vẫn đang load tốt

    # Thống kê sau khi xong 1 trang
    if session_times:
        avg = sum(session_times) / len(session_times)
        print(f"\n--- 📊 THỐNG KÊ TRANG ---")
        print(f"✅ Đã tải: {len(session_times)} videos")
        print(f"⏳ Trung bình: {avg:.2f} giây/video")
        print(f"------------------------\n")

if __name__ == "__main__":
    try:
        start_program = time.time()
        if login_with_cookies():
            for link in TARGET_LIST:
                crawl_target(link)
                print("☕ Nghỉ 15s tránh bị Facebook quét...")
                time.sleep(15)
        
        end_program = time.time()
        print(f"✨ HOÀN THÀNH! Tổng tgian: {(end_program - start_program)/60:.2f} phút.")
    finally:
        driver.quit()