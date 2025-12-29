import yt_dlp
import pandas as pd
import json
import os
from typing import List, Dict, Any

# --- CẤU HÌNH CHUNG ---
OUTPUT_DIR = 'youtube_multi_keyword_output'
DOWNLOAD_VIDEO_FILES = False # Đặt True nếu bạn muốn tải cả file video
NUM_VIDEOS_PER_KEYWORD = 500  # Số lượng video muốn lấy thông tin cho mỗi từ khóa

# --- DANH SÁCH TỪ KHÓA BẠN MUỐN CRAWL ---
KEYWORD_LIST = [
    "covid danger"
    
]

# --- CÁC HÀM HỖ TRỢ HIỂN THỊ TIẾN TRÌNH (Giữ nguyên) ---
class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        print(f"Cảnh báo: {msg}")

    def error(self, msg):
        print(f"LỖI: {msg}")

def my_hook(d):
    if d['status'] == 'downloading':
        p = d['_percent_str']
        e = d['_eta_str']
        print(f"Tiến trình: {p} - ETA: {e}", end='\r')
    elif d['status'] == 'finished':
        print(f"Hoàn thành xử lý file {d['filename']}")


# --- HÀM CHÍNH: LẤY THÔNG TIN TỪ MỘT TỪ KHÓA ---
def crawl_single_keyword(search_term: str, num_videos: int) -> List[Dict[str, Any]]:
    """
    Tìm kiếm video theo một từ khóa duy nhất và lấy thông tin.
    """
    search_query = f"ytsearch{num_videos}:{search_term}"
    
    ydl_opts = {
        'simulate': not DOWNLOAD_VIDEO_FILES, 
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
        'outtmpl': os.path.join(OUTPUT_DIR, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True, 
        'logger': MyLogger(),
        'progress_hooks': [my_hook] if DOWNLOAD_VIDEO_FILES else [],
    }

    print(f"\n--- 🔎 Đang tìm kiếm {num_videos} video cho từ khóa: '{search_term}' ---")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
            if not info or 'entries' not in info or not info['entries']:
                print(f"❌ Không tìm thấy video nào cho từ khóa: {search_term}")
                return []

            video_data = []
            urls_to_download = []
            for entry in info['entries']:
                if entry:
                    video_info = {
                        'keyword': search_term, # Thêm cột từ khóa để dễ phân loại sau này
                        'title': entry.get('title'),
                        'url': entry.get('webpage_url'),
                        'duration_sec': entry.get('duration'),
                        'view_count': entry.get('view_count'),
                        'upload_date': entry.get('upload_date'),
                        'channel': entry.get('channel'),
                        'description': entry.get('description', '').replace('\n', ' ')[:100] + '...',
                    }
                    video_data.append(video_info)
                    urls_to_download.append(video_info['url'])

            print(f"✅ Đã lấy thành công thông tin của {len(video_data)} video.")

            # Tải file video nếu được cấu hình
            if DOWNLOAD_VIDEO_FILES and urls_to_download:
                 print("\n--- 💾 Bắt đầu tải xuống file video (Cần FFmpeg) ---")
                 # Tải xuống từng video
                 ydl.download(urls_to_download)
            
            return video_data

    except Exception as e:
        print(f"\n❌ Đã xảy ra lỗi khi xử lý từ khóa '{search_term}': {e}")
        return []

# --- HÀM LƯU DỮ LIỆU TỔNG HỢP ---
def save_data(all_data: List[Dict[str, Any]], filename_prefix: str):
    if not all_data:
        print("Không có dữ liệu tổng hợp để lưu.")
        return

    # 1. Lưu vào JSON (Tổng hợp)
    json_path = os.path.join(OUTPUT_DIR, f'{filename_prefix}_all_data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Dữ liệu JSON tổng hợp đã lưu tại: {json_path}")

    # 2. Lưu vào CSV (Tổng hợp)
    csv_path = os.path.join(OUTPUT_DIR, f'{filename_prefix}_all_data.csv')
    df = pd.DataFrame(all_data)
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"✅ Dữ liệu CSV tổng hợp đã lưu tại: {csv_path}")


# --- CHẠY CHƯƠNG TRÌNH CHÍNH ---
if __name__ == "__main__":
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    all_crawled_data = []

    # Lặp qua từng từ khóa trong danh sách
    for keyword in KEYWORD_LIST:
        results = crawl_single_keyword(
            search_term=keyword,
            num_videos=NUM_VIDEOS_PER_KEYWORD
        )
        all_crawled_data.extend(results) # Thêm kết quả của từng từ khóa vào danh sách tổng hợp

    # Lưu dữ liệu tổng hợp sau khi crawl xong tất cả các từ khóa
    save_data(all_crawled_data, "multi_keyword")

    print("\n=======================================================")
    print(f"HOÀN TẤT: Đã xử lý {len(KEYWORD_LIST)} từ khóa và tổng hợp {len(all_crawled_data)} mục dữ liệu.")
    print("=======================================================")