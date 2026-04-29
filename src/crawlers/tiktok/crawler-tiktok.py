import os
import time
import re
import sys
import pandas as pd
import ffmpeg
import yt_dlp
import soundfile as sf
import sherpa_onnx
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('tiktok_crawler')

INPUT_DIR = 'data/raw/tiktok'
OUTPUT_DIR = 'data/raw/tiktok'
MODEL_DIR = 'models/zipformer'
COOKIE_FILE = 'config/cookies/tiktok.txt'

def get_folders(output_dir):
    return {
        'video': os.path.join(output_dir, 'video'),
        'audio': os.path.join(output_dir, 'audio'),
        'transcript': os.path.join(output_dir, 'transcripts')
    }

def get_latest_input_file(directory):
    if not os.path.exists(directory):
        return None
    txt_files = [f for f in os.listdir(directory) if f.endswith('.txt') and 'input' in f.lower()]
    if not txt_files:
        txt_files = [f for f in os.listdir(directory) if f.endswith('.txt')]
    if not txt_files:
        return None
    txt_files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
    return os.path.join(directory, txt_files[0])

FOLDERS = get_folders(OUTPUT_DIR)
EXCEL_REPORT_FILE = os.path.join(OUTPUT_DIR, 'report.xlsx')

MAX_WORKERS = 3
ai_lock = threading.Lock()
ai_recognizer = None

def load_ai_model():
    global ai_recognizer
    if ai_recognizer is None:
        encoder_file = os.path.join(MODEL_DIR, "encoder-epoch-20-avg-10.int8.onnx")
        decoder_file = os.path.join(MODEL_DIR, "decoder-epoch-20-avg-10.int8.onnx")
        joiner_file = os.path.join(MODEL_DIR, "joiner-epoch-20-avg-10.int8.onnx")
        tokens_file = os.path.join(MODEL_DIR, "tokens.txt")

        if not all(os.path.exists(f) for f in [encoder_file, decoder_file, joiner_file, tokens_file]):
            logger.error(f"Missing model files in '{MODEL_DIR}'")
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
            logger.info("AI model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise e
        
    return ai_recognizer

def setup_dirs():
    for p in FOLDERS.values():
        if not os.path.exists(p):
            os.makedirs(p)

def download_video_direct(url, save_path):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'http_headers': headers,
            'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
            'outtmpl': save_path,
            'ignoreerrors': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(save_path):
            return True
        if os.path.exists(save_path + ".mp4"):
            os.rename(save_path + ".mp4", save_path)
            return True
    except Exception:
        pass

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
                with open(save_path, 'wb') as f:
                    f.write(video_bytes)
                return True
    except Exception:
        pass
    return False

def extract_audio(video_path, audio_path):
    try:
        ffmpeg.input(video_path).output(audio_path, ac=1, ar='16k').overwrite_output().run(quiet=True)
        return True
    except:
        return False

def transcribe(recognizer, audio_path):
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
            if len(chunk) < sample_rate:
                continue
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, chunk)
            recognizer.decode_stream(stream)
            text_segment = stream.result.text.strip()
            if text_segment:
                full_text_parts.append(text_segment)
            del stream
            del chunk
        return " ".join(full_text_parts)
    except Exception:
        return ""

def process_single_task(item, index, total):
    url = item['url']
    desc_text = item.get('desc', '')
    
    try:
        vid_id = re.findall(r'/video/(\d+)', url)[0]
    except:
        vid_id = str(int(time.time())) + f"_{index}"

    logger.info(f"[{index+1}/{total}] Processing: {url}")

    v_path = os.path.join(FOLDERS['video'], f"{vid_id}.mp4")
    a_path = os.path.join(FOLDERS['audio'], f"{vid_id}.wav")
    t_path = os.path.join(FOLDERS['transcript'], f"{vid_id}.txt")

    transcript_text = ""

    if not os.path.exists(v_path):
        success = download_video_direct(url, v_path)
        if not success:
            return {"ID": vid_id, "URL": url, "Status": "Download Error", "Content": ""}
    
    if not os.path.exists(a_path) and os.path.exists(v_path):
        extract_audio(v_path, a_path)

    if os.path.exists(a_path):
        if os.path.exists(t_path):
            with open(t_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
        else:
            with ai_lock:
                recognizer = load_ai_model()
                transcript_text = transcribe(recognizer, a_path)
                if not transcript_text:
                    transcript_text = "[No speech detected]"
                with open(t_path, 'w', encoding='utf-8') as f:
                    f.write(transcript_text)

    final_text = f"[CAPTION]: {desc_text}\n[AUDIO]: {transcript_text}"

    return {
        "ID": vid_id,
        "URL": url,
        "Status": "Done",
        "Content": final_text[:500]
    }

def main(input_file=None):
    setup_dirs()
    
    if input_file is None:
        input_file = get_latest_input_file(INPUT_DIR)
    
    if input_file is None or not os.path.exists(input_file):
        logger.error(f"No input file found in {INPUT_DIR}")
        return

    logger.info(f"Using input file: {input_file}")

    tasks = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.strip().split('|')
            if len(parts) >= 3:
                tasks.append({"url": parts[0], "type": parts[1], "desc": parts[2]})
            else:
                tasks.append({"url": parts[0], "type": "AI", "desc": ""})

    logger.info(f"Found {len(tasks)} links. Starting with {MAX_WORKERS} workers...")
    
    load_ai_model()
    
    report_data = []
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(process_single_task, item, i, len(tasks)): item for i, item in enumerate(tasks)}
        
        for i, future in enumerate(as_completed(future_to_url)):
            try:
                result = future.result()
                if result:
                    report_data.append(result)
                    if result['Status'] == 'Done':
                        success_count += 1
                    else:
                        error_count += 1
                    logger.debug(f"Done: {result['ID']} | Status: {result['Status']}")
            except Exception as exc:
                logger.error(f"Task error: {exc}")
                error_count += 1

    logger.info(f"Completed: Success={success_count}, Errors={error_count}")

    if report_data:
        df = pd.DataFrame(report_data)
        try:
            df.to_excel(EXCEL_REPORT_FILE, index=False)
            logger.info(f"Report saved to: {EXCEL_REPORT_FILE}")
        except PermissionError:
            logger.error("Cannot save report: Close Excel file first!")

if __name__ == "__main__":
    main()
