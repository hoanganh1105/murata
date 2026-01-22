import yt_dlp
import os
import re

def clean_duplicated_text(text):
    """Thuật toán khử lặp cụm từ đặc trị cho sub YouTube"""
    # Xóa các khoảng trắng thừa và mã vị trí còn sót
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Tách thành các từ
    words = text.split()
    if not words: return ""

    final_text = []
    for word in words:
        # Nếu từ hiện tại chưa có hoặc không trùng với từ vừa thêm, thì mới thêm vào
        # Đây là bước lọc cơ bản cho các từ lặp sát nhau
        if not final_text or word != final_text[-1]:
            final_text.append(word)
    
    # Ghép lại thành chuỗi
    combined = " ".join(final_text)
    
    # Bước nâng cao: Khử lặp các cụm câu dài (ví dụ: "abc def abc def")
    # Sử dụng Regex để tìm các đoạn lặp lại liên tiếp
    # Cơ chế: Tìm một cụm (từ 3 từ trở lên) bị lặp lại ngay lập tức
    cleaned = re.sub(r'(.{15,})\1+', r'\1', combined)
    
    return cleaned

def get_sub_perfect(url):
    ydl_opts = {
        'skip_download': True,
        'writeautomaticsub': True,
        'writesubtitles': True,
        'sub_langs': ['en'],        # Lấy tiếng Anh theo ý bạn
        'cookiefile': 'www.youtube.com_cookies.txt', # Dùng file cookie đã chuẩn bị
        'outtmpl': 'temp_file',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("🚀 Đang tải phụ đề và xử lý lặp... Chờ chút...")
            ydl.download([url])

        # Tìm file vừa tải
        filename = ""
        for file in os.listdir('.'):
            if file.startswith("temp_file") and (file.endswith(".vtt") or file.endswith(".srt")):
                filename = file
                break

        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. Xóa mốc thời gian và các thẻ định dạng <c>, align, v.v.
            clean = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3} --> \d{2}:\d{2}:\d{2}[.,]\d{3}', '', content)
            clean = re.sub(r'<[^>]+>', '', clean)
            clean = re.sub(r'align:[\w%]+|position:[\w%]+|size:[\w%]+|line:[\w%]+', '', clean)
            clean = re.sub(r'WEBVTT|Kind:.*|Language:.*', '', clean)
            
            # 2. Đưa về 1 dòng
            clean = clean.replace('\n', ' ')
            
            # 3. Chạy thuật toán khử lặp mạnh
            final_result = clean_duplicated_text(clean)

            # Lưu file kết quả cuối cùng
            with open("youtube_short/ket_qua_sach.txt", "w", encoding="utf-8") as f:
                f.write(final_result)

            # Xóa file tạm
            os.remove(filename)
            
            print("\n✅ THÀNH CÔNG RỰC RỠ!")
            print("-" * 50)
            print(final_result[:500] + "...") # In thử 500 ký tự đầu
            print("-" * 50)
            print(f"👉 File sạch đã lưu tại: {os.path.abspath('ket_qua_sach.txt')}")
        else:
            print("❌ Không lấy được phụ đề. Hãy kiểm tra lại file cookies.txt")

    except Exception as e:
        print(f"❌ Lỗi: {e}")

# Link của bạn
link = "https://www.youtube.com/shorts/pLHICFatuVk"
get_sub_perfect(link)