import re
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('facebook_reels_filter')

DEFAULT_INPUT_DIR = 'data/raw/facebook_reels'

def get_latest_links_file(directory):
    if not os.path.exists(directory):
        return None
    txt_files = [f for f in os.listdir(directory) if f.endswith('.txt') and 'raw' in f.lower()]
    if not txt_files:
        txt_files = [f for f in os.listdir(directory) if f.endswith('.txt')]
    if not txt_files:
        return None
    txt_files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
    return os.path.join(directory, txt_files[0])

def filter_clean_reels(input_file, output_file=None):
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return
    
    if output_file is None:
        base_dir = os.path.dirname(input_file)
        output_file = os.path.join(base_dir, 'links_clean.txt')
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    reel_ids = re.findall(r'/reel(?:s)?/([0-9]+)', content)

    unique_ids = list(dict.fromkeys(reel_ids))

    clean_links = [f"https://m.facebook.com/reel/{rid}/" for rid in unique_ids]

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for link in clean_links:
            f.write(link + '\n')

    logger.info(f"Filtered {len(clean_links)} reel links -> {output_file}")

if __name__ == "__main__":
    input_file = get_latest_links_file(DEFAULT_INPUT_DIR)
    if input_file is None:
        logger.warning(f"No links file found in {DEFAULT_INPUT_DIR}")
    else:
        logger.info(f"Using input file: {input_file}")
        filter_clean_reels(input_file)
