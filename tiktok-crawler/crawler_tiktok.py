import os
import time
import re
import pandas as pd
import torch
import ffmpeg
import yt_dlp
import soundfile as sf
import sherpa_onnx
from huggingface_hub import snapshot_download
from datetime import datetime
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= CẤU HÌNH HỆ THỐNG =================
INPUT_FILE = 'input_links_tiktok.txt'
OUTPUT_DIR = 'dataset_tiktok'
MODEL_DIR = 'model_zipformer'
FOLDERS = {
    'video': os.path.join(OUTPUT_DIR, 'video'),
    'audio': os.path.join(OUTPUT_DIR, 'audio'),
    'transcript': os.path.join(OUTPUT_DIR, 'transcripts')
}
EXCEL_REPORT_FILE = os.path.join(OUTPUT_DIR, 'Bao_Cao_Tong_Hop.xlsx')
VIOLATION_LOG_FILE = os.path.join(OUTPUT_DIR, 'DANH_SACH_VI_PHAM.txt')

# Số luồng chạy song song (Tăng lên 5 nếu mạng khỏe và muốn test gắt hơn)
MAX_WORKERS = 3 

VIOLATION_KEYWORDS = [
    "cam kết 100%", "trị dứt điểm", "hoàn tiền", "khỏi ngay", 
    "nhà tôi ba đời", "điều trị tận gốc", "thần dược", "sạch nám", 
    "bay màu", "hết hẳn", "không tái phát", "đông y"
]

# Khóa để đồng bộ hóa việc ghi file và chạy AI (Tránh xung đột)
log_lock = threading.Lock()
ai_lock = threading.Lock()

# ================= KHỞI TẠO AI (ZIPFORMER) =================
ai_recognizer = None 

def load_ai_model():
    global ai_recognizer
    if ai_recognizer is None:
        print("🚀 Đang khởi tạo Zipformer (Transducer)...")
        encoder_file = os.path.join(MODEL_DIR, "encoder-epoch-20-avg-10.int8.onnx")
        decoder_file = os.path.join(MODEL_DIR, "decoder-epoch-20-avg-10.int8.onnx")
        joiner_file = os.path.join(MODEL_DIR, "joiner-epoch-20-avg-10.int8.onnx")
        tokens_file = os.path.join(MODEL_DIR, "tokens.txt") 

        if not all(os.path.exists(f) for f in [encoder_file, decoder_file, joiner_file, tokens_file]):
            print(f"❌ LỖI: Thiếu file trong '{MODEL_DIR}'.")
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

# ================= CÁC HÀM XỬ LÝ (GIỮ NGUYÊN) =================

