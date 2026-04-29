import os
import time
import re
import pandas as pd
import ffmpeg
import yt_dlp
import soundfile as sf
import sherpa_onnx
from datetime import datetime
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import queue

# ================= CẤU HÌNH HỆ THỐNG =================
INPUT_FILE = 'input_links_tiktok.txt'
OUTPUT_DIR = 'dataset-optimzation'
MODEL_DIR = 'model_zipformer'
FOLDERS = {
    'video': os.path.join(OUTPUT_DIR, 'video'),
    'audio': os.path.join(OUTPUT_DIR, 'audio'),
    'transcript': os.path.join(OUTPUT_DIR, 'transcripts')
}
EXCEL_REPORT_FILE = os.path.join(OUTPUT_DIR, 'report.xlsx')
VIOLATION_LOG_FILE = os.path.join(OUTPUT_DIR, 'list.txt')
ERROR_LOG_FILE = os.path.join(OUTPUT_DIR, 'error_details.txt')

# --- CẤU HÌNH CHẠY ---
RESET_DATA_AT_START = True  # Xóa dữ liệu cũ khi chạy
MAX_WORKERS = 3            # Số luồng tải video
AI_POOL_SIZE = 4            # Số lượng AI (Với GPU GTX 1650 chỉ cần 1 là đủ cân tất cả)

VIOLATION_KEYWORDS = [
    "cam kết 100%", "trị dứt điểm", "hoàn tiền", "khỏi ngay", 
    "nhà tôi ba đời", "điều trị tận gốc", "thần dược", "sạch nám", 
    "bay màu", "hết hẳn", "không tái phát", "đông y"
]

# --- BIẾN TOÀN CỤC & KHÓA (LOCK) ---
success_count = 0
failure_count = 0
counter_lock = threading.Lock() # Khóa để đếm số
print_lock = threading.Lock()   # Khóa để in log không bị lộn xộn
log_lock = threading.Lock()     # Khóa ghi file

# Hàng đợi chứa AI (Thay cho ai_lock cũ)
ai_pool = queue.Queue()

# ================= CLASS & HÀM HỖ TRỢ =================
class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def download_video_direct(url, save_path):
    current_folder = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(current_folder, 'tiktok_cookies.txt')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...'}

    try:
        ydl_opts = {
            'quiet': True,           
            'no_warnings': True,     
            'noprogress': True,      
            'logger': MyLogger(),    
            'http_headers': headers,
            'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
            'outtmpl': save_path,
            'ffmpeg_location': current_folder,
            'ignoreerrors': True, 
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        
        if os.path.exists(save_path): return True
        if os.path.exists(save_path + ".mp4"):
            os.rename(save_path + ".mp4", save_path)
            return True     
    except Exception as e:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] URL: {url} | ERROR: {str(e)}\n")
    
    # Fallback TikWM
    try:
        api_url = "https://www.tikwm.com/api/"
        data = {'url': url, 'count': 12, 'cursor': 0, 'web': 1, 'hd': 1}
        requests.post(api_url, data=data, headers=headers).json()
    except: pass

    return False

# ================= KHỞI TẠO AI (GPU MODE) =================
def init_ai_pool():
    global ai_pool
    # Nếu hàng đợi đã có AI rồi thì không khởi tạo lại
    if not ai_pool.empty(): return

    # Lấy số lượng AI từ cấu hình (Nếu quên chỉnh ở trên thì mặc định là 3 cho mạnh)
    # Bạn nhớ sửa dòng AI_POOL_SIZE = 3 ở đầu file nhé
    num_instances = AI_POOL_SIZE 

    print(f"\n... Đang khởi tạo {num_instances} luồng AI trên GPU (GTX 1650) ...")
    
    encoder_file = os.path.join(MODEL_DIR, "encoder-epoch-20-avg-10.int8.onnx")
    decoder_file = os.path.join(MODEL_DIR, "decoder-epoch-20-avg-10.int8.onnx")
    joiner_file = os.path.join(MODEL_DIR, "joiner-epoch-20-avg-10.int8.onnx")
    tokens_file = os.path.join(MODEL_DIR, "tokens.txt")

    if not all(os.path.exists(f) for f in [encoder_file, decoder_file, joiner_file, tokens_file]):
        print("!!! LỖI: Thiếu file model.")
        return

    try:
        # Vòng lặp tạo nhiều con AI để nạp vào Pool
        for i in range(num_instances):
            recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=encoder_file, decoder=decoder_file, joiner=joiner_file, tokens=tokens_file,
                num_threads=1, 
                sample_rate=16000, feature_dim=80, 
                provider="cuda",  # <--- QUAN TRỌNG: CHẠY BẰNG GPU
                decoding_method="greedy_search", debug=False
            )
            ai_pool.put(recognizer)
            print(f" -> [GPU] Đã khởi tạo AI instance #{i+1}")

        print(f" -> HOÀN TẤT: Đã kích hoạt {num_instances} luồng AI chạy song song!")
        
    except Exception as e:
        print(f"!!! Lỗi kích hoạt GPU: {e}")
        print("!!! Đang thử chuyển về CPU (Chế độ dự phòng 1 luồng)...")
        try:
             # Fallback về CPU chỉ tạo 1 con để tránh treo máy
             recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=encoder_file, decoder=decoder_file, joiner=joiner_file, tokens=tokens_file,
                num_threads=4, sample_rate=16000, feature_dim=80, 
                provider="cpu", decoding_method="greedy_search", debug=False
            )
             ai_pool.put(recognizer)
             print(" -> Đã chạy chế độ CPU (dự phòng).")
        except: pass

