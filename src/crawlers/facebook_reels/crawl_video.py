import os
import gc
import sys
import pandas as pd
import numpy as np
import subprocess
import sherpa_onnx

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('facebook_reels_transcribe')

DEFAULT_VIDEO_DIR = 'data/raw/facebook_reels/videos'
MODEL_DIR = 'models/zipformer'
DEFAULT_OUTPUT_DIR = 'data/raw/facebook_reels'

ai_recognizer = None

def load_ai_model():
    global ai_recognizer
    if ai_recognizer is None:
        logger.info("Loading AI model...")
        ai_recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=os.path.join(MODEL_DIR, "encoder-epoch-20-avg-10.int8.onnx"),
            decoder=os.path.join(MODEL_DIR, "decoder-epoch-20-avg-10.int8.onnx"),
            joiner=os.path.join(MODEL_DIR, "joiner-epoch-20-avg-10.int8.onnx"),
            tokens=os.path.join(MODEL_DIR, "tokens.txt"),
            num_threads=2,
            sample_rate=16000,
            feature_dim=80,
            provider="cpu"
        )
        logger.info("AI model loaded successfully")
    return ai_recognizer

def transcribe_video(file_path):
    recognizer = load_ai_model()
    
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

        samples = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
        
        stream = recognizer.create_stream()
        chunk_size = 16000 * 10
        
        for i in range(0, len(samples), chunk_size):
            chunk = samples[i : i + chunk_size]
            stream.accept_waveform(16000, chunk.tolist())
        
        recognizer.decode_stream(stream)
        text = stream.result.text.strip().lower()
        
        del stream, samples, raw_audio
        gc.collect()
        
        return text
    except Exception as e:
        logger.error(f"Error transcribing {file_path}: {e}")
        return ""

def main(video_dir=None, output_dir=None):
    video_dir = video_dir or DEFAULT_VIDEO_DIR
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    output_excel = os.path.join(output_dir, 'transcripts.xlsx')
    
    if not os.path.exists(video_dir):
        logger.error(f"Video folder not found: {video_dir}")
        return

    video_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
    logger.info(f"Found {len(video_files)} videos in {video_dir}")

    results = []
    success_count = 0
    
    for i, filename in enumerate(video_files):
        file_path = os.path.join(video_dir, filename)
        logger.info(f"[{i+1}/{len(video_files)}] Processing: {filename}")
        
        content = transcribe_video(file_path)
        
        results.append({
            "File": filename,
            "Content": content
        })
        
        if content:
            success_count += 1

        if (i + 1) % 10 == 0:
            os.makedirs(output_dir, exist_ok=True)
            pd.DataFrame(results).to_excel(output_excel, index=False)
            logger.info(f"Backup saved: {i+1} videos...")

    os.makedirs(output_dir, exist_ok=True)
    pd.DataFrame(results).to_excel(output_excel, index=False)
    logger.info(f"Done! Success: {success_count}/{len(video_files)}, Output: {output_excel}")

if __name__ == "__main__":
    main()
