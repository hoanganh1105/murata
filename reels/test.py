import os
import time
import random
import pandas as pd
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= CẤU HÌNH =================
INPUT_FILE = 'No related/links_clean.txt'
OUTPUT_DIR = 'dataset_reels_final1'
VIDEO_DIR = os.path.join(OUTPUT_DIR, 'videos')
REPORT_FILE = os.path.join(OUTPUT_DIR, 'Ket_Qua_Crawl.xlsx')
COOKIE_FILE = 'fb_cookies.txt' 

# Để 2-3 luồng để FB không nghi ngờ. Càng chậm càng chắc, không sót.
MAX_WORKERS = 1 
RETRY_COUNT = 3 # Thử lại 3 lần nếu lỗi

def setup_dirs():
    os.makedirs(VIDEO_DIR, exist_ok=True)

def download_reels_no_loss(url, save_path):
    """Cơ chế tải cực kỳ lỳ lợm, thử lại nhiều lần"""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': save_path,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'socket_timeout': 45,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://www.facebook.com/',
        }
    }

    for i in range(RETRY_COUNT):
        try:
            # Nghỉ ngẫu nhiên trước khi thử
            time.sleep(random.uniform(5, 10)) 
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                if os.path.exists(save_path):
                    return True
        except Exception as e:
            print(f"   ⚠️ Thử lần {i+1} lỗi: {url}")
            continue
    return False

def process_task(url, index):
    # Dọn dẹp link
    clean_url = url.split('|')[0].strip().split('?')[0]
    
    # Tạo ID từ link
    vid_id = clean_url.split('/')[-2] if clean_url.endswith('/') else clean_url.split('/')[-1]
    if not vid_id.isdigit(): 
        vid_id = f"reels_{index}_{int(time.time())}"
        
    save_path = os.path.join(VIDEO_DIR, f"{vid_id}.mp4")

    # Kiểm tra nếu đã tải rồi thì bỏ qua
    if os.path.exists(save_path):
        print(f"⏩ Đã có: {vid_id}")
        return {"ID": vid_id, "URL": url, "Status": "Đã tồn tại"}

    print(f"📥 Đang hốt [{index}]: {clean_url}")
    
    if download_reels_no_loss(clean_url, save_path):
        print(f"✅ Thành công: {vid_id}")
        return {"ID": vid_id, "URL": url, "Status": "Thành công"}
    else:
        print(f"❌ THẤT BẠI sau {RETRY_COUNT} lần: {clean_url}")
        return {"ID": vid_id, "URL": url, "Status": "Thất bại"}



def main():
    setup_dirs()
    if not os.path.exists(INPUT_FILE):
        print("❌ Không thấy file links!")
        return

    # Đọc toàn bộ link
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    print(f"🚀 Bắt đầu crawl KHÔNG SÓT {len(links)} link...")

    results = []
    # Dùng ThreadPool nhưng khống chế số luồng thấp để "tàng hình"
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_task, url, i): url for i, url in enumerate(links)}
        
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            
            # Lưu mỗi khi xong 5 cái
            if len(results) % 5 == 0:
                pd.DataFrame(results).to_excel(REPORT_FILE, index=False)

    pd.DataFrame(results).to_excel(REPORT_FILE, index=False)
    print(f"\n✨ HOÀN THÀNH! Kiểm tra folder: {VIDEO_DIR}")

if __name__ == "__main__":
    main()