import re

def filter_clean_reels(input_file, output_file):
    # Đọc file gốc
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Tìm tất cả các dãy số ID (thường là 15-16 chữ số) nằm sau /reels/ hoặc /reel/
    # Regex này sẽ bắt được cả: /reels/123... hoặc /reel/123...
    reel_ids = re.findall(r'/reel(?:s)?/(\[0-9\]+)', content)

    # Loại bỏ ID trùng lặp
    unique_ids = list(dict.fromkeys(reel_ids))

    # Tạo lại link theo định dạng bạn muốn
    clean_links = [f"https://m.facebook.com/reel/{rid}/" for rid in unique_ids]

    # Ghi ra file mới
    with open(output_file, 'w', encoding='utf-8') as f:
        for link in clean_links:
            f.write(link + '\n')

    print(f"✅ Đã lọc xong!")
    print(f"📊 Tìm thấy: {len(clean_links)} link Reel chuẩn.")

# Chạy lọc
filter_clean_reels('No related/links.txt', 'No related/links_clean.txt')