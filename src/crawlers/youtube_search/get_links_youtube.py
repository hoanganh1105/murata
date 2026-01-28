import yt_dlp
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('youtube_search')

DEFAULT_MAX_VIDEOS = 20
OUTPUT_DIR = "data/raw/youtube_search"
KEYWORDS_FILE = "config/keywords/youtube_search.txt"

def load_keywords(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_youtube_links(query, max_count):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
    }

    if "youtube.com" in query or "youtu.be" in query:
        search_query = query
        ydl_opts['playlistend'] = max_count
    else:
        search_query = f"ytsearch{max_count}:{query}"

    found_links = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
            
            if 'entries' in result:
                for entry in result['entries']:
                    if entry and 'id' in entry:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        found_links.append(video_url)
            elif 'webpage_url' in result:
                 found_links.append(result['webpage_url'])
    except Exception as e:
        logger.error(f"Error searching '{query}': {e}")

    return found_links

def get_metadata_from_links(links):
    metadata_list = []

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': False,
        'force_generic_extractor': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(links):
            logger.debug(f"Processing {i+1}/{len(links)}: {url}")
            try:
                info = ydl.extract_info(url, download=False)
                metadata_list.append({
                    "url": url,
                    "title": info.get('title', 'N/A'),
                    "description": info.get('description', 'N/A'),
                    "uploader": info.get('uploader', 'N/A')
                })
            except Exception as e:
                metadata_list.append({
                    "url": url,
                    "title": "ERROR",
                    "description": str(e),
                    "uploader": "N/A"
                })

    return metadata_list

def process_keyword(keyword, max_videos):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    output_links = os.path.join(OUTPUT_DIR, f'{keyword.replace(" ", "_")}_links.txt')
    output_metadata = os.path.join(OUTPUT_DIR, f'{keyword.replace(" ", "_")}_metadata.json')
    
    raw_links = get_youtube_links(keyword, max_videos)
    
    if not raw_links:
        logger.warning(f"No videos found for keyword: {keyword}")
    else:
        final_metadata = get_metadata_from_links(raw_links)
        
        with open(output_links, 'w', encoding='utf-8') as f:
            for item in final_metadata:
                f.write(item['url'] + "\n")
        logger.info(f"Saved {len(final_metadata)} links to '{output_links}'")
        
        with open(output_metadata, 'w', encoding='utf-8') as f:
            json.dump(final_metadata, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved metadata to '{output_metadata}'")

if __name__ == "__main__":
    keywords = load_keywords(KEYWORDS_FILE)
    if not keywords:
        logger.warning(f"No keywords found in {KEYWORDS_FILE}")
    else:
        logger.info(f"Loaded {len(keywords)} keywords from {KEYWORDS_FILE}")
        for i, kw in enumerate(keywords):
            logger.info(f"[{i+1}/{len(keywords)}] Processing: {kw}")
            process_keyword(kw, DEFAULT_MAX_VIDEOS)
