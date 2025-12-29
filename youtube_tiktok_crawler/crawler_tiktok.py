# CODE CRAWLER TIKTOK (FINAL FIX COOKIES & TIMEOUT)
from DrissionPage import ChromiumPage, ChromiumOptions
import os
import time
import json
import whisper
import torch
import re
import requests 

# --- CẤU HÌNH ---
INPUT_FILE = 'input_links_tiktok.txt'
OUTPUT_DIR = 'dataset_tiktok'
FOLDERS = {
    'video': os.path.join(OUTPUT_DIR, 'video'),
    'audio': os.path.join(OUTPUT_DIR, 'audio'),
    'transcript': os.path.join(OUTPUT_DIR, 'transcripts')
}

print("⏳ Đang khởi động AI Model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
ai_model = whisper.load_model("base", device=device) 
print(f"✅ AI Sẵn sàng! (Đang chạy trên {device.upper()})")

def setup_dirs():
    for p in FOLDERS.values():
        if not os.path.exists(p): os.makedirs(p)

def get_cookies_safe(page):
    """
    Hàm lấy cookies an toàn cho mọi phiên bản DrissionPage
    Thay vì dùng as_dict=True (gây lỗi), ta lấy list rồi tự chuyển sang dict
    """
    try:
        # Thử gọi hàm cookies() không tham số
        cookies_list = page.cookies()
        
        # Chuyển đổi list dictionary thành dictionary chuẩn cho requests
        cookies_dict = {}
        for cookie in cookies_list:
            # Kiểm tra kỹ để tránh lỗi key
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookies_dict[name] = value
        return cookies_dict
    except Exception as e:
        print(f"   ⚠️ Lỗi lấy cookies: {e}")
        return {}

def download_video_direct(url, save_path):
    co = ChromiumOptions()
    co.set_argument('--mute-audio')
    
    current_folder = os.path.dirname(os.path.abspath(__file__))
    co.set_user_data_path(os.path.join(current_folder, 'User_Data_TikTok'))
    
    page = ChromiumPage(co)
    
    try:
        page.listen.start()
        print(f"   🌍 Truy cập: {url}")
        page.get(url)
        
        # --- FIX 1: Tăng thời gian chờ load video từ 5s -> 15s ---
        if not page.ele('tag:video', timeout=15):
            print("   ❌ Không thấy video (Mạng chậm hoặc Link lỗi).")
            return False

        print("   🎧 Đang dò tìm gói tin video...")
        found_url = None
        
        # --- FIX 2: Tăng thời gian bắt gói tin từ 15s -> 25s ---
        for packet in page.listen.steps(timeout=25):
            try:
                if not packet.response: continue 
                content_type = packet.response.headers.get('content-type', '').lower()
                if 'video' in content_type:
                    # Lấy file > 100KB
                    if packet.response.body and len(packet.response.body) > 100000: 
                        found_url = packet.url
                        print(f"   ⚡ Bắt được link thật: {content_type}")
                        break
            except Exception:
                continue
                    
        if found_url:
            print(f"   ⬇️  Đang tải trực tiếp bằng Python...")
            
            # --- FIX 3: Lấy cookies theo cách thủ công (bao chạy mọi phiên bản) ---
            cookies = get_cookies_safe(page)
            
            headers = {
                'User-Agent': page.user_agent,
                'Referer': 'https://www.tiktok.com/'
            }
            
            try:
                with requests.get(found_url, headers=headers, cookies=cookies, stream=True) as r:
                    r.raise_for_status()
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): 
                            f.write(chunk)
                
                print(f"   ✅ Tải thành công: {os.path.basename(save_path)}")
                return True
            except Exception as e:
                print(f"   ❌ Lỗi khi tải file: {e}")
                return False
        else:
            print("   ❌ Timeout: Không bắt được gói tin video nào.")
            return False

    except Exception as e:
        print(f"   ❌ Lỗi DrissionPage: {e}")
        return False
    finally:
        page.listen.stop()
        page.quit()

def extract_audio_ffmpeg(video_path, audio_path):
    cmd = f'ffmpeg -i "{video_path}" -q:a 0 -map a "{audio_path}" -y -loglevel quiet'
    os.system(cmd)

def main():
    setup_dirs()
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Không tìm thấy file {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"📂 Có {len(urls)} video cần xử lý.")

    for i, url in enumerate(urls):
        print(f"\n{'='*50}")
        print(f"🔄 [{i+1}/{len(urls)}] Đang xử lý: {url}")
        
        try:
            video_id = re.findall(r'\d+', url)[-1]
        except:
            video_id = str(int(time.time()))

        video_path = os.path.join(FOLDERS['video'], f"{video_id}.mp4")
        audio_path = os.path.join(FOLDERS['audio'], f"{video_id}.mp3")
        trans_path = os.path.join(FOLDERS['transcript'], f"{video_id}.txt")

        # 1. Tải Video
        file_downloaded = False
        if os.path.exists(video_path):
            print("   ⏩ Video đã tồn tại, bỏ qua tải.")
            file_downloaded = True
        else:
            file_downloaded = download_video_direct(url, video_path)

        if not file_downloaded:
            print("   ⚠️ Bỏ qua link này do lỗi tải.")
            continue

        # 2. Tách Audio
        if not os.path.exists(audio_path):
            print("   🎵 Đang tách audio...")
            extract_audio_ffmpeg(video_path, audio_path)

        # 3. Dịch bằng AI
        if not os.path.exists(trans_path) and os.path.exists(audio_path):
            print(f"   🤖 AI đang nghe và viết lại...")
            try:
                use_fp16 = True if device == "cuda" else False
                result = ai_model.transcribe(audio_path, fp16=use_fp16)
                
                with open(trans_path, 'w', encoding='utf-8') as f:
                    f.write(f"Source: {url}\n\nCONTENT:\n{result['text']}")
                print("   ✅ Đã xong Transcript!")
            except Exception as e:
                print(f"   ❌ Lỗi AI Whisper: {e}")
        elif os.path.exists(trans_path):
             print("   ⏩ Transcript đã có sẵn.")

    print("\n✅ HOÀN TẤT TOÀN BỘ!")

if __name__ == "__main__":
    main()