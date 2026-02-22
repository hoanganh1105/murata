import os
import time
from urllib.parse import quote
from yt_dlp import YoutubeDL
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH ---
KEYWORDS = ["suc khoe", "ung thu"] 
PAGES_PER_KEYWORD = 3       # Số lượng Fanpage mỗi từ khóa
DOWNLOAD_DIR = "fb_reels_dataset"
COOKIE_FILE = "www.facebook.com_cookies (1).txt" 
HISTORY_FILE = "downloaded_history.txt"

# Tạo thư mục lưu video nếu chưa có
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- QUẢN LÝ LỊCH SỬ ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_to_history(link):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

# --- HÀM NẠP COOKIE ---
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
                    cookies.append({
                        'domain': parts[0] if parts[0].startswith('.') else f".{parts[0]}",
                        'name': parts[5], 'value': parts[6], 'path': parts[2],
                        'secure': parts[3].upper() == 'TRUE'
                    })
    return cookies

# --- CẤU HÌNH YT-DLP ---
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True, 
        'no_warnings': True, 
        'merge_output_format': 'mp4',
        'cookiefile': COOKIE_FILE 
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"⚠️ Lỗi tải video {url}: {e}")
        return False

# --- HÀM VÉT CẠN REELS ---
def crawl_all_reels_from_page(driver, page_url, history):
    reels_url = page_url.rstrip('/') + "/reels"
    print(f"\n📺 Đang QUÉT SẠCH Reels tại: {reels_url}")
    driver.get(reels_url)
    time.sleep(6)

    retry_scroll = 0
    max_retries = 8
    total_downloaded = 0

    while True:
        reel_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/')]")
        found_new = False
        
        for elem in reel_elements:
            try:
                raw_link = elem.get_attribute("href")
                if not raw_link: continue
                clean_link = raw_link.split('?')[0].split('&')[0]
                
                if clean_link not in history:
                    print(f"📥 Đang tải: {clean_link}")
                    if download_video(clean_link):
                        save_to_history(clean_link)
                        history.add(clean_link)
                        total_downloaded += 1
                        found_new = True
                        time.sleep(1)
            except: continue
        
        # Cuộn trang
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)
        
        if not found_new:
            retry_scroll += 1
            print(f"🔄 Đang tìm thêm (Lần thử {retry_scroll}/{max_retries})...")
            driver.execute_script("window.scrollBy(0, -300);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            if retry_scroll >= max_retries: break
        else:
            retry_scroll = 0
    print(f"✅ Xong trang! Tổng tải: {total_downloaded}")

# --- MAIN ---
if __name__ == "__main__":
    driver = None
    try:
        # Khởi tạo Selenium
        chrome_options = Options()
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_experimental_option("detach", True) # Giữ trình duyệt không tự đóng
        
        print("🚀 Đang khởi tạo Driver...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # Đăng nhập bằng Cookie
        driver.get("https://www.facebook.com")
        time.sleep(2)
        cookies = load_cookies_from_txt(COOKIE_FILE)
        if not cookies:
            print("❌ Không nạp được cookie. Vui lòng kiểm tra file cookie!")
        else:
            for c in cookies:
                try: driver.add_cookie(c)
                except: pass
            driver.refresh()
            time.sleep(5)
            print("🍪 Đã nạp Cookie thành công.")

            history = load_history()
            
            for kw in KEYWORDS:
                print(f"\n🔍 Đang tìm Fanpage cho từ khóa: {kw}")
                driver.get(f"https://www.facebook.com/search/pages/?q={quote(kw)}")
                time.sleep(5)
                
                # Lấy danh sách link Fanpage
                page_nodes = driver.find_elements(By.XPATH, "//a[@role='link' and contains(@href, 'https://www.facebook.com/')]")
                page_links = []
                for node in page_nodes:
                    href = node.get_attribute("href").split('?')[0]
                    if href not in page_links and "search" not in href:
                        page_links.append(href)
                    if len(page_links) >= PAGES_PER_KEYWORD: break
                
                for p in page_links:
                    crawl_all_reels_from_page(driver, p, history)
                    print("☕ Nghỉ 10s tránh bị quét...")
                    time.sleep(10)

    except Exception as e:
        print(f"\n‼️ LỖI HỆ THỐNG: {e}")
    finally:
        if driver:
            print("\n✨ Hoàn thành chương trình. Bạn có thể đóng trình duyệt.")
            # driver.quit() # Tạm thời comment lại để bạn xem kết quả trên màn hình
        input("Nhấn Enter để thoát hoàn toàn...")