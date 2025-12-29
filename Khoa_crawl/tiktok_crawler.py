# CODE CRAWLER TIKTOK (FINAL FIX COOKIES & TIMEOUT)
from DrissionPage import ChromiumPage, ChromiumOptions
import os
import time
import json
import torch
import re
import requests 

# ❗ ĐÃ SỬA: Thay thế 'import whisper' bằng 'from faster_whisper import WhisperModel'
from faster_whisper import WhisperModel 

# --- CẤU HÌNH ---
# Sử dụng os.path.join để đảm bảo đường dẫn hoạt động trên mọi hệ điều hành
INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'link_tiktok.txt')
OUTPUT_DIR = 'dataset_tiktok'
FOLDERS = {
    'video': os.path.join(OUTPUT_DIR, 'video'),
    'audio': os.path.join(OUTPUT_DIR, 'audio'),
    'transcript': os.path.join(OUTPUT_DIR, 'transcripts')
}

print("⏳ Đang khởi động AI Model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
# ❗ ĐÃ SỬA: Khởi tạo model từ Faster Whisper
ai_model = WhisperModel("base", device=device, compute_type="int8") 
print(f"✅ AI Sẵn sàng! (Đang chạy trên {device.upper()})")

def setup_dirs():
    for p in FOLDERS.values():
        if not os.path.exists(p): os.makedirs(p)

# Giữ nguyên hàm get_cookies_safe (Đã hoạt động tốt)
def get_cookies_safe(page):
    """
    Hàm lấy cookies an toàn cho mọi phiên bản DrissionPage
    """
    try:
        cookies_list = page.cookies()
        cookies_dict = {}
        for cookie in cookies_list:
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookies_dict[name] = value
        return cookies_dict
    except Exception as e:
        print(f"   ⚠️ Lỗi lấy cookies: {e}")
        return {}

# Giữ nguyên hàm download_video_direct (Logic bắt gói tin đã ổn)
def download_video_direct(url, save_path):
    co = ChromiumOptions()
    co.set_argument('--mute-audio')
    
    current_folder = os.path.dirname(os.path.abspath(__file__))
    co.set_user_data_path(os.path.join(current_folder, 'User_Data_TikTok'))
    
    page = ChromiumPage(co)
    
    try:
        page.listen.start()
        print(f"   🌍 Truy cập: {url}")
        page.get(url)
        
        if not page.ele('tag:video', timeout=15):
            print("   ❌ Không thấy video (Mạng chậm hoặc Link lỗi).")
            return False

        print("   🎧 Đang dò tìm gói tin video...")
        found_url = None
        
        for packet in page.listen.steps(timeout=25):
            try:
                if not packet.response: continue 
                content_type = packet.response.headers.get('content-type', '').lower()
                if 'video' in content_type:
                    if packet.response.body and len(packet.response.body) > 100000: 
                        found_url = packet.url
                        print(f"   ⚡ Bắt được link thật: {content_type}")
                        break
            except Exception:
                continue
                    
        if found_url:
            print(f"   ⬇️  Đang tải trực tiếp bằng Python...")
            
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
                
                print(f"   ✅ Tải thành công: {os.path.basename(save_path)}")
                return True
            except Exception as e:
                print(f"   ❌ Lỗi khi tải file: {e}")
                return False
        else:
            print("   ❌ Timeout: Không bắt được gói tin video nào.")
            return False

    except Exception as e:
        print(f"   ❌ Lỗi DrissionPage: {e}")
        return False
    finally:
        page.listen.stop()
        page.quit()

# Giữ nguyên hàm extract_audio_ffmpeg (Yêu cầu FFmpeg trong PATH)
def extract_audio_ffmpeg(video_path, audio_path):
    # Lệnh sử dụng FFmpeg để trích xuất audio (q:a 0 = chất lượng cao nhất)
    cmd = f'ffmpeg -i "{video_path}" -q:a 0 -map a "{audio_path}" -y -loglevel quiet'
    os.system(cmd)

def main():
    # ❗ KHẮC PHỤC LỖI CÚ PHÁP: Khai báo global ngay đầu hàm
    global INPUT_FILE
    
    setup_dirs()
    
    # Bây giờ, lệnh này sử dụng biến global INPUT_FILE đã được khai báo
    if not os.path.exists(INPUT_FILE): 
        print(f"❌ Không tìm thấy file {INPUT_FILE}")
        # Thử đường dẫn cũ nếu đường dẫn mới thất bại
        fallback_path = 'input_links_tiktok.txt'
        if os.path.exists(fallback_path):
            print(f"💡 Đang dùng file fallback: {fallback_path}")
            # Gán giá trị mới cho biến global
            INPUT_FILE = fallback_path 
        else:
            return

    # ... (Các phần còn lại của hàm main)

    with open(INPUT_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"📂 Có {len(urls)} video cần xử lý.")

    for i, url in enumerate(urls):
        print(f"\n{'='*50}")
        print(f"🔄 [{i+1}/{len(urls)}] Đang xử lý: {url}")
        
        try:
            # Trích xuất ID bằng RegEx hoặc dùng timestamp nếu thất bại
            video_id = re.findall(r'\d+', url)[-1]
        except:
            video_id = str(int(time.time()))

        video_path = os.path.join(FOLDERS['video'], f"{video_id}.mp4")
        audio_path = os.path.join(FOLDERS['audio'], f"{video_id}.mp3")
        trans_path = os.path.join(FOLDERS['transcript'], f"{video_id}.txt")

        # 1. Tải Video
        file_downloaded = False
        if os.path.exists(video_path) and os.path.getsize(video_path) > 1024:
            print("   ⏩ Video đã tồn tại, bỏ qua tải.")
            file_downloaded = True
        else:
            file_downloaded = download_video_direct(url, video_path)

        if not file_downloaded:
            print("   ⚠️ Bỏ qua link này do lỗi tải.")
            continue

        # 2. Tách Audio
        if not os.path.exists(audio_path):
            print("   🎵 Đang tách audio...")
            extract_audio_ffmpeg(video_path, audio_path)
        else:
             print("   ⏩ Audio đã tồn tại, bỏ qua tách.")


        # 3. Dịch bằng AI
        if not os.path.exists(trans_path) and os.path.exists(audio_path):
            print(f"   🤖 AI đang nghe và viết lại...")
            try:
                # ❗ ĐÃ SỬA: Gọi transcribe từ Faster Whisper
                # compute_type="int8" (dành cho CPU) hoặc "float16" (dành cho CUDA/GPU)
                use_compute_type = "float16" if device == "cuda" else "int8"
                
                # Faster Whisper sử dụng compute_type thay vì fp16
                result = ai_model.transcribe(audio_path, compute_type=use_compute_type) 
                
                # Faster Whisper trả về generator segments, cần lấy text từ segments
                full_text = " ".join([segment.text for segment in result]) 

                with open(trans_path, 'w', encoding='utf-8') as f:
                    f.write(f"Source: {url}\n\nCONTENT:\n{full_text}")
                print("   ✅ Đã xong Transcript!")
            except Exception as e:
                print(f"   ❌ Lỗi AI Whisper: {e}")
        elif os.path.exists(trans_path):
             print("   ⏩ Transcript đã có sẵn.")

    print("\n✅ HOÀN TẤT TOÀN BỘ!")

if __name__ == "__main__":
    main()