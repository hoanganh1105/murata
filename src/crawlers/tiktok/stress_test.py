import os
import time
import re
import pandas as pd
import yt_dlp
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= CẤU HÌNH STRESS TEST =================
INPUT_FILE = 'input_links_tiktok.txt'
OUTPUT_DIR = 'dataset_tiktok_stress_test' 
VIDEO_DIR = os.path.join(OUTPUT_DIR, 'video')
EXCEL_REPORT_FILE = os.path.join(OUTPUT_DIR, 'Ket_Qua_Stress_Test.xlsx')

MAX_WORKERS = 8 # Số luồng chạy song song

# [NEW] BIẾN ĐẾM TOÀN CỤC & KHÓA
counter_lock = threading.Lock()
global_success = 0
global_fail = 0
global_processed = 0
total_tasks = 0

# ================= HÀM HỖ TRỢ =================
def setup_dirs():
    if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

def download_video_direct(url, save_path):
    # Logic Hybrid: YT-DLP -> TikWM
    current_folder = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(current_folder, 'tiktok_cookies.txt')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    # CÁCH 1: YT-DLP
    try:
        ydl_opts = {
            'quiet': True, 'no_warnings': True,
            'http_headers': headers,
            'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
            'outtmpl': save_path,
            'ignoreerrors': False, 
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        if os.path.exists(save_path): return "Success"
        if os.path.exists(save_path + ".mp4"):
            os.rename(save_path + ".mp4", save_path)
            return "Success"
    except Exception: pass

    # CÁCH 2: API TIKWM
    try:
        api_url = "https://www.tikwm.com/api/"
        data = {'url': url, 'count': 12, 'cursor': 0, 'web': 1, 'hd': 1}
        resp = requests.post(api_url, data=data, headers=headers).json()
        if resp.get('code') == 0:
            data_vid = resp.get('data', {})
            video_download_url = data_vid.get('hdplay') or data_vid.get('play')
            if video_download_url:
                if not video_download_url.startswith("http"):
                    video_download_url = "https://www.tikwm.com" + video_download_url
                video_bytes = requests.get(video_download_url, headers=headers).content
                with open(save_path, 'wb') as f: f.write(video_bytes)
                return "Success"
    except Exception: pass
    
    return "Failed"

def process_single_task(item):
    global global_success, global_fail, global_processed
    
    url = item['url']
    try: vid_id = re.findall(r'/video/(\d+)', url)[0]
    except: vid_id = str(int(time.time()))

    v_path = os.path.join(VIDEO_DIR, f"{vid_id}.mp4")
    
    # Thực hiện tải
    status_msg = "Failed"
    if os.path.exists(v_path):
        status_msg = "Skip (Đã có)"
        is_success = True
    else:
        res = download_video_direct(url, v_path)
        status_msg = res
        is_success = (res == "Success")

    # [NEW] CẬP NHẬT BIẾN ĐẾM AN TOÀN (THREAD-SAFE)
    with counter_lock:
        global_processed += 1
        if is_success: global_success += 1
        else: global_fail += 1
        
        current_s = global_success
        current_f = global_fail
        current_p = global_processed
    
    # In thông báo tiến độ thời gian thực
    # Ví dụ: [5/109] ✅ OK: 4 | ❌ Fail: 1 ...
    icon = "✅" if is_success else "❌"
    print(f"[{current_p}/{total_tasks}] {icon} {vid_id} | S: {current_s} | F: {current_f}")

    return {"ID": vid_id, "URL": url, "Status": status_msg}

# ================= MAIN =================
def main():
    global total_tasks
    setup_dirs()
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Thiếu file {INPUT_FILE}."); return

    tasks = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            parts = line.strip().split('|')
            tasks.append({"url": parts[0]})
    
    total_tasks = len(tasks)
    print(f"📂 Stress Test: {total_tasks} link. Luồng: {MAX_WORKERS}")
    print(f"🚀 Bắt đầu oanh tạc...")
    print("-" * 60)

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit task
        futures = [executor.submit(process_single_task, item) for item in tasks]
        
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                print(f"   ❌ Lỗi hệ thống: {exc}")

    end_time = time.time()
    
    print("-" * 60)
    print(f"🏁 KẾT QUẢ CUỐI CÙNG:")
    print(f"⏱️ Thời gian: {end_time - start_time:.2f}s")
    print(f"✅ Tổng thành công: {global_success}")
    print(f"❌ Tổng thất bại: {global_fail}")
    
    if global_fail > 0:
        print("⚠️ CẢNH BÁO: Có thất bại. Hãy xem log ở trên để biết bắt đầu lỗi từ đoạn nào.")

    df = pd.DataFrame(results)
    df.to_excel(EXCEL_REPORT_FILE, index=False)
    print(f"📄 Đã lưu báo cáo: {EXCEL_REPORT_FILE}")

if __name__ == "__main__":
    main()