import requests
import isodate
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('youtube_short_api')

API_KEY = "AIzaSyCF6gy-ld1cit7FZUUmOCWFttT8pjlS1Jk"
BASE_URL = "https://www.googleapis.com/youtube/v3/"
YOUTUBE_URL_BASE = "https://www.youtube.com/watch?v="

OUTPUT_DIR = "data/raw/youtube_short"
KEYWORDS_FILE = "config/keywords/youtube_short.txt"

def load_keywords(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_50_videos(query):
    search_url = f"{BASE_URL}search"
    search_params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'videoDuration': 'short',
        'maxResults': 100,
        'key': API_KEY
    }
    
    try:
        res = requests.get(search_url, params=search_params)
        res.raise_for_status()
        search_data = res.json()
        
        items = search_data.get('items', [])
        video_ids = [i['id']['videoId'] for i in items if i['id']['kind'] == 'youtube#video']
        
        if not video_ids:
            return []

        details_url = f"{BASE_URL}videos"
        detail_params = {
            'part': 'snippet,contentDetails',
            'id': ",".join(video_ids),
            'key': API_KEY
        }
        
        det_res = requests.get(details_url, params=detail_params)
        det_res.raise_for_status()
        detail_data = det_res.json()

        final_list = []
        for item in detail_data.get('items', []):
            duration_iso = item['contentDetails']['duration']
            total_seconds = isodate.parse_duration(duration_iso).total_seconds()
            
            final_list.append({
                'video_id': item['id'],
                'video_title': item['snippet']['title'],
                'video_url': YOUTUBE_URL_BASE + item['id'],
                'duration_seconds': total_seconds
            })
            
        return final_list

    except Exception as e:
        logger.error(f"Error searching '{query}': {e}")
        return []

def save_json(data, query):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    filename = os.path.join(OUTPUT_DIR, f"{query.replace(' ', '_')}_results.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"Saved {len(data)} videos to: {filename}")

if __name__ == "__main__":
    keywords = load_keywords(KEYWORDS_FILE)
    if not keywords:
        logger.warning(f"No keywords found in {KEYWORDS_FILE}")
    else:
        logger.info(f"Loaded {len(keywords)} keywords from {KEYWORDS_FILE}")
        for i, kw in enumerate(keywords):
            logger.info(f"[{i+1}/{len(keywords)}] Searching: {kw}")
            results = get_50_videos(kw)
            if results:
                save_json(results, kw)
            else:
                logger.warning(f"No results for keyword: {kw}")
