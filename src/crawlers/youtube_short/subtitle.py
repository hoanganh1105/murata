import yt_dlp
import os
import json
import re
import time
import random

# Đường dẫn (Kiểm tra kỹ xem file cookie có đúng tên youtube_cookies.txt không)
COOKIE_FILE = 'config/cookies/youtube_cookies.txt'
INPUT_JSON = 'data/raw/youtube_short/vay_nen_1769743247.json'
OUTPUT_DIR = 'data/raw/youtube_short/subtitles_clean'

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def clean_sub_hardcore(vtt_path):
    """Trị dứt điểm mọi loại rác và nhai lại cụm từ"""
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 1. Lọc dòng rác
        cleaned_lines = []
        for line in lines:
            if any(x in line for x in ["-->", "align:", "WEBVTT", "Kind:", "Language:"]):
                continue
            line = re.sub(r'<[^>]+>', '', line).strip()
            if line and not line.isdigit():
                cleaned_lines.append(line)
        
        # 2. Thuật toán Window: Xóa nhai lại (Rolling subs)
        # YouTube: "Hello", "Hello world", "Hello world how" -> Chỉ lấy "Hello world how"
        words = " ".join(cleaned_lines).split()
        final_words = []
        for word in words:
            if not final_words or word.lower() != final_words[-1].lower():
                # Kiểm tra thêm cụm 3 từ để tránh lặp đoạn ngắn
                if len(final_words) >= 3:
                    if word.lower() in [w.lower() for w in final_words[-3:]]:
                        continue
                final_words.append(word)
        
        return " ".join(final_words).strip()
    except: return ""

def crawl_now():
    if not os.path.exists(INPUT_JSON):
        print(f"❌ File JSON đéo tồn tại: {INPUT_JSON}")
        return

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Lấy ID video chuẩn hơn
    links = []
    for item in data:
        url = item.get('video_url') or item.get('url')
        if url: links.append(url)
    
    links = list(set(links)) # Xóa link trùng

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'sub_langs': ['en.*', 'vi.*'],
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'outtmpl': f'{OUTPUT_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # Giả lập trình duyệt thật để tránh bị xích
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(links):
            # Lấy video ID chuẩn từ yt-dlp luôn cho chắc
            try:
                info = ydl.extract_info(url, download=False)
                v_id = info['id']
            except:
                v_id = url.split('/')[-1].split('?')[0]

            print(f"🔄 [{i+1}/{len(links)}] Đang xử lý: {v_id}")
            
            try:
                ydl.download([url])
                
                # Quét tất cả file .vtt liên quan đến v_id
                sub_found = False
                for f in os.listdir(OUTPUT_DIR):
                    if v_id in f and f.endswith('.vtt'):
                        vtt_path = os.path.join(OUTPUT_DIR, f)
                        cleaned = clean_sub_hardcore(vtt_path)
                        
                        if cleaned:
                            with open(os.path.join(OUTPUT_DIR, f"{v_id}.txt"), 'w', encoding='utf-8') as f_out:
                                f_out.write(cleaned)
                            print(f"✅ Ngon: {v_id}.txt")
                            sub_found = True
                        os.remove(vtt_path)
                
                if not sub_found:
                    print(f"⚠️ Thằng này đéo có sub: {v_id}")
                
                # Nghỉ ngẫu nhiên để YouTube đéo nghi ngờ
                time.sleep(random.uniform(3, 7))

            except Exception as e:
                print(f"❌ Lỗi {v_id}: {str(e)[:100]}")
                if "429" in str(e):
                    print("🛑 Ăn gậy 429 rồi. Nghỉ 2 phút...")
                    time.sleep(120)

if __name__ == "__main__":
    crawl_now()