# ================= CÁC HÀM XỬ LÝ KHÁC =================

def setup_dirs():
    for p in FOLDERS.values():
        if not os.path.exists(p): os.makedirs(p)
    if not os.path.exists(VIOLATION_LOG_FILE):
        with open(VIOLATION_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== LOG VI PHẠM (Tạo lúc: {datetime.now()}) ===\n\n")

def log_violation(vid_id, url, detect_type, violations, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = (
        f"TIME: {timestamp}\nID: {vid_id}\nLINK: {url}\nNGUON: {detect_type}\n"
        f"LOI: {', '.join(violations)}\n"
        f"NOI DUNG:\n{content[:300]}...\n{'-'*50}\n"
    )
    with log_lock:
        with open(VIOLATION_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_text)

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
    except: return ""

# ================= HÀM XỬ LÝ 1 TASK (ĐÃ SỬA DÙNG POOL) =================
def process_single_task(item, index):
    task_start_time = time.time()
    
    global success_count, failure_count
    url = item['url']
    detect_type = item['type'] 
    desc_text = item['desc']
    
    try: vid_id = re.findall(r'/video/(\d+)', url)[0]
    except: vid_id = f"unknown_{index}"

    v_path = os.path.join(FOLDERS['video'], f"{vid_id}.mp4")
    a_path = os.path.join(FOLDERS['audio'], f"{vid_id}.wav") 
    t_path = os.path.join(FOLDERS['transcript'], f"{vid_id}.txt")

    transcript_text = ""
    violations = []
    status = "SACH" 
    video_real_duration = 0 # [MỚI] Biến lưu độ dài video

    # B1: Tải Video
    is_downloaded = False
    if os.path.exists(v_path):
        is_downloaded = True
    else:
        is_downloaded = download_video_direct(url, v_path)

    if not is_downloaded:
        with counter_lock: failure_count += 1
        task_duration = time.time() - task_start_time
        # Trả về video length = 0 vì không tải được
        return {"ID": vid_id, "Status": "LOI_TAI", "Note": "Khong tai duoc", "Duration": task_duration, "VideoLength": 0}

    with counter_lock: success_count += 1

    # Kiểm tra độ dài video (Skip nếu quá 10 phút)
    try:
        probe = ffmpeg.probe(v_path)
        duration = float(probe['format']['duration'])
        video_real_duration = duration # [MỚI] Cập nhật độ dài thật
        
        if duration > 600:  
            task_duration = time.time() - task_start_time
            return {
                "ID": vid_id, "URL": url, "Status": "SKIPPED", 
                "Note": f"Video qua dai ({int(duration/60)}p)", 
                "Violations": "", "Content": "", 
                "Duration": task_duration,
                "VideoLength": video_real_duration # [MỚI]
            }
    except: pass 
    
    # B2: Audio & Transcript
    if not os.path.exists(a_path): extract_audio_robust(v_path, a_path)

    if os.path.exists(a_path):
        if os.path.exists(t_path):
            with open(t_path, 'r', encoding='utf-8') as f: transcript_text = f.read()
        else:
            # [QUAN TRỌNG] Lấy AI từ Pool thay vì dùng Lock
            recognizer = ai_pool.get() 
            try:
                transcript_text = transcribe_smart(recognizer, a_path)
                if not transcript_text: transcript_text = ""
                with open(t_path, 'w', encoding='utf-8') as f: f.write(transcript_text)
            finally:
                ai_pool.put(recognizer) # Trả AI về kho

    # B3: Phân tích
    caption_violations = []
    if desc_text:
        caption_violations = analyze_content(desc_text)
        if detect_type == "KW" and not caption_violations:
            caption_violations.append("Manual_Check")
    
    audio_violations = analyze_content(transcript_text)
    violations = list(set(caption_violations + audio_violations))
    final_text = f"[CAPTION]: {desc_text}\n[AUDIO]: {transcript_text}"

    if violations:
        status = "VI PHAM"
        log_violation(vid_id, url, detect_type, violations, final_text)

    note = ", ".join(violations) if violations else "Clean"
    
    task_duration = time.time() - task_start_time
    
    return {
        "ID": vid_id, "URL": url, "Status": status, "Note": note,
        "Violations": ", ".join(violations), "Content": final_text[:500],
        "Duration": task_duration,
        "VideoLength": video_real_duration # [MỚI] Trả về độ dài video
    }

# ================= MAIN ĐA LUỒNG =================
def main():
    if RESET_DATA_AT_START:
        if os.path.exists(OUTPUT_DIR):
            try:
                shutil.rmtree(OUTPUT_DIR)
                time.sleep(1) 
            except Exception as e:
                print(f"Loi xoa folder: {e}")

    setup_dirs()
    if not os.path.exists(INPUT_FILE):
        print(f"!!! Khong thay file {INPUT_FILE}"); return

    tasks = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            parts = line.strip().split('|')
            if len(parts) >= 3: tasks.append({"url": parts[0], "type": parts[1], "desc": parts[2]})
            else: tasks.append({"url": parts[0], "type": "AI", "desc": ""})

    print(f"\n{'='*110}")
    print(f" BAT DAU QUET {len(tasks)} LINKS | LUONG: {MAX_WORKERS} | RESET MODE: {RESET_DATA_AT_START}")
    # [MỚI] Thêm cột VIDEO vào Header (Giữ nguyên các cột cũ)
    print(f" DANG: [STT/TONG] | {'ID VIDEO':<18} | {'TRANG THAI':<9} | {'GIAY':<6} | {'VIDEO':<6} | {'TB/V':<6} | {'OK':<4} | GHI CHU")
    print(f"{'='*110}")
    
    # [QUAN TRỌNG] Gọi hàm khởi tạo Pool (GPU)
    init_ai_pool() 

    report_data = []
    start_time_global = time.time()
    processed_ok = 0 

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(process_single_task, item, i): item for i, item in enumerate(tasks)}
        
        for i, future in enumerate(as_completed(future_to_url)):
            try:
                result = future.result()
                report_data.append(result)
                
                if result['Status'] != "LOI_TAI":
                    processed_ok += 1
                
                current_process_time = result.get('Duration', 0) # Thời gian xử lý
                video_len = result.get('VideoLength', 0)         # [MỚI] Độ dài video
                
                elapsed_total = time.time() - start_time_global
                processed_count = i + 1
                avg_speed_accumulated = elapsed_total / processed_count
                
                stt = f"[{processed_count}/{len(tasks)}]"
                vid = result['ID']
                stt_text = result['Status']
                note = result['Note']
                
                if stt_text == "VI PHAM": icon = "⚠️ "
                elif stt_text == "LOI_TAI": icon = "❌ "
                elif stt_text == "SKIPPED": icon = "⏩ " 
                else: icon = "✅ "

                with print_lock:
                    # [MỚI] Thêm cột {video_len:5.1f}s vào dòng in
                    print(f"{stt} | {vid:<18} | {icon}{stt_text:<8} | {current_process_time:5.1f}s | {video_len:5.1f}s | {avg_speed_accumulated:4.1f}s | {processed_ok:<4} | {note}")
                    
            except Exception as exc:
                with print_lock:
                    print(f"!!! LOI TAI TASK {i}: {exc}")

    total_time = time.time() - start_time_global
    print(f"{'='*110}")
    print(f" TONG KET: ✅ OK: {success_count}  |  ❌ FAIL: {failure_count}")
    print(f" TONG THOI GIAN: {total_time:.2f}s | TRUNG BINH CHUNG: {total_time/len(tasks):.2f}s/video")
    
    if report_data:
        df = pd.DataFrame(report_data)
        # Drop các cột phụ trước khi xuất Excel để file gọn gàng
        cols_to_drop = ['Duration', 'VideoLength']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        
        df.to_excel(EXCEL_REPORT_FILE, index=False)
        print(f" >> DA XUAT FILE: {EXCEL_REPORT_FILE}")

if __name__ == "__main__":
    main()