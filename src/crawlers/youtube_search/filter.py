import json
import os
import sys
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('youtube_search_filter')

DEFAULT_THRESHOLD = 0.45
INPUT_DIR = 'data/raw/youtube_search'
KEYWORDS_FILE = 'config/keywords/youtube_search.txt'
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'

def load_keywords(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_all_metadata_files(directory):
    if not os.path.exists(directory):
        return []
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('_metadata.json')]

def filter_and_save_links(query_keyword, min_similarity_threshold, input_file, output_file, model_name):
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            video_data = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON file: {input_file}")
            return

    if not video_data:
        logger.warning(f"Empty video list in: {input_file}")
        return

    logger.info(f"Loading model: {model_name}...")
    model = SentenceTransformer(model_name)

    video_texts = [f"{item['title']} {item['description']}" for item in video_data]
    all_texts = [query_keyword] + video_texts

    logger.info(f"Creating embeddings for {len(video_texts)} videos...")
    embeddings = model.encode(all_texts, convert_to_tensor=False)

    query_embedding = embeddings[0].reshape(1, -1)
    video_embeddings = embeddings[1:]

    similarities = cosine_similarity(query_embedding, video_embeddings)[0]

    filtered_links_info = []
    for i, sim in enumerate(similarities):
        if sim >= min_similarity_threshold:
            info = video_data[i].copy()
            info['similarity_score'] = round(float(sim), 4)
            filtered_links_info.append(info)

    filtered_links_info.sort(key=lambda x: x['similarity_score'], reverse=True)

    if filtered_links_info:
        count = len(filtered_links_info)
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in filtered_links_info:
                f.write(item['url'] + "\n")
                
        logger.info(f"Filtered {count}/{len(video_data)} links (threshold={min_similarity_threshold}) -> {output_file}")
    else:
        logger.warning(f"No links found with similarity >= {min_similarity_threshold}")

if __name__ == "__main__":
    metadata_files = get_all_metadata_files(INPUT_DIR)
    
    if not metadata_files:
        logger.warning(f"No metadata files found in {INPUT_DIR}")
    else:
        logger.info(f"Found {len(metadata_files)} metadata files")
        for input_file in metadata_files:
            base_name = os.path.basename(input_file).replace('_metadata.json', '')
            keyword = base_name.replace('_', ' ')
            output_file = os.path.join(INPUT_DIR, f'{base_name}_filtered.txt')
            
            logger.info(f"Filtering: {input_file}")
            filter_and_save_links(
                keyword,
                DEFAULT_THRESHOLD,
                input_file,
                output_file,
                EMBEDDING_MODEL_NAME
            )
