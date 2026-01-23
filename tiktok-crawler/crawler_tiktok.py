import os
import time
import re
import pandas as pd
import torch
import ffmpeg
import yt_dlp
import soundfile as sf  # [NEW] Thư viện đọc audio cho Zipformer
import sherpa_onnx      # [NEW] Engine chạy model
from huggingface_hub import snapshot_download # [NEW] Tự tải model
from datetime import datetime

# ================= CẤU HÌNH HỆ THỐNG =================
INPUT_FILE = 'input_links_tiktok.txt'
OUTPUT_DIR = 'dataset_tiktok'
MODEL_DIR = 'model_zipformer' # [NEW] Thư mục chứa model Zipformer
FOLDERS = {
    'video': os.path.join(OUTPUT_DIR, 'video'),
    'audio': os.path.join(OUTPUT_DIR, 'audio'),
    'transcript': os.path.join(OUTPUT_DIR, 'transcripts')
}
EXCEL_REPORT_FILE = os.path.join(OUTPUT_DIR, 'Bao_Cao_Tong_Hop.xlsx')
VIOLATION_LOG_FILE = os.path.join(OUTPUT_DIR, 'DANH_SACH_VI_PHAM.txt')

VIOLATION_KEYWORDS = [
    "cam kết 100%", "trị dứt điểm", "hoàn tiền", "khỏi ngay", 
    "nhà tôi ba đời", "điều trị tận gốc", "thần dược", "sạch nám", 
    "bay màu", "hết hẳn", "không tái phát", "đông y"
]

# ================= KHỞI TẠO AI (ZIPFORMER) =================
print("⏳ Đang kiểm tra cấu hình AI...")
ai_recognizer = None 

def load_ai_model():
    global ai_recognizer
    if ai_recognizer is None:
        print("🚀 Đang khởi tạo Zipformer (Transducer)...")
        
        MODEL_DIR = "model_zipformer" 
        
        # Cập nhật đúng tên file như trong ảnh bạn gửi
        encoder_file = os.path.join(MODEL_DIR, "encoder-epoch-20-avg-10.int8.onnx")
        decoder_file = os.path.join(MODEL_DIR, "decoder-epoch-20-avg-10.int8.onnx")
        joiner_file = os.path.join(MODEL_DIR, "joiner-epoch-20-avg-10.int8.onnx")
        tokens_file = os.path.join(MODEL_DIR, "tokens.txt") # Nhớ đổi tên config.json thành file này

        # Kiểm tra file
        if not all(os.path.exists(f) for f in [encoder_file, decoder_file, joiner_file, tokens_file]):
            print(f"❌ LỖI: Thiếu file trong '{MODEL_DIR}'.")
            print("   👉 Hãy đảm bảo bạn đã tải 3 file .int8.onnx và đổi tên config.json -> tokens.txt")
            return None

        try:
            ai_recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=encoder_file,
                decoder=decoder_file,
                joiner=joiner_file,
                tokens=tokens_file,
                num_threads=4,
                sample_rate=16000,
                feature_dim=80,
                provider="cpu",
                decoding_method="greedy_search",
                debug=False
            )
            print("   ✅ Khởi tạo Zipformer thành công!")
        except Exception as e:
            print(f"   ❌ Lỗi khởi tạo Sherpa: {e}")
            raise e
        
    return ai_recognizer
# ================= CÁC HÀM XỬ LÝ =================

