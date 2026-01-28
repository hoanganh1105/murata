import os
import time
import sys
import requests
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('facebook_ads_crawler')

try:
    from moviepy.editor import VideoFileClip
except (ImportError, ModuleNotFoundError):
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
    except:
        logger.error("MoviePy not installed. Run: pip install moviepy==1.0.3")

KEYWORDS_FILE = 'config/keywords/facebook_reels.txt'
DEFAULT_SCROLL_COUNT = 5
DEFAULT_OUTPUT_DIR = "data/ads/input"
DEFAULT_MAX_WORKERS = 6

def load_keywords(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def download_and_convert(v_url, count, output_dir):
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        video_path = os.path.join(output_dir, f"ad_{count}.mp4")
        audio_path = os.path.join(output_dir, f"ad_{count}.mp3")
        
        logger.debug(f"Downloading video {count}...")
        clean_url = v_url.replace("&amp;", "&")
        with requests.get(clean_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(video_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
        
        clip = VideoFileClip(video_path)
        if clip.audio:
            clip.audio.write_audiofile(audio_path, codec='mp3', logger=None)
            logger.info(f"Done: ad_{count}.mp4 & ad_{count}.mp3")
        else:
            logger.warning(f"Video {count} has no audio.")
        
        clip.close()

    except Exception as e:
        logger.error(f"Error processing video {count}: {e}")

def start_crawl(keyword=None, scroll_count=None, output_dir=None, max_workers=None):
    if keyword is None:
        raise ValueError("keyword is required")
    scroll_count = scroll_count or DEFAULT_SCROLL_COUNT
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    max_workers = max_workers or DEFAULT_MAX_WORKERS
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)
    
    q = urllib.parse.quote(keyword)
    url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&q={q}&country=VN&media_type=video"

    seen_videos = set()
    count = 0

    try:
        logger.info(f"Starting browser... Keyword: {keyword}")
        driver.get(url)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(scroll_count):
                try:
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                except:
                    logger.debug("No new videos found, scrolling...")

                videos = driver.find_elements(By.TAG_NAME, "video")
                
                for v_tag in videos:
                    try:
                        v_url = v_tag.get_attribute("src")
                        if v_url and v_url not in seen_videos and not v_url.startswith("blob:"):
                            seen_videos.add(v_url)
                            count += 1
                            executor.submit(download_and_convert, v_url, count, output_dir)
                    except:
                        continue

                driver.execute_script("window.scrollBy(0, 2500);")
                logger.debug(f"Scrolled {i+1}/{scroll_count}")
                time.sleep(4)

    finally:
        driver.quit()
        logger.info(f"Browser closed. Found {count} videos for keyword: {keyword}")

if __name__ == "__main__":
    keywords = load_keywords(KEYWORDS_FILE)
    if not keywords:
        logger.warning(f"No keywords found in {KEYWORDS_FILE}")
    else:
        logger.info(f"Loaded {len(keywords)} keywords from {KEYWORDS_FILE}")
        for i, kw in enumerate(keywords):
            logger.info(f"[{i+1}/{len(keywords)}] Crawling: {kw}")
            output_dir = os.path.join(DEFAULT_OUTPUT_DIR, kw.replace(' ', '_'))
            
            start_time = time.time()
            start_crawl(keyword=kw, output_dir=output_dir)
            if os.path.exists(output_dir):
                file_count = len(os.listdir(output_dir))//2
                logger.info(f"Total files: {file_count}")
            logger.info(f"Time: {time.time() - start_time:.2f} seconds")
