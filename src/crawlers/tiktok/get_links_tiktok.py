from DrissionPage import ChromiumPage, ChromiumOptions
from sentence_transformers import SentenceTransformer, util
import time
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('tiktok_links')

KEYWORDS_FILE = 'config/keywords/tiktok.txt'
DEFAULT_CONTEXT = "Video quang cao thuoc, thuc pham chuc nang, cam ket tri benh, ban hang online, dong y, my pham"
DEFAULT_MAX_LINKS = 3
OUTPUT_DIR = 'data/raw/tiktok'
DEFAULT_THRESHOLD = 0.22

def load_keywords(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def clean_tiktok_text(raw_text):
    text = re.sub(r'(created by|with).*$', '', raw_text, flags=re.IGNORECASE)
    text = text.replace('\n', ' ').replace('|', ' ').strip()
    return text

def init_output_file(output_file):
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if os.path.exists(output_file):
        choice = input("File exists. Delete and start fresh? (y/n): ").lower()
        if choice == 'y':
            open(output_file, 'w').close()

def get_tiktok_links(keywords_list=None, context_desc=None, max_links=None, threshold=None, output_file=None):
    keywords_list = keywords_list or load_keywords(KEYWORDS_FILE)
    context_desc = context_desc or DEFAULT_CONTEXT
    max_links = max_links or DEFAULT_MAX_LINKS
    threshold = threshold or DEFAULT_THRESHOLD
    output_file = output_file or os.path.join(OUTPUT_DIR, 'input_links.txt')
    
    logger.info("Loading AI model...")
    model = SentenceTransformer('keepitreal/vietnamese-sbert')
    target_embedding = model.encode(context_desc, convert_to_tensor=True)
    logger.info(f"Processing {len(keywords_list)} keywords")

    co = ChromiumOptions()
    co.set_argument('--mute-audio')
    current_folder = os.path.dirname(os.path.abspath(__file__))
    co.set_user_data_path(os.path.join(current_folder, 'User_Data_TikTok'))
    
    page = ChromiumPage(co)
    
    try:
        for kw_index, keyword in enumerate(keywords_list):
            logger.info(f"Keyword [{kw_index+1}/{len(keywords_list)}]: '{keyword}'")
            
            url = f"https://www.tiktok.com/search?q={keyword}"
            page.get(url)
            
            if "Login" in page.title:
                input("Please login manually, then press Enter...")
            else:
                time.sleep(3)

            found_links_count = 0
            found_urls_in_session = set()
            retry_scroll = 0
            
            while found_links_count < max_links:
                video_elements = page.eles('tag:a@@href:video')
                
                for ele in video_elements:
                    link = ele.attr('href')
                    
                    if not link or "/video/" not in link or link in found_urls_in_session:
                        continue
                        
                    img_alt = ele.ele('tag:img').attr('alt') if ele.ele('tag:img') else ""
                    raw_text = f"{img_alt} {ele.text}".strip()
                    clean_text = clean_tiktok_text(raw_text)
                    
                    if len(clean_text) < 5:
                        continue

                    should_save = False
                    detect_type = "UNKNOWN"

                    if keyword.lower() in clean_text.lower():
                        should_save = True
                        detect_type = "KW"
                    else:
                        cand_embedding = model.encode(clean_text, convert_to_tensor=True)
                        score = util.cos_sim(target_embedding, cand_embedding).item()
                        if score >= threshold:
                            should_save = True
                            detect_type = "AI"

                    if should_save:
                        with open(output_file, 'a', encoding='utf-8') as f:
                             f.write(f"{link}|{detect_type}|{clean_text}\n")
                        found_urls_in_session.add(link)
                        found_links_count += 1
                        
                    if found_links_count >= max_links:
                        break
                
                if found_links_count >= max_links:
                    break

                logger.debug(f"Found: {found_links_count}/{max_links}. Scrolling...")
                prev_height = page.run_js('return document.body.scrollHeight')
                page.scroll.to_bottom()
                time.sleep(3)
                curr_height = page.run_js('return document.body.scrollHeight')
                
                if prev_height == curr_height:
                    retry_scroll += 1
                    if retry_scroll >= 3:
                        break
                else:
                    retry_scroll = 0
            
            logger.info(f"Completed keyword '{keyword}'. Found {found_links_count} links.")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        page.quit()
    
    logger.info(f"Done! Links saved to '{output_file}'")

if __name__ == "__main__":
    output_file = os.path.join(OUTPUT_DIR, 'input_links.txt')
    init_output_file(output_file)
    get_tiktok_links(output_file=output_file)
