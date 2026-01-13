import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os

# ==============================================================================
#                      CẤU HÌNH VÀ THAM SỐ
# ==============================================================================
# Keyword truy vấn
QUERY_KEYWORD = "cancer" 

# Ngưỡng tương đồng tối thiểu để chấp nhận link (từ 0.0 đến 1.0)
MIN_SIMILARITY_THRESHOLD = 0.45 

# File đầu vào (chứa link, title, description)
INPUT_METADATA_FILE = 'Embedding/video_metadata.json' 

# ⚠️ FILE ĐẦU RA SẼ CHỈ CHỨA CÁC LINK (DẠNG .txt)
OUTPUT_FILTERED_LINKS_FILE = 'Embedding/filtered_links_for_download.txt' 

# Tên mô hình Embedding nhẹ và đa ngôn ngữ
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2' 

# ==============================================================================
#                      HÀM LỌC VÀ GHI FILE
# ==============================================================================

def filter_and_save_links(query_keyword, min_similarity_threshold, input_file, output_file, model_name):
    """
    Đọc metadata, lọc bằng embedding và lưu CHỈ CÁC LINK phù hợp vào file TXT mới.
    """
    if not os.path.exists(input_file):
        print(f"❌ Lỗi: Không tìm thấy file đầu vào '{input_file}'. Vui lòng kiểm tra đường dẫn hoặc chạy bước crawl metadata.")
        return

    # 1. Đọc dữ liệu từ file JSON
    print(f"📥 Đang đọc dữ liệu từ file '{input_file}'...")
    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            video_data = json.load(f)
        except json.JSONDecodeError:
            print("❌ Lỗi: File JSON không hợp lệ. Kiểm tra định dạng file.")
            return

    if not video_data:
        print("❌ Danh sách video trống. Kết thúc lọc.")
        return

    # 2. Chuẩn bị dữ liệu và khởi tạo Model
    print(f"\n⚙️ Khởi tạo Embedding Model: {model_name}...")
    model = SentenceTransformer(model_name)

    # Kết hợp Title và Description để tạo chuỗi ngữ cảnh đầy đủ
    video_texts = [f"{item['title']} {item['description']}" for item in video_data]
    all_texts = [query_keyword] + video_texts

    # 3. Tạo Embeddings (Vectors) 
    print(f"Đang tạo Embeddings cho {len(video_texts)} mục metadata...")
    embeddings = model.encode(all_texts, convert_to_tensor=False)

    # Tách riêng embedding của keyword và video
    query_embedding = embeddings[0].reshape(1, -1) 
    video_embeddings = embeddings[1:]

    # 4. Tính Cosine Similarity 
    print("Đang tính Cosine Similarity và lọc...")
    # 
    similarities = cosine_similarity(query_embedding, video_embeddings)[0]

    # 5. Lọc và sắp xếp kết quả
    filtered_links_info = []
    for i, sim in enumerate(similarities):
        if sim >= min_similarity_threshold:
            # Lưu thông tin video cùng điểm tương đồng
            info = video_data[i].copy()
            # Vẫn tính và lưu score để sắp xếp
            info['similarity_score'] = round(float(sim), 4) 
            filtered_links_info.append(info)

    # Sắp xếp kết quả theo điểm tương đồng giảm dần
    filtered_links_info.sort(key=lambda x: x['similarity_score'], reverse=True)

    # 6. Ghi CHỈ CÁC LINK ĐÃ LỌC vào file TXT mới
    if filtered_links_info:
        count = len(filtered_links_info)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            
            
            # Chỉ ghi URL
            for item in filtered_links_info:
                f.write(item['url'] + "\n")
                
        print(f"\n✅ Hoàn tất. Đã lọc và lưu {count} links vào file: **{output_file}**")
        print("👉 File này đã sẵn sàng để làm đầu vào cho công cụ tải video như yt-dlp.")
    else:
        print(f"\n❌ Không tìm thấy link nào phù hợp với từ khóa '{query_keyword}' (Điểm < {min_similarity_threshold}).")

# ==============================================================================
#                             CHẠY CHÍNH
# ==============================================================================

if __name__ == "__main__":
    
    # Sử dụng biến OUTPUT_FILTERED_LINKS_FILE đã đổi tên
    filter_and_save_links(
        QUERY_KEYWORD, 
        MIN_SIMILARITY_THRESHOLD, 
        INPUT_METADATA_FILE, 
        OUTPUT_FILTERED_LINKS_FILE, 
        EMBEDDING_MODEL_NAME
    )