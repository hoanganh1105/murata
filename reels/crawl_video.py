import os
import gc
import re
import time
import pandas as pd
import numpy as np
import subprocess
import sherpa_onnx
import threading
from datetime import datetime

# ================= CẤU HÌNH =================
VIDEO_DIR = 'dataset_reels_final/videos'
MODEL_DIR = 'tiktok-crawler/model_zipformer'
OUTPUT_EXCEL = 'dataset_reels_final/Ket_Qua_AI_Text.xlsx'

# TỪ KHÓA VI PHẠM
VIOLATION_KEYWORDS = [
    "cam kết 100%", "trị dứt điểm", "hoàn tiền", "khỏi ngay", 
    "nhà tôi ba đời", "điều trị tận gốc", "thần dược", "sạch nám", 
    "vẩy nến", "hết hẳn", "không tái phát", "đông y"
]

# ================= KHỞI TẠO AI (SINGLETON) =================
ai_recognizer = None

def load_ai_model():
    global ai_recognizer
    if ai_recognizer is None:
        print("🧠 Đang nạp Model Zipformer (Cấu hình tiết kiệm RAM)...")
        ai_recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=os.path.join(MODEL_DIR, "encoder-epoch-20-avg-10.int8.onnx"),
            decoder=os.path.join(MODEL_DIR, "decoder-epoch-20-avg-10.int8.onnx"),
            joiner=os.path.join(MODEL_DIR, "joiner-epoch-20-avg-10.int8.onnx"),
            tokens=os.path.join(MODEL_DIR, "tokens.txt"),
            num_threads=2, # Giữ 2 threads để máy không bị đứng khi AI chạy
            sample_rate=16000,
            feature_dim=80,
            provider="cpu"
        )
    return ai_recognizer

# ================= XỬ LÝ ÂM THANH CHUNKING =================
def transcribe_video(file_path):
    recognizer = load_ai_model()
    
    # Dùng FFmpeg bốc Audio ra (Ép về 16kHz đơn kênh)
    cmd = [
        'ffmpeg', '-threads', '1', '-i', file_path, 
        '-f', 's16le', '-acodec', 'pcm_s16le', 
        '-ac', '1', '-ar', '16000', '-'
    ]
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw_audio, _ = proc.communicate()
        
        if not raw_audio:
            return ""

        # Chuyển đổi sang mảng float32
        samples = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Tạo stream và nạp dữ liệu theo CHUNK để tránh OOM
        stream = recognizer.create_stream()
        chunk_size = 16000 * 10 # Mỗi lần nạp 10 giây âm thanh
        
        for i in range(0, len(samples), chunk_size):
            chunk = samples[i : i + chunk_size]
            stream.accept_waveform(16000, chunk.tolist())
        
        recognizer.decode_stream(stream)
        text = stream.result.text.strip().lower()
        
        # Giải phóng bộ nhớ ngay lập tức
        del stream, samples, raw_audio
        gc.collect()
        
        return text
    except Exception as e:
        print(f"❌ Lỗi AI tại file {file_path}: {e}")
        return ""

# ================= HÀM CHÍNH =================
def main():
    if not os.path.exists(VIDEO_DIR):
        print(f"❌ Folder video '{VIDEO_DIR}' không tồn tại!")
        return

    # Lấy danh sách video trong folder
    video_files = [f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')]
    print(f"📂 Tìm thấy {len(video_files)} video. Bắt đầu quét text...")

    results = []
    
    for i, filename in enumerate(video_files):
        file_path = os.path.join(VIDEO_DIR, filename)
        print(f"🎙️ [{i+1}/{len(video_files)}] Đang nghe: {filename}")
        
        # Gọi AI nghe
        content = transcribe_video(file_path)
        
        # Kiểm tra vi phạm
        violations = [kw for kw in VIOLATION_KEYWORDS if kw in content]
        status = "⚠️ VI PHẠM" if violations else "✅ SẠCH"
        
        results.append({
            "File": filename,
            "Trạng Thái": status,
            "Vi Phạm": ", ".join(violations),
            "Nội Dung": content
        })
        
        # Log nhanh ra màn hình
        if violations:
            print(f"   🚨 Phát hiện: {', '.join(violations)}")

        # Lưu dự phòng mỗi 10 video
        if (i + 1) % 10 == 0:
            pd.DataFrame(results).to_excel(OUTPUT_EXCEL, index=False)
            print(f"💾 Đã lưu dự phòng {i+1} video...")

    # Lưu kết quả cuối cùng
    pd.DataFrame(results).to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✨ HOÀN THÀNH! Kết quả lưu tại: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()