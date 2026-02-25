import os
import time
import threading
import queue
import wave
import numpy as np
import csv
import sherpa_onnx
from pydub import AudioSegment
from yt_dlp import YoutubeDL
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH ---
FB_EMAIL = ""
FB_PASS = ""
COOKIE_FILE = "www.facebook.com_cookies (1).txt" 
MODEL_DIR = "model_zipformer"
DOWNLOAD_DIR = "fb_reels_dataset"
LOG_FILE = "process_log.csv"

TARGET_LIST = [
    "https://www.facebook.com/profile.php?id=61585278802454&sk=reels_tab",
    "https://www.facebook.com/profile.php?id=61585140699619&sk=reels_tab",
]

video_queue = queue.Queue()

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Khởi tạo file log nếu chưa có
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Video Name", "Start Time", "End Time", "Duration (s)", "Status"])

# --- LUỒNG 2: AI PHÂN TÍCH GIỌNG NÓI ---
def ai_worker():
    print("🤖 AI Worker: Đang nạp model Zipformer...")
    try:
        required = [
            f"{MODEL_DIR}/encoder-epoch-20-avg-10.int8.onnx", 
            f"{MODEL_DIR}/decoder-epoch-20-avg-10.int8.onnx", 
            f"{MODEL_DIR}/joiner-epoch-20-avg-10.int8.onnx", 
            f"{MODEL_DIR}/tokens.txt"
        ]
        
        recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=required[0], decoder=required[1],
            joiner=required[2], tokens=required[3], num_threads=4
        )
        print("✅ AI Đã sẵn sàng!")
    except Exception as e:
        print(f"❌ Lỗi nạp Model: {e}")
        return

    while True:
        video_path = video_queue.get()
        if video_path is None: break
        
        v_name = os.path.basename(video_path)
        start_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        t_start = time.time()
        
        audio_tmp = video_path.replace(".mp4", "_temp.wav")
        status = "Success"
        
        try:
            print(f"🧠 AI đang xử lý: {v_name}")
            
            # 1. Tách âm thanh
            audio = AudioSegment.from_file(video_path)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(audio_tmp, format="wav")
            
            # 2. Đọc file WAV
            with wave.open(audio_tmp, "rb") as f:
                num_frames = f.getnframes()
                sample_rate = f.getframerate()
                buf = f.readframes(num_frames)
                samples = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0

            # 3. AI dịch
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples)
            recognizer.decode_stream(stream)
            text_result = stream.result.text.strip()
            
            # 4. Xuất file Text
            txt_path = video_path.replace(".mp4", ".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text_result if text_result else "[Không có tiếng người]")
            
            print(f"📝 Đã xong text cho: {v_name}")

        except Exception as e:
            print(f"❌ Lỗi AI xử lý {v_name}: {e}")
            status = f"Error: {e}"
        finally:
            # Dọn dẹp file tạm
            if os.path.exists(audio_tmp): os.remove(audio_tmp)
            
            # Tính toán thời gian và ghi Log
            t_end = time.time()
            end_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
            duration = round(t_end - t_start, 2)
            
            with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([v_name, start_time_str, end_time_str, duration, status])
            
            video_queue.task_done()

# --- CÁC HÀM CRAWLER ---
def load_cookies_from_txt(file_path):
    cookies = []
    if not os.path.exists(file_path): return cookies
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

def login_facebook(driver):
    print("🔑 Đang nạp Cookies...")
    driver.get("https://www.facebook.com")
    time.sleep(3)
    cookies = load_cookies_from_txt(COOKIE_FILE)
    for cookie in cookies:
        try: driver.add_cookie(cookie)
        except: continue
    driver.refresh()
    time.sleep(5)
    if "login" in driver.current_url or driver.find_elements(By.NAME, "login"):
        try:
            driver.find_element(By.ID, "email").send_keys(FB_EMAIL)
            driver.find_element(By.ID, "pass").send_keys(FB_PASS)
            driver.find_element(By.NAME, "login").click()
            time.sleep(10)
        except: pass

def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'cookiefile': COOKIE_FILE,
        'merge_output_format': 'mp4'
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return True, ydl.prepare_filename(info)
    except: return False, None

def crawl_target(url, driver):
    print(f"\n📡 ĐANG QUÉT TRANG: {url}")
    driver.get(url)
    time.sleep(8)
    downloaded_links = set()
    for _ in range(3):
        elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/') or contains(@href, '/reels/')]")
        for elem in elements:
            try:
                link = elem.get_attribute("href").split('?')[0].split('&')[0]
                if link not in downloaded_links:
                    success, file_path = download_video(link)
                    if success:
                        downloaded_links.add(link)
                        video_queue.put(file_path)
            except: continue
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)

if __name__ == "__main__":
    ai_thread = threading.Thread(target=ai_worker, daemon=True)
    ai_thread.start()

    options = Options()
    options.add_argument("--disable-notifications")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        login_facebook(driver)
        for target in TARGET_LIST:
            crawl_target(target, driver)
        video_queue.join()
    finally:
        driver.quit()
        print(f"✨ HOÀN THÀNH! Kiểm tra kết quả trong '{DOWNLOAD_DIR}' và log tại '{LOG_FILE}'")