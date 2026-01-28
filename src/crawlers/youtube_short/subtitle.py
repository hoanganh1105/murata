import yt_dlp
import os
import json
import time
import random
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('youtube_short_download')

INPUT_DIR = 'data/raw/youtube_short'
OUTPUT_DIR = 'data/raw/youtube_short/videos'
COOKIE_FILE = 'config/cookies/youtube.txt'

def get_latest_json_file(directory):
    if not os.path.exists(directory):
        return None
    json_files = [f for f in os.listdir(directory) if f.endswith('_results.json')]
    if not json_files:
        return None
    json_files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
    return os.path.join(directory, json_files[0])

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def clean_sub(vtt_path):
    if not os.path.exists(vtt_path): 
        return ""
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        clean = re.sub(r'WEBVTT|Kind:.*|Language:.*|Style:.*|##.*', '', content)
        clean = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3} --> \d{2}:\d{2}:\d{2}[.,]\d{3}', '', clean)
        clean = re.sub(r'align:[^\s]+|position:[^\s]+|size:[^\s]+|<[^>]+>', '', clean)
        
        lines = clean.split('\n')
        final_text = []
        last_line = ""
        for line in lines:
            line = line.strip()
            if not line or line.isdigit(): 
                continue
            words = line.split()
            unique_words = []
            for w in words:
                if not unique_words or w != unique_words[-1]: 
                    unique_words.append(w)
            line = " ".join(unique_words)
            if line != last_line:
                final_text.append(line)
                last_line = line
        return " ".join(final_text)
    except: 
        return ""

def download_videos(input_file=None):
    if input_file is None:
        input_file = get_latest_json_file(INPUT_DIR)
    
    if input_file is None or not os.path.exists(input_file):
        logger.error(f"No JSON file found in: {INPUT_DIR}")
        return

    logger.info(f"Using input file: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    links = [item.get('video_url') for item in data if item.get('video_url')][:50]
    
    ydl_opts = {
        'format': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best',
        'outtmpl': f'{OUTPUT_DIR}/%(id)s.%(ext)s',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'sub_langs': ['en.*'],
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }

    logger.info(f"Starting download {len(links)} videos...")
    success_count = 0
    error_count = 0

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(links):
            logger.info(f"[{i+1}/{len(links)}] Downloading: {url}")
            try:
                info = ydl.extract_info(url, download=True)
                if info:
                    v_id = info.get('id')
                    for file in os.listdir(OUTPUT_DIR):
                        if v_id in file and file.endswith(".vtt"):
                            vtt_p = os.path.join(OUTPUT_DIR, file)
                            txt_content = clean_sub(vtt_p)
                            if txt_content:
                                with open(os.path.join(OUTPUT_DIR, f"{v_id}.txt"), 'w', encoding='utf-8') as ft:
                                    ft.write(txt_content)
                            os.remove(vtt_p)
                    success_count += 1
                
                time.sleep(random.uniform(5, 10))
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                error_count += 1

    logger.info(f"Done! Success: {success_count}, Errors: {error_count}, Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    download_videos()
