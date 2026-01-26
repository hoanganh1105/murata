import yt_dlp
import os
import json
import time
import random
import re

# --- CẤU HÌNH ---
INPUT_FILE = 'vẩy_nến_results.json'
OUTPUT_DIR = 'Dataset_Crawl_50'
COOKIE_FILE = 'youtube_cookies.txt'

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def clean_sub(vtt_path):
    """Lọc sạch rác kỹ thuật: align, position, timestamps và khử lặp"""
    if not os.path.exists(vtt_path): return ""
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Xóa WEBVTT header, timestamps và các mã kỹ thuật râu ria
        clean = re.sub(r'WEBVTT|Kind:.*|Language:.*|Style:.*|##.*', '', content)
        clean = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3} --> \d{2}:\d{2}:\d{2}[.,]\d{3}', '', clean)
        clean = re.sub(r'align:[^\s]+|position:[^\s]+|size:[^\s]+|<[^>]+>', '', clean)
        
        lines = clean.split('\n')
        final_text = []
        last_line = ""
        for line in lines:
            line = line.strip()
            if not line or line.isdigit(): continue
            # Khử lặp từ trong dòng và khử lặp dòng cuốn chiếu
            words = line.split()
            unique_words = []
            for w in words:
                if not unique_words or w != unique_words[-1]: unique_words.append(w)
            line = " ".join(unique_words)
            if line != last_line:
                final_text.append(line)
                last_line = line
        return " ".join(final_text)
    except: return ""

def start_bulldozer():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Không thấy file {INPUT_FILE}!"); return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Giới hạn 50 cái nếu file json của mày nhiều hơn
    links = [item.get('video_url') for item in data if item.get('video_url')][:50]
    
    ydl_opts = {
        'format': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best',
        'outtmpl': f'{OUTPUT_DIR}/%(id)s.%(ext)s',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'sub_langs': ['en.*'],
        'cookiefile': COOKIE_FILE,
        'quiet': False,
        'no_warnings': True,
        'ignoreerrors': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }

    print(f"🚀 Bắt đầu ủi sạch {len(links)} video vào folder '{OUTPUT_DIR}'...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(links):
            print(f"\n🔥 [{i+1}/{len(links)}] Đang hốt: {url}")
            try:
                # Tải video và sub
                info = ydl.extract_info(url, download=True)
                if info:
                    v_id = info.get('id')
                    # Tìm file vtt để thiến rác thành file txt
                    for file in os.listdir(OUTPUT_DIR):
                        if v_id in file and file.endswith(".vtt"):
                            vtt_p = os.path.join(OUTPUT_DIR, file)
                            txt_content = clean_sub(vtt_p)
                            if txt_content:
                                with open(os.path.join(OUTPUT_DIR, f"{v_id}.txt"), 'w', encoding='utf-8') as ft:
                                    ft.write(txt_content)
                            os.remove(vtt_p) # Xóa file vtt xong chuyện
                
                # Nghỉ để né 429 (quan trọng!)
                time.sleep(random.uniform(5, 10))
            except Exception as e:
                print(f"❌ Bỏ qua {url} do lỗi: {e}")

    print(f"\n🏁 XONG! Toàn bộ 50 video và text đã nằm gọn trong folder: {OUTPUT_DIR}")

if __name__ == "__main__":
    start_bulldozer()