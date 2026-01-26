import requests
import isodate
import json

API_KEY = "AIzaSyCF6gy-ld1cit7FZUUmOCWFttT8pjlS1Jk"
BASE_URL = "https://www.googleapis.com/youtube/v3/"
YOUTUBE_URL_BASE = "https://www.youtube.com/watch?v=" 

def get_50_videos(query):
    print(f"🚀 Đang quét 50 video cho từ khóa: {query}...")
    
    # BƯỚC 1: Search lấy 50 ID (YouTube giới hạn max 50 một lần gọi)
    search_url = f"{BASE_URL}search"
    search_params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'videoDuration': 'short', # Lấy các video ngắn (thường < 4 phút)
        'maxResults': 50,
        'key': API_KEY
    }
    
    try:
        res = requests.get(search_url, params=search_params)
        res.raise_for_status()
        search_data = res.json()
        
        items = search_data.get('items', [])
        video_ids = [i['id']['videoId'] for i in items if i['id']['kind'] == 'youtube#video']
        
        if not video_ids:
            print("Không tìm thấy video nào.")
            return []

        # BƯỚC 2: Lấy chi tiết (Title và Duration) để lưu vào JSON
        details_url = f"{BASE_URL}videos"
        detail_params = {
            'part': 'snippet,contentDetails',
            'id': ",".join(video_ids),
            'key': API_KEY
        }
        
        det_res = requests.get(details_url, params=detail_params)
        det_res.raise_for_status()
        detail_data = det_res.json()

        final_list = []
        for item in detail_data.get('items', []):
            duration_iso = item['contentDetails']['duration']
            total_seconds = isodate.parse_duration(duration_iso).total_seconds()
            
            final_list.append({
                'video_id': item['id'],
                'video_title': item['snippet']['title'],
                'video_url': YOUTUBE_URL_BASE + item['id'],
                'duration_seconds': total_seconds
            })
            
        return final_list

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return []

def save_json(data, query):
    filename = f"{query.replace(' ', '_')}_results.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Đã lưu {len(data)} video vào file: {filename}")

if __name__ == "__main__":
    search_query = "vẩy nến"
    results = get_50_videos(search_query)
    if results:
        save_json(results, search_query)