import yt_dlp
import os
import json
import time
import random

# --- CONFIG (Dùng đường dẫn tương đối để máy nào cũng chạy được) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Thư mục chứa file code này

INPUT_JSON = os.path.join('vay_nen_1769743247.json')
OUTPUT_DIR = os.path.join('output_videos_fast')
COOKIE_FILE = os.path.join('config', 'cookies', 'youtube_cookies.txt')

# Tạo folder output nếu chưa có
os.makedirs(OUTPUT_DIR, exist_ok=True)

def crawl_speed_run():
    if not os.path.exists(INPUT_JSON): 
        print(f"❌ Không tìm thấy file JSON tại: {INPUT_JSON}")
        return
    
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Lọc link
    links = list(set([item.get('video_url') or item.get('url') for item in data if (item.get('video_url') or item.get('url'))]))
    total_videos = len(links)
    print(f"🚀 Bắt đầu xay {total_videos} video trên máy cá nhân...")

    ydl_opts = {
        'format': 'worst', 
        'outtmpl': f'{OUTPUT_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'nocheckcertificate': True,
        'ignoreerrors': True,
        # Nếu chưa cài aria2 trên Windows thì comment 2 dòng dưới lại
        # 'external_downloader': 'aria2c',
        # 'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
    }

    start_all = time.time()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(links):
            print(f"⚡ [{i+1}/{total_videos}] Húp: {url}", end=" ")
            start_single = time.time()
            try:
                ydl.download([url])
                print(f"✅ ({time.time() - start_single:.2f}s)")
                time.sleep(random.uniform(1, 2)) # Nghỉ xíu cho an toàn
            except Exception as e:
                print(f"❌ Lỗi")

    print(f"\n🏁 Xong! Tổng thời gian: {(time.time() - start_all)/60:.2f} phút")

if __name__ == "__main__":
    crawl_speed_run()