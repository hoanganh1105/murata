import yt_dlp
import json
import os

# ==============================================================================
#                        CẤU HÌNH THAM SỐ
# ==============================================================================
KEYWORD = "cancer"  # Từ khóa bạn muốn tìm (hoặc URL kênh/playlist)
MAX_VIDEOS = 20 # Số lượng link muốn lấy
OUTPUT_FILE_LINKS = 'input_links_youtube.txt' # File chỉ chứa link (cho tool crawler)
OUTPUT_FILE_METADATA = 'video_metadata.json' # File chứa link, title, description

# ==============================================================================
#                        HÀM 1: LẤY URL VIDEO (TỐC ĐỘ CAO)
# ==============================================================================

def get_youtube_links(query, max_count):
    """Sử dụng yt-dlp ở chế độ flat để lấy nhanh các URL video."""
    print(f"🔍 Đang quét YouTube tìm: '{query}' ({max_count} kết quả)...")
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True, # Chỉ lấy danh sách ID, không tải chi tiết
        'force_generic_extractor': False,
    }

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
                for entry in result['entries']:
                    if entry and 'id' in entry:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        found_links.append(video_url)
            elif 'webpage_url' in result:
                 # Trường hợp chỉ có 1 video lẻ
                 found_links.append(result['webpage_url'])
    except Exception as e:
        print(f"❌ Lỗi khi lấy link: {e}")

    return found_links

# ==============================================================================
#                      HÀM 2: LẤY METADATA (TITLE, DESC)
# ==============================================================================

def get_metadata_from_links(links):
    """Sử dụng yt-dlp để lấy title và description từ danh sách URL."""
    print(f"\n⚙️ Đang lấy metadata chi tiết cho {len(links)} link...")
    metadata_list = []

    # Cấu hình yt-dlp chỉ lấy thông tin, không in ra terminal
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': False, # Cần chi tiết
        'force_generic_extractor': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(links):
            print(f"   -> Xử lý link {i+1}/{len(links)}...", end='\r')
            try:
                info = ydl.extract_info(url, download=False)
                
                # Trích xuất thông tin cần thiết
                metadata_list.append({
                    "url": url,
                    "title": info.get('title', 'N/A'),
                    "description": info.get('description', 'N/A'),
                    "uploader": info.get('uploader', 'N/A')
                })
            except Exception as e:
                print(f"\n   ❌ Lỗi khi lấy metadata cho {url}: {e}")
                metadata_list.append({
                    "url": url,
                    "title": "LỖI TRUY CẬP",
                    "description": "Lỗi truy cập hoặc video đã bị xóa.",
                    "uploader": "N/A"
                })

    print("\n✅ Hoàn thành lấy metadata.")
    return metadata_list

# ==============================================================================
#                        HÀM MAIN CHÍNH
# ==============================================================================

if __name__ == "__main__":
    # 1. Lấy danh sách URL (Tốc độ cao)
    raw_links = get_youtube_links(KEYWORD, MAX_VIDEOS)
    
    if not raw_links:
        print("Không tìm thấy video nào. Kết thúc chương trình.")
    else:
        # 2. Lấy Title và Description từ các URL đã có
        final_metadata = get_metadata_from_links(raw_links)
        
        # 3. Ghi kết quả vào file chỉ chứa link (Dành cho tool crawler)
        with open(OUTPUT_FILE_LINKS, 'w', encoding='utf-8') as f:
            for item in final_metadata:
                f.write(item['url'] + "\n")
        print(f"📝 Đã lưu {len(final_metadata)} link vào '{OUTPUT_FILE_LINKS}'.")
        
        # 4. Ghi toàn bộ metadata vào file JSON (Dễ đọc và xử lý)
        with open(OUTPUT_FILE_METADATA, 'w', encoding='utf-8') as f:
            json.dump(final_metadata, f, ensure_ascii=False, indent=4)
        print(f"📝 Đã lưu {len(final_metadata)} metadata chi tiết vào '{OUTPUT_FILE_METADATA}'.")
        
        # 5. Kết thúc
        print("\n👉 Bạn có thể xem kết quả chi tiết trong file JSON!")