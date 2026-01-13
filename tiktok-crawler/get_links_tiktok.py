from DrissionPage import ChromiumPage, ChromiumOptions
from sentence_transformers import SentenceTransformer, util
import time
import os
import re

# ================= CẤU HÌNH HỆ THỐNG =================
KEYWORDS_LIST = [
    "trị dứt điểm",
    "nhà tôi ba đời",
    "cam kết 100%",
    "thần dược trị bệnh",
    "sạch nám tàn nhang",
    "đông y gia truyền"
]

CONTEXT_DESCRIPTION = "Video quảng cáo thuốc, thực phẩm chức năng, cam kết trị bệnh, bán hàng online, đông y, mỹ phẩm"
MAX_LINKS_PER_KEYWORD = 3 
OUTPUT_FILE = 'input_links_tiktok.txt' 
SIMILARITY_THRESHOLD = 0.22 

# ================= HÀM XỬ LÝ =================

def clean_tiktok_text(raw_text):
    """Làm sạch text: xóa ký tự lạ và dấu | để không lỗi file save"""
    text = re.sub(r'(created by|with).*$', '', raw_text, flags=re.IGNORECASE)
    text = text.replace('\n', ' ').replace('|', ' ').strip()
    return text

def init_output_file():
    if os.path.exists(OUTPUT_FILE):
        print(f"⚠️ File '{OUTPUT_FILE}' đang có dữ liệu cũ.")
        choice = input("👉 Bạn có muốn xóa để quét mới không? (y/n): ").lower()
        if choice == 'y':
            open(OUTPUT_FILE, 'w').close()
            print("🗑️ Đã xóa dữ liệu cũ.")
        else:
            print("➥ Sẽ ghi nối tiếp vào file cũ.")

def get_tiktok_links_pro():
    print("⏳ Đang tải Model AI (SentenceTransformer)...")
    model = SentenceTransformer('keepitreal/vietnamese-sbert')
    target_embedding = model.encode(CONTEXT_DESCRIPTION, convert_to_tensor=True)
    print("✅ Model sẵn sàng!")

    co = ChromiumOptions()
    co.set_argument('--mute-audio')
    current_folder = os.path.dirname(os.path.abspath(__file__))
    co.set_user_data_path(os.path.join(current_folder, 'User_Data_TikTok'))
    
    page = ChromiumPage(co)
    
    try:
        for kw_index, keyword in enumerate(KEYWORDS_LIST):
            print(f"\n{'='*50}")
            print(f"🔍 TỪ KHÓA [{kw_index+1}/{len(KEYWORDS_LIST)}]: '{keyword.upper()}'")
            
            url = f"https://www.tiktok.com/search?q={keyword}"
            page.get(url)
            
            if "Login" in page.title:
                print("⚠️ CẦN ĐĂNG NHẬP THỦ CÔNG...")
                input("✅ Bấm Enter sau khi login xong...")
            else:
                time.sleep(3)

            found_links_count = 0
            found_urls_in_session = set()
            retry_scroll = 0
            
            while found_links_count < MAX_LINKS_PER_KEYWORD:
                video_elements = page.eles('tag:a@@href:video')
                
                for ele in video_elements:
                    link = ele.attr('href')
                    
                    if not link or "/video/" not in link or link in found_urls_in_session:
                        continue
                        
                    img_alt = ele.ele('tag:img').attr('alt') if ele.ele('tag:img') else ""
                    raw_text = f"{img_alt} {ele.text}".strip()
                    clean_text = clean_tiktok_text(raw_text)
                    
                    if len(clean_text) < 5: continue

                    should_save = False
                    detect_type = "UNKNOWN" # KW (Keyword) hoặc AI (Semantic)

                    # 1. Check cứng (Keyword có trong text) -> Ưu tiên cao nhất
                    if keyword.lower() in clean_text.lower():
                        print(f"   🔥 [TRÙNG TỪ KHÓA] {clean_text[:60]}...")
                        should_save = True
                        detect_type = "KW"
                    else:
                        # 2. Check mềm (AI tương đồng ngữ nghĩa)
                        cand_embedding = model.encode(clean_text, convert_to_tensor=True)
                        score = util.cos_sim(target_embedding, cand_embedding).item()
                        if score >= SIMILARITY_THRESHOLD:
                            print(f"   ✅ [AI: {score:.2f}] {clean_text[:60]}...")
                            should_save = True
                            detect_type = "AI"

                    if should_save:
                        # LƯU ĐỊNH DẠNG: LINK | LOẠI | TEXT_MÔ_TẢ
                        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                             f.write(f"{link}|{detect_type}|{clean_text}\n")
                        found_urls_in_session.add(link)
                        found_links_count += 1
                        
                    if found_links_count >= MAX_LINKS_PER_KEYWORD: break
                
                if found_links_count >= MAX_LINKS_PER_KEYWORD: break

                print(f"   🔄 Đang lấy: {found_links_count}/{MAX_LINKS_PER_KEYWORD}. Cuộn xuống...")
                prev_height = page.run_js('return document.body.scrollHeight')
                page.scroll.to_bottom()
                time.sleep(3)
                curr_height = page.run_js('return document.body.scrollHeight')
                
                if prev_height == curr_height:
                    retry_scroll += 1
                    if retry_scroll >= 3: 
                        print("   ⚠️ Hết trang hoặc bị chặn cuộn.")
                        break
                else:
                    retry_scroll = 0
            
            print(f"✅ Hoàn thành từ khóa '{keyword}'. Tìm được {found_links_count} link.")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        page.quit()
    
    print(f"\n🎉 XONG! Link đã được lưu vào '{OUTPUT_FILE}'")

if __name__ == "__main__":
    init_output_file()
    get_tiktok_links_pro()