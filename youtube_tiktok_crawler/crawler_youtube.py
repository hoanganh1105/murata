import os
import json
import yt_dlp
import whisper
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
from faster_whisper import WhisperModel

# --- CẤU HÌNH HỆ THỐNG ---
INPUT_FILE = 'input_links_youtube.txt'
OUTPUT_DIR = 'dataset_youtube'
FOLDERS = {
    'video': os.path.join(OUTPUT_DIR, 'video'),
    'audio': os.path.join(OUTPUT_DIR, 'audio'),
    'metadata': os.path.join(OUTPUT_DIR, 'metadata'),
    'transcript': os.path.join(OUTPUT_DIR, 'transcripts')
}

# Load model AI Whisper (Chỉ load 1 lần để tiết kiệm RAM)
# Các options: "tiny", "base", "small", "medium", "large"
# "base" là cân bằng nhất giữa tốc độ và độ chính xác cho nghiên cứu
print("⏳ Đang khởi động AI Model (Whisper)... vui lòng chờ...")
ai_model = whisper.load_model("base")
print("✅ AI Model đã sẵn sàng!")

def setup_directories():
    """Tạo cấu trúc thư mục lưu trữ nếu chưa có"""
    for path in FOLDERS.values():
        if not os.path.exists(path):
            os.makedirs(path)

def get_youtube_transcript_api(video_id):
    """Lấy phụ đề YouTube bằng API (Ưu tiên số 1)"""
    try:
        # Thử lấy tiếng Việt trước, nếu không có thì lấy tiếng Anh
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['vi', 'en'])
        full_text = " ".join([t['text'] for t in transcript_list])
        return full_text
    except Exception:
        return None

print("⏳ Đang khởi động Faster Whisper...")
ai_model = WhisperModel("base", device="cpu", compute_type="int8")

def transcribe_audio_with_ai(audio_path):
    try:
        print(f"   🤖 AI đang nghe: {os.path.basename(audio_path)}...")
        # faster-whisper trả về segments, cần nối lại
        segments, info = ai_model.transcribe(audio_path, beam_size=5)
        full_text = " ".join([segment.text for segment in segments])
        return full_text
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        return None

def process_url(url):
    print(f"\n{'='*50}")
    print(f"🔄 Đang xử lý: {url}")
    
    # Cấu hình yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f"{FOLDERS['video']}/%(id)s.%(ext)s", # Lưu video theo ID để tránh lỗi tên file
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'keepvideo': True, # Giữ lại file video
        # Post-processing để tách Audio ra file MP3 riêng cho AI đọc
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Tải Video & Audio
            print("   ⬇️  Đang tải Video & tách Audio...")
            info = ydl.extract_info(url, download=True)
            
            if not info:
                print("   ❌ Không lấy được thông tin video.")
                return

            video_id = info.get('id')
            title = info.get('title')
            platform = info.get('extractor_key') # 'Youtube' hoặc 'TikTok'
            
            # Đường dẫn file audio (do yt-dlp tự tạo ra sau khi convert)
            # Lưu ý: yt-dlp sẽ lưu file audio cùng chỗ video nhưng đuôi mp3
            audio_filename = f"{video_id}.mp3"
            audio_path = os.path.join(FOLDERS['video'], audio_filename)
            
            # Di chuyển file mp3 sang folder audio cho gọn
            final_audio_path = os.path.join(FOLDERS['audio'], audio_filename)
            if os.path.exists(audio_path):
                os.rename(audio_path, final_audio_path)
            
            print(f"   ✅ Đã tải xong: {title[:50]}...")

            # 2. Lưu Metadata (JSON)
            info = ydl.sanitize_info(info)
            metadata_path = os.path.join(FOLDERS['metadata'], f"{video_id}.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            print("   ✅ Đã lưu Metadata.")

            # 3. Xử lý Transcript (Text)
            transcript_text = None
            method_used = ""

            # Chiến thuật: Nếu là YouTube -> Thử API trước. Nếu thất bại hoặc là TikTok -> Dùng AI.
            if 'Youtube' in platform:
                transcript_text = get_youtube_transcript_api(video_id)
                method_used = "YouTube API (CC)"
            
            if not transcript_text:
                # Nếu API thất bại hoặc là TikTok, dùng AI Whisper
                if os.path.exists(final_audio_path):
                    transcript_text = transcribe_audio_with_ai(final_audio_path)
                    method_used = "OpenAI Whisper (AI Speech-to-Text)"
                else:
                    print("   ⚠️ Không tìm thấy file Audio để chạy AI.")

            # 4. Lưu Transcript
            if transcript_text:
                trans_path = os.path.join(FOLDERS['transcript'], f"{video_id}.txt")
                with open(trans_path, 'w', encoding='utf-8') as f:
                    f.write(f"Source: {url}\nMethod: {method_used}\nTitle: {title}\n\nCONTENT:\n{transcript_text}")
                print(f"   ✅ Đã lưu Transcript (Bằng phương pháp: {method_used})")
            else:
                print("   ⚠️ Không thể lấy được nội dung text.")

    except Exception as e:
        print(f"   ❌ Lỗi xử lý link này: {e}")

def main():
    setup_directories()
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Không tìm thấy file {INPUT_FILE}. Hãy tạo file và dán link vào.")
        return

    with open(INPUT_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"📂 Tìm thấy {len(urls)} links cần xử lý.")
    
    for url in urls:
        process_url(url)
    
    print(f"\n✅ HOÀN TẤT! Kiểm tra dữ liệu trong thư mục '{OUTPUT_DIR}'")

if __name__ == "__main__":
    main()