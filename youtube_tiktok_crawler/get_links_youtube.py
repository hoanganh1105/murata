import yt_dlp
import json

# --- CẤU HÌNH ---
KEYWORD = "Cam kết 100%"  # Từ khóa bạn muốn tìm (hoặc link kênh)
MAX_VIDEOS = 10                # Số lượng link muốn lấy
OUTPUT_FILE = 'input_links_youtube.txt' # File kết quả để ném sang tool crawler

def get_youtube_links(query, max_count):
    print(f"🔍 Đang quét YouTube tìm: '{query}'...")
    
    # Cấu hình yt-dlp chỉ lấy ID (extract_flat), không tải video -> Cực nhanh
    ydl_opts = {
        'quiet': True,
        'extract_flat': True, # Chỉ lấy danh sách, không tải
        'force_generic_extractor': False,
    }

    # Nếu query là URL kênh -> dùng trực tiếp
    # Nếu query là từ khóa -> thêm tiền tố ytsearch
    if "youtube.com" in query or "youtu.be" in query:
        search_query = query
        # Với kênh, ta cần playlist_end để giới hạn số lượng
        ydl_opts['playlistend'] = max_count
    else:
        # Cú pháp search của yt-dlp: "ytsearch<số_lượng>:<từ_khóa>"
        search_query = f"ytsearch{max_count}:{query}"

    found_links = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
            
            if 'entries' in result:
                # Kết quả trả về là một danh sách video
                for entry in result['entries']:
                    if entry:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        found_links.append(video_url)
            else:
                # Trường hợp chỉ có 1 video lẻ
                found_links.append(result['webpage_url'])

    except Exception as e:
        print(f"❌ Lỗi: {e}")

    return found_links

# --- CHẠY TOOL ---
if __name__ == "__main__":
    # 1. Lấy link
    links = get_youtube_links(KEYWORD, MAX_VIDEOS)
    
    print(f"✅ Đã tìm thấy {len(links)} videos.")
    
    # 2. Ghi vào file (Ghi nối tiếp hoặc ghi đè tùy bạn)
    # Mode 'w': Ghi đè (xóa cũ viết mới)
    # Mode 'a': Ghi nối tiếp (giữ cũ viết thêm)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for link in links:
            f.write(link + "\n")
            
    print(f"📝 Đã lưu danh sách vào '{OUTPUT_FILE}'.")
    print("👉 Giờ bạn hãy chạy file 'crawler_main.py' để bắt đầu tải!")