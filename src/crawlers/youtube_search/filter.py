import json
import os
import sys
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Setup Path & Logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import setup_logger

logger = setup_logger('youtube_search_filter')

DEFAULT_THRESHOLD = 0.3
INPUT_DIR = 'data/raw/youtube_short/vay_nen_1769743247.json'
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'

def get_all_metadata_files(directory):
    if not os.path.exists(directory):
        return []
    # Lấy các file metadata hoặc file kết quả crawl
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('_metadata.json') or f.endswith('_results.json')]

def filter_and_save_links(query_keyword, min_similarity_threshold, input_file, output_file, model_name):
    if not os.path.exists(input_file):
        logger.error(f"❌ Không tìm thấy file: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            video_data = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"❌ File JSON lỗi: {input_file}")
            return

    if not video_data:
        logger.warning(f"⚠️ File rỗng: {input_file}")
        return

    # Khởi tạo Model
    logger.info(f"🔄 Đang nạp model: {model_name}...")
    model = SentenceTransformer(model_name)

    # Trích xuất text để tính toán (Title + Description) 
    # Dùng .get() để tránh lỗi nếu thiếu key
    video_texts = []
    valid_videos = []

    for item in video_data:
        title = item.get('title', '')
        desc = item.get('description', '') or ''
        # Lấy link từ 'video_url' (định dạng của yt-dlp) hoặc 'url'
        url = item.get('video_url') or item.get('url')
        
        if url:
            video_texts.append(f"{title} {desc}")
            valid_videos.append(item)

    if not video_texts:
        logger.warning("⚠️ Không tìm thấy link video nào trong dữ liệu.")
        return

    # Tính toán Similarity
    all_texts = [query_keyword] + video_texts
    logger.info(f"🧠 Đang tạo embeddings cho {len(video_texts)} videos...")
    embeddings = model.encode(all_texts, convert_to_tensor=False)

    query_embedding = embeddings[0].reshape(1, -1)
    video_embeddings = embeddings[1:]

    similarities = cosine_similarity(query_embedding, video_embeddings)[0]

    # Lọc theo ngưỡng
    filtered_results = []
    for i, sim in enumerate(similarities):
        if sim >= min_similarity_threshold:
            info = valid_videos[i].copy()
            # Đảm bảo lấy đúng key video_url
            info['link'] = info.get('video_url') or info.get('url')
            info['similarity_score'] = round(float(sim), 4)
            filtered_results.append(info)

    # Sắp xếp theo độ liên quan giảm dần
    filtered_results.sort(key=lambda x: x['similarity_score'], reverse=True)

    if filtered_results:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in filtered_results:
                f.write(item['link'] + "\n")
                
        logger.info(f"✅ Đã lọc {len(filtered_results)}/{len(video_data)} link -> {output_file}")
    else:
        logger.warning(f"⚠️ Không có video nào đạt ngưỡng tương đồng >= {min_similarity_threshold}")

if __name__ == "__main__":
    metadata_files = get_all_metadata_files(INPUT_DIR)
    
    if not metadata_files:
        logger.warning(f"❌ Không thấy file metadata nào trong {INPUT_DIR}")
    else:
        logger.info(f"📂 Tìm thấy {len(metadata_files)} file dữ liệu")
        for input_file in metadata_files:
            # Tạo keyword từ tên file (Ví dụ: "cach_lam_com_tam_metadata.json" -> "cach lam com tam")
            base_name = os.path.basename(input_file).replace('_metadata.json', '').replace('_results.json', '')
            keyword = base_name.replace('_', ' ')
            output_file = os.path.join(INPUT_DIR, f'{base_name}_filtered.txt')
            
            logger.info(f"🔍 Đang lọc file: {os.path.basename(input_file)} với từ khóa: '{keyword}'")
            filter_and_save_links(
                keyword,
                DEFAULT_THRESHOLD,
                input_file,
                output_file,
                EMBEDDING_MODEL_NAME
            )