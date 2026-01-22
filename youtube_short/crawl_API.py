import requests
import isodate
import json # Thêm thư viện JSON

# Cảnh báo: API Key này nên được bảo mật và không nên nhúng trực tiếp trong code sản xuất.
API_KEY = "AIzaSyCF6gy-ld1cit7FZUUmOCWFttT8pjlS1Jk" # Thay bằng API Key của bạn
BASE_URL = "https://www.googleapis.com/youtube/v3/"
YOUTUBE_URL_BASE = "https://www.youtube.com/watch?v=" 

def search_short_videos(query, max_results=50):
    """
    Gửi yêu cầu search.list để tìm các video ngắn (videoDuration=short)
    """
    search_url = f"{BASE_URL}search"
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'videoDuration': 'short', # Lọc sơ bộ: < 4 phút
        'maxResults': max_results,
        'key': API_KEY
    }
    
    response = requests.get(search_url, params=params)
    response.raise_for_status() # Báo lỗi nếu yêu cầu thất bại
    data = response.json()
    
    video_ids = []
    for item in data.get('items', []):
        # Trích xuất videoId từ kết quả tìm kiếm
        if item['id']['kind'] == 'youtube#video':
            video_ids.append(item['id']['videoId'])
            
    print(f"-> Đã tìm thấy {len(video_ids)} video ID ngắn sơ bộ.")
    return video_ids

def get_video_details(video_ids):
    """
    Gửi yêu cầu videos.list để lấy contentDetails (duration) VÀ snippet (title)
    Lưu ý: API chỉ cho phép tối đa 50 ID mỗi lần gọi
    """
    details_url = f"{BASE_URL}videos"
    
    # Gom 50 ID vào một chuỗi
    id_string = ",".join(video_ids)
    
    params = {
        'part': 'contentDetails,snippet', # Lấy cả duration và title
        'id': id_string,
        'key': API_KEY
    }
    
    response = requests.get(details_url, params=params)
    response.raise_for_status()
    data = response.json()
    
    return data.get('items', [])

def filter_shorts(videos_detail_list):
    """
    Phân tích duration, lọc ra video Shorts (thời lượng <= 60 giây),
    và thêm Tiêu đề cùng Link URL đầy đủ.
    """
    shorts_data = []
    
    for item in videos_detail_list:
        try:
            video_id = item['id']
            duration_iso = item['contentDetails']['duration']
            
            # Lấy tiêu đề từ 'snippet'
            video_title = item['snippet']['title'] 
            
            # Tạo link đầy đủ
            video_url = YOUTUBE_URL_BASE + video_id
            
            # Phân tích thời lượng
            duration_timedelta = isodate.parse_duration(duration_iso)
            total_seconds = duration_timedelta.total_seconds()
            
            # Điều kiện LỌC CHÍNH XÁC: Video Shorts <= 60 giây
            if total_seconds <= 60:
                shorts_data.append({
                    'video_id': video_id,
                    'video_title': video_title,
                    'video_url': video_url,
                    'duration_seconds': total_seconds,
                })
                
        except KeyError as e:
            print(f"Cảnh báo: Thiếu trường dữ liệu {e} cho video ID {item.get('id', 'Không rõ')}. Bỏ qua.")
            continue
        except Exception as e:
            # Xử lý nếu chuỗi ISO không hợp lệ
            print(f"Lỗi phân tích duration {duration_iso} cho ID {video_id}: {e}")
            continue
            
    return shorts_data

def save_to_json(data, filename="youtube_shorts_results.json"):
    """
    Lưu danh sách dữ liệu (list of dicts) vào một file JSON.
    """
    if not data:
        print("Không có dữ liệu để lưu.")
        return

    try:
        # Sử dụng json.dump để ghi dữ liệu
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            # indent=4 giúp file JSON dễ đọc hơn (định dạng đẹp)
            json.dump(data, jsonfile, ensure_ascii=False, indent=4)
            
        print(f"\n-> Đã lưu thành công {len(data)} video vào file: {filename}")
        
    except Exception as e:
        print(f"\nLỖI khi lưu file JSON: {e}")


if __name__ == "__main__":
    
    search_query = "ung thư"
    
    print(f"===== BẮT ĐẦU CRAWLING VỚI TỪ KHÓA: {search_query} =====")
    
    # BƯỚC 1: Tìm kiếm sơ bộ (Lấy ID)
    video_ids = search_short_videos(search_query, max_results=50)
    
    if not video_ids:
        print("Không tìm thấy ID video nào.")
    else:
        # BƯỚC 2: Lấy chi tiết thời lượng và Tiêu đề
        videos_detail_list = get_video_details(video_ids)
        
        # BƯỚC 3: Phân tích, Lọc Chính xác và Thêm Link/Title
        final_shorts = filter_shorts(videos_detail_list)
        
        print("\n===== KẾT QUẢ CUỐI CÙNG HIỂN THỊ =====")
        print(f"Tổng số video Shorts được xác định chính xác: {len(final_shorts)}")
        
        # Hiển thị kết quả ra màn hình
        for i, short in enumerate(final_shorts, 1):
            print(f"--- Video {i} ---")
            print(f"  > Tiêu đề: {short['video_title']}")
            print(f"  > Thời lượng: {short['duration_seconds']}s")
            print(f"  > Link URL: {short['video_url']}") 
            
        # BƯỚC 4: LƯU KẾT QUẢ VÀO FILE JSON
        filename = f"{search_query.replace(' ', '_')}_shorts_results.json"
        save_to_json(final_shorts, filename)

    print("\n===== HOÀN TẤT QUY TRÌNH THU THẬP DỮ LIỆU =====")