def setup_dirs():
    for p in FOLDERS.values():
        if not os.path.exists(p): os.makedirs(p)
    
    if not os.path.exists(VIOLATION_LOG_FILE):
        with open(VIOLATION_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== LOG VI PHẠM (Tạo lúc: {datetime.now()}) ===\n\n")

def log_violation(vid_id, url, detect_type, violations, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = (
        f"⏰ {timestamp}\n"
        f"🆔 ID: {vid_id}\n"
        f"🔗 Link: {url}\n"
        f"🕵️ Nguồn phát hiện: {detect_type}\n"
        f"🚨 Lỗi vi phạm: {', '.join(violations)}\n"
        f"📝 Nội dung trích dẫn:\n{content[:300]}...\n"
        f"{'-'*50}\n"
    )
    with open(VIOLATION_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_text)
    print(f"   📝 Đã ghi vào file log: {VIOLATION_LOG_FILE}")

def download_video_direct(url, save_path):
    print(f"   🌍 Đang xử lý: {url}")
    current_folder = os.path.dirname(os.path.abspath(__file__))
    
    # Logic cũ giữ nguyên
    video_duration = 0
    download_format = 'best'
    
    info_opts = {
        'quiet': True, 'no_warnings': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0...'}
    }
    
    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_duration = info.get('duration', 0)
            if video_duration > 300: download_format = 'worst'
    except: pass

    ydl_opts = {
        'format': download_format,
        'outtmpl': save_path,         
        'quiet': True, 'no_warnings': True,
        'ffmpeg_location': current_folder,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(save_path): return True
        elif os.path.exists(save_path + ".mp4"): 
            os.rename(save_path + ".mp4", save_path)
            return True
        else: return False
    except Exception as e:
        print(f"   ❌ Lỗi yt-dlp: {e}")
        return False

def extract_audio_robust(video_path, audio_path):
    # Hàm này QUAN TRỌNG: ar='16k' là bắt buộc cho Zipformer
    try:
        (ffmpeg.input(video_path).output(audio_path, ac=1, ar='16k').overwrite_output().run(quiet=True))
        return True
    except: return False

def analyze_content(text):
    text_lower = text.lower()
    return [kw for kw in VIOLATION_KEYWORDS if kw in text_lower]

# ================= MAIN =================
def main():
    setup_dirs()
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Thiếu file {INPUT_FILE}.")
        return

    tasks = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            parts = line.strip().split('|')
            if len(parts) >= 3:
                tasks.append({"url": parts[0], "type": parts[1], "desc": parts[2]})
            else:
                tasks.append({"url": parts[0], "type": "AI", "desc": ""})

    print(f"📂 Tìm thấy {len(tasks)} link. Bắt đầu xử lý...")
    report_data = []

    for i, item in enumerate(tasks):
        url = item['url']
        detect_type = item['type'] 
        desc_text = item['desc']
        
        print(f"\n{'='*60}")
        print(f"🔄 [{i+1}/{len(tasks)}] Mode: {detect_type} | URL: {url}")
        
        try: vid_id = re.findall(r'/video/(\d+)', url)[0]
        except: vid_id = str(int(time.time()))
            
        v_path = os.path.join(FOLDERS['video'], f"{vid_id}.mp4")
        a_path = os.path.join(FOLDERS['audio'], f"{vid_id}.wav") # [CHANGE] Zipformer thích .wav hơn .mp3
        t_path = os.path.join(FOLDERS['transcript'], f"{vid_id}.txt")

        final_text = ""
        violations = []
        is_violation = False
        status = "✅ Sạch"

        if detect_type == "KW":
            print("   ⚡ Mode KW: Caption chứa từ khóa -> Bỏ qua tải Video.")
            final_text = f"[CAPTION]: {desc_text}"
            violations = analyze_content(desc_text)
            if not violations: violations = ["Keyword match in Title"]
            is_violation = True
        
        else:
            if not os.path.exists(v_path):
                success = download_video_direct(url, v_path)
                if not success:
                    report_data.append({"ID": vid_id, "URL": url, "Status": "Lỗi Tải", "Violations": ""})
                    continue
            else:
                print("   ⏩ Video đã có sẵn.")

            print("   🤖 Mode AI: Cần nghe nội dung (Zipformer)...")
            if not os.path.exists(a_path): extract_audio_robust(v_path, a_path)
            
            if os.path.exists(a_path):
                if os.path.exists(t_path):
                    with open(t_path, 'r', encoding='utf-8') as f: final_text = f.read()
                else:
                    # [NEW LOGIC] Xử lý bằng Zipformer
                    recognizer = load_ai_model()
                    try:
                        # Đọc file audio bằng soundfile
                        audio, sample_rate = sf.read(a_path, dtype="float32")
                        
                        # Tạo stream để xử lý
                        stream = recognizer.create_stream()
                        stream.accept_waveform(sample_rate, audio)
                        recognizer.decode_stream(stream)
                        
                        final_text = stream.result.text
                        
                        # Fix lỗi nếu text rỗng
                        if not final_text: final_text = "[No speech detected]"
                        
                        with open(t_path, 'w', encoding='utf-8') as f: f.write(final_text)
                        print(f"      ✅ Text: {final_text[:50]}...")
                    except Exception as e: 
                        print(f"   ❌ Lỗi Zipformer: {e}")

                violations = analyze_content(final_text)
                if violations: is_violation = True
            else:
                print("   ❌ Lỗi: Không có file Audio.")

        status = "⚠️ VI PHẠM" if is_violation else "✅ Sạch"
        
        if is_violation:
            print(f"   🚨 VI PHẠM: {', '.join(violations)}")
            log_violation(vid_id, url, detect_type, violations, final_text)
        
        report_data.append({
            "ID": vid_id,
            "URL": url,
            "Detect Source": detect_type,
            "Status": status,
            "Violations": ", ".join(violations),
            "Content": final_text[:500]
        })

    print(f"\n{'='*60}")
    if report_data:
        df = pd.DataFrame(report_data)
        df.sort_values(by="Status", ascending=False, inplace=True)
        try:
            df.to_excel(EXCEL_REPORT_FILE, index=False)
            print(f"✅ Đã xuất báo cáo: {EXCEL_REPORT_FILE}")   
        except PermissionError:
            print("❌ Lỗi: Đóng file Excel trước khi chạy!")

if __name__ == "__main__":
    main()