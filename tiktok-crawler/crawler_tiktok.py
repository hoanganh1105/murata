import os
import time
import re
import pandas as pd
import torch
import ffmpeg  # Thư viện xử lý video
import yt_dlp  # Thư viện tải video
from faster_whisper import WhisperModel
from datetime import datetime

# ================= CẤU HÌNH HỆ THỐNG =================
INPUT_FILE = 'input_links_tiktok.txt'
OUTPUT_DIR = 'dataset_tiktok'
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

# ================= KHỞI TẠO AI =================
print("⏳ Đang kiểm tra cấu hình AI...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model_size = "base"
ai_model = None 

def load_ai_model():
    global ai_model
    if ai_model is None:
        print("🚀 Đang load Model Whisper (Chỉ chạy 1 lần)...")
        try:
            ai_model = WhisperModel(model_size, device=device, compute_type="int8")
        except:
            ai_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return ai_model

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

# === HÀM TẢI VIDEO MỚI (CẬP NHẬT LOGIC 15 PHÚT) ===
def download_video_direct(url, save_path):
    print(f"   🌍 Đang xử lý: {url}")
    
    current_folder = os.path.dirname(os.path.abspath(__file__))
    
    # --- BƯỚC 1: KIỂM TRA ĐỘ DÀI VIDEO TRƯỚC ---
    video_duration = 0
    download_format = 'best' # Mặc định là nét nhất
    
    # Cấu hình chỉ lấy info, không tải
    info_opts = {
        'quiet': True, 
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }
    
    try:
        print("      ⏳ Đang kiểm tra metadata...")
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False) # Chỉ lấy thông tin
            video_duration = info.get('duration', 0) # Lấy số giây
            
            # 15 phút = 900 giây
            if video_duration > 300:
                minutes = int(video_duration/60)
                print(f"      🐢 Video dài {minutes} phút (>15p). Chuyển chế độ: TẢI NHANH (Thấp).")
                download_format = 'worst' # Chất lượng thấp nhất
            else:
                print(f"      🐇 Video ngắn. Chuyển chế độ: TẢI NÉT (Best).")
                download_format = 'best'
    except Exception as e:
        print(f"      ⚠️ Không lấy được info (vẫn sẽ tải mặc định Best): {e}")

    # --- BƯỚC 2: TIẾN HÀNH TẢI ---
    ydl_opts = {
        'format': download_format,
        'outtmpl': save_path,         
        'quiet': True,                
        'no_warnings': True,
        'ffmpeg_location': current_folder, 
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.tiktok.com/'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Kiểm tra file sau khi tải
        if os.path.exists(save_path):
            return True
        elif os.path.exists(save_path + ".mp4"): 
            os.rename(save_path + ".mp4", save_path)
            return True
        else:
            return False
    except Exception as e:
        print(f"   ❌ Lỗi yt-dlp: {e}")
        return False

def extract_audio_robust(video_path, audio_path):
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
        a_path = os.path.join(FOLDERS['audio'], f"{vid_id}.mp3")
        t_path = os.path.join(FOLDERS['transcript'], f"{vid_id}.txt")

        # --- LOGIC MỚI: NẾU MODE LÀ KEYWORD THÌ KHÔNG CẦN TẢI VIDEO ---
        final_text = ""
        violations = []
        is_violation = False
        status = "✅ Sạch"

        if detect_type == "KW":
            print("   ⚡ Mode KW: Caption chứa từ khóa -> Bỏ qua tải Video/Whisper.")
            final_text = f"[CAPTION]: {desc_text}"
            violations = analyze_content(desc_text)
            if not violations: violations = ["Keyword match in Title"]
            is_violation = True
        
        else:
            # Chỉ tải video nếu mode KHÔNG PHẢI là KW
            if not os.path.exists(v_path):
                success = download_video_direct(url, v_path)
                if not success:
                    print("   ❌ Không tải được video (Link chết hoặc Private).")
                    report_data.append({"ID": vid_id, "URL": url, "Status": "Lỗi Tải", "Violations": ""})
                    continue
            else:
                print("   ⏩ Video đã có sẵn.")

            print("   🤖 Mode AI: Cần nghe nội dung...")
            if not os.path.exists(a_path): extract_audio_robust(v_path, a_path)
            
            if os.path.exists(a_path):
                if os.path.exists(t_path):
                    with open(t_path, 'r', encoding='utf-8') as f: final_text = f.read()
                else:
                    model = load_ai_model()
                    try:
                        segments, _ = model.transcribe(a_path, beam_size=5)
                        final_text = " ".join([s.text for s in segments]).strip()
                        with open(t_path, 'w', encoding='utf-8') as f: f.write(final_text)
                    except Exception as e: print(f"   ❌ Lỗi Whisper: {e}")

                violations = analyze_content(final_text)
                if violations: is_violation = True
            else:
                print("   ❌ Lỗi: Không có file Audio để xử lý.")

        # 3. KẾT LUẬN
        status = "⚠️ VI PHẠM" if is_violation else "✅ Sạch"
        
        if is_violation:
            print(f"   🚨 VI PHẠM TÌM THẤY: {', '.join(violations)}")
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
            print(f"✅ Đã xuất báo cáo tổng hợp: {EXCEL_REPORT_FILE}")
            print(f"✅ Đã xuất danh sách vi phạm riêng: {VIOLATION_LOG_FILE}")
        except PermissionError:
            print("❌ Lỗi: Bạn đang mở file Excel. Hãy tắt file Excel đi để tool ghi dữ liệu!")

if __name__ == "__main__":
    main()