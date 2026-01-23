import os
import time
import requests
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Xử lý lỗi import của MoviePy tùy phiên bản
try:
    from moviepy.editor import VideoFileClip
except (ImportError, ModuleNotFoundError):
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
    except:
        print("❌ Lỗi: Chưa cài đặt MoviePy. Hãy chạy: pip install moviepy==1.0.3")

# --- CẤU HÌNH ---
KEYWORD = "mỹ phẩm"
SCROLL_COUNT = 5       # Số lần cuộn trang để lấy thêm video
FOLDER = "ads_media_mp3" 
MAX_WORKERS = 6        # Số video tải & convert cùng lúc (đừng để quá cao tránh treo máy)

def download_and_convert(v_url, count):
    """Hàm xử lý tải video và tách nhạc mp3"""
    try:
        if not os.path.exists(FOLDER): os.makedirs(FOLDER)
        
        video_path = os.path.join(FOLDER, f"ad_{count}.mp4")
        audio_path = os.path.join(FOLDER, f"ad_{count}.mp3")
        
        # 1. Tải Video từ URL
        print(f"⏳ Đang tải video {count}...")
        clean_url = v_url.replace("&amp;", "&")
        with requests.get(clean_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(video_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)
        
        # 2. Trích xuất Audio sang MP3
        print(f"🎧 Đang tách nhạc cho bộ {count}...")
        clip = VideoFileClip(video_path)
        if clip.audio:
            # Ghi file mp3, tắt log của moviepy cho sạch màn hình
            clip.audio.write_audiofile(audio_path, codec='mp3', logger=None)
            print(f"✅ Đã xong: ad_{count}.mp4 & ad_{count}.mp3")
        else:
            print(f"⚠️ Video {count} không có âm thanh.")
        
        clip.close() # Giải phóng file

    except Exception as e:
        print(f"❌ Lỗi xử lý bộ {count}: {e}")

def start_crawl(keyword):
    if not os.path.exists(FOLDER): os.makedirs(FOLDER)

    # Cấu hình Chrome
    options = Options()
    # options.add_argument("--headless") # Bỏ comment nếu muốn chạy ẩn
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)
    
    q = urllib.parse.quote(keyword)
    url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&q={q}&country=VN&media_type=video"

    seen_videos = set()
    count = 0

    try:
        print(f"🚀 Khởi động trình duyệt... Từ khóa: {keyword}")
        driver.get(url)
        
        # Sử dụng ThreadPool để xử lý song song
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for i in range(SCROLL_COUNT):
                # Đợi video xuất hiện trên trang
                try:
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                except:
                    print("Không tìm thấy video mới, đang cuộn tiếp...")

                videos = driver.find_elements(By.TAG_NAME, "video")
                
                for v_tag in videos:
                    try:
                        v_url = v_tag.get_attribute("src")
                        # Không lấy link blob vì đó là luồng data tạm thời
                        if v_url and v_url not in seen_videos and not v_url.startswith("blob:"):
                            seen_videos.add(v_url)
                            count += 1
                            # Đẩy việc tải và convert vào thread riêng
                            executor.submit(download_and_convert, v_url, count)
                    except: continue

                # Cuộn trang để Facebook load thêm card mới
                driver.execute_script("window.scrollBy(0, 2500);")
                print(f"⬇️ Đã cuộn trang lần {i+1}/{SCROLL_COUNT}")
                time.sleep(4) 

    finally:
        driver.quit()
        print(f"\n⚡ Hoàn tất quét trang! Chờ các luồng tải nốt video cuối cùng...")

if __name__ == "__main__":
    start_time = time.time()
    start_crawl(KEYWORD)
    print(f"⏱️ Tổng cộng hốt được {len(os.listdir(FOLDER))//2} bộ media.")
    print(f"⏱️ Thời gian chạy: {time.time() - start_time:.2f} giây")