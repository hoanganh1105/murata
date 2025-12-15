import json
import csv

# 1. Load file JSON
with open("Khoa_crawl/youtube_shorts_vn_misinfo.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 2. Ghi ra CSV
with open("Khoa_crawl/youtube_shorts_vn_misinfo.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

print("Đã chuyển JSON → CSV thành công!")