def setup_dirs():
    for p in FOLDERS.values():
        if not os.path.exists(p): os.makedirs(p)
    if not os.path.exists(VIOLATION_LOG_FILE):
        with open(VIOLATION_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== LOG VI PHẠM (Tạo lúc: {datetime.now()}) ===\n\n")

def log_violation(vid_id, url, detect_type, violations, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = (
        f"⏰ {timestamp}\nID: {vid_id}\nLink: {url}\nNguồn: {detect_type}\n"
        f"🚨 Lỗi: {', '.join(violations)}\n"
        f"📝 Nội dung:\n{content[:300]}...\n{'-'*50}\n"
    )
    # Dùng Lock để tránh 2 luồng ghi cùng lúc làm lỗi file
    with log_lock:
        with open(VIOLATION_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_text)
    print(f"   📝 [Thread] Đã ghi log vi phạm.")

def download_video_direct(url, save_path):
    #  - Hình dung nhiều luồng tải cùng lúc
    current_folder = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(current_folder, 'tiktok_cookies.txt')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    # CÁCH 1: YT-DLP
    try:
        ydl_opts = {
            'quiet': True, 'no_warnings': True,
            'http_headers': headers,
            'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
            'outtmpl': save_path,
            'ffmpeg_location': current_folder,
            'ignoreerrors': False, 
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        if os.path.exists(save_path): return True
        if os.path.exists(save_path + ".mp4"):
            os.rename(save_path + ".mp4", save_path)
            return True
    except Exception: pass

    # CÁCH 2: API TIKWM
    try:
        api_url = "https://www.tikwm.com/api/"
        data = {'url': url, 'count': 12, 'cursor': 0, 'web': 1, 'hd': 1}
        resp = requests.post(api_url, data=data, headers=headers).json()
        if resp.get('code') == 0:
            data_vid = resp.get('data', {})
            video_download_url = data_vid.get('hdplay') or data_vid.get('play')
            if video_download_url:
                if not video_download_url.startswith("http"):
                    video_download_url = "https://www.tikwm.com" + video_download_url
                video_bytes = requests.get(video_download_url, headers=headers).content
                with open(save_path, 'wb') as f: f.write(video_bytes)
                return True
    except Exception: pass
    return False

def extract_audio_robust(video_path, audio_path):
    try:
        (ffmpeg.input(video_path).output(audio_path, ac=1, ar='16k').overwrite_output().run(quiet=True))
        return True
    except: return False

def analyze_content(text):
    text_lower = text.lower()
    return [kw for kw in VIOLATION_KEYWORDS if kw in text_lower]

def transcribe_smart(recognizer, audio_path):
    try:
        audio, sample_rate = sf.read(audio_path, dtype="float32")
        total_samples = len(audio)
        duration_sec = total_samples / sample_rate
        
        if duration_sec < 60:
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, audio)
            recognizer.decode_stream(stream)
            return stream.result.text
        
        full_text_parts = []
        chunk_duration = 30 
        chunk_samples = int(chunk_duration * sample_rate)
        
        for i in range(0, total_samples, chunk_samples):
            chunk = audio[i : i + chunk_samples]
            if len(chunk) < sample_rate: continue
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, chunk)
            recognizer.decode_stream(stream)
            text_segment = stream.result.text.strip()
            if text_segment: full_text_parts.append(text_segment)
            del stream; del chunk
        return " ".join(full_text_parts)
    except Exception: return ""

# ================= HÀM XỬ LÝ 1 TASK (ĐỂ CHẠY ĐA LUỒNG) =================
def process_single_task(item, index, total):
    url = item['url']
    detect_type = item['type'] 
    desc_text = item['desc']
    
    # Tạo ID
    try: vid_id = re.findall(r'/video/(\d+)', url)[0]
    except: vid_id = str(int(time.time())) + f"_{index}"

    print(f"🔄 [Luồng {threading.get_ident()}] Đang xử lý: {url}")

    v_path = os.path.join(FOLDERS['video'], f"{vid_id}.mp4")
    a_path = os.path.join(FOLDERS['audio'], f"{vid_id}.wav") 
    t_path = os.path.join(FOLDERS['transcript'], f"{vid_id}.txt")

    transcript_text = ""
    violations = []
    status = "✅ Sạch"

    # B1: Tải Video (Không cần khóa, chạy song song thoải mái)
    if not os.path.exists(v_path):
        success = download_video_direct(url, v_path)
        if not success:
            return {"ID": vid_id, "URL": url, "Status": "Lỗi Tải", "Content": ""}
    
    # B2: Tách Audio (Song song ok)
    if not os.path.exists(a_path) and os.path.exists(v_path):
        extract_audio_robust(v_path, a_path)

    # B3: Transcribe AI (CẦN KHÓA CPU NẾU MÁY YẾU)
    # Chúng ta dùng ai_lock để đảm bảo chỉ 1 luồng được dùng AI tại 1 thời điểm
    # để tránh tràn RAM hoặc crash model, nhưng các luồng khác vẫn có thể đang tải video.
    if os.path.exists(a_path):
        if os.path.exists(t_path):
            with open(t_path, 'r', encoding='utf-8') as f: transcript_text = f.read()
        else:
            with ai_lock: # <--- CHỜ ĐẾN LƯỢT DÙNG AI
                recognizer = load_ai_model()
                transcript_text = transcribe_smart(recognizer, a_path)
                if not transcript_text: transcript_text = "[No speech detected]"
                with open(t_path, 'w', encoding='utf-8') as f: f.write(transcript_text)

    # B4: Phân tích
    caption_violations = []
    if desc_text:
        caption_violations = analyze_content(desc_text)
        if detect_type == "KW" and not caption_violations:
            caption_violations.append("Keyword match in Title (Manual)")
    
    audio_violations = analyze_content(transcript_text)
    violations = list(set(caption_violations + audio_violations))
    final_text = f"[CAPTION]: {desc_text}\n[AUDIO]: {transcript_text}"

    if violations:
        status = "⚠️ VI PHẠM"
        log_violation(vid_id, url, detect_type, violations, final_text)

    return {
        "ID": vid_id,
        "URL": url,
        "Detect Source": detect_type,
        "Status": status,
        "Violations": ", ".join(violations),
        "Content": final_text[:500]
    }

# ================= MAIN ĐA LUỒNG =================
def main():
    setup_dirs()
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Thiếu file {INPUT_FILE}."); return

    # Load tasks
    tasks = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            parts = line.strip().split('|')
            if len(parts) >= 3: tasks.append({"url": parts[0], "type": parts[1], "desc": parts[2]})
            else: tasks.append({"url": parts[0], "type": "AI", "desc": ""})

    print(f"📂 Tìm thấy {len(tasks)} link. Kích hoạt {MAX_WORKERS} luồng xử lý...")
    
    # Load model trước 1 lần để cache vào RAM
    load_ai_model()
    
    report_data = []
    
    # CHẠY ĐA LUỒNG
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit tất cả task vào pool
        future_to_url = {executor.submit(process_single_task, item, i, len(tasks)): item for i, item in enumerate(tasks)}
        
        for i, future in enumerate(as_completed(future_to_url)):
            try:
                result = future.result()
                if result:
                    report_data.append(result)
                    print(f"   ✅ [Done] {result['ID']} | Status: {result['Status']}")
            except Exception as exc:
                print(f"   ❌ Lỗi Task: {exc}")

    # Xuất báo cáo cuối cùng
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