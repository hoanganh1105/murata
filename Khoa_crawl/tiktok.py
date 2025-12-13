import subprocess
import json
import os
import glob
from datetime import datetime

KEYWORDS = [
    "ung thư chữa khỏi",
    "vẩy nến không tái phát",
    "cam kết khỏi bệnh",
    "vaccine covid 100%"
]

BASE_DIR = "yt_shorts_data"
OUTPUT_FILE = "youtube_shorts_vn_misinfo.json"

os.makedirs(BASE_DIR, exist_ok=True)

def crawl_keyword(keyword):
    safe_kw = keyword.replace(" ", "_")
    out_dir = os.path.join(BASE_DIR, safe_kw)
    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        "yt-dlp",
        f"ytsearch50:{keyword}",
        "--skip-download",
        "--write-info-json",
        "--no-warnings",
        "--match-filter", "duration < 60",
        "-o", f"{out_dir}/%(id)s.%(ext)s"
    ]

    subprocess.run(cmd, check=True)

dataset = []

# 🔥 Crawl
for kw in KEYWORDS:
    print(f"[+] Crawling keyword: {kw}")
    crawl_keyword(kw)

# 🔥 Parse metadata
for kw_dir in os.listdir(BASE_DIR):
    dir_path = os.path.join(BASE_DIR, kw_dir)
    if not os.path.isdir(dir_path):
        continue

    keyword = kw_dir.replace("_", " ")

    for info_file in glob.glob(f"{dir_path}/*.info.json"):
        with open(info_file, "r", encoding="utf-8") as f:
            info = json.load(f)

        upload_date = info.get("upload_date")
        if upload_date:
            upload_date = datetime.strptime(
                upload_date, "%Y%m%d"
            ).strftime("%Y-%m-%d")

        dataset.append({
            "platform": "youtube",
            "type": "shorts",
            "keyword": keyword,
            "video_id": info.get("id"),
            "title": info.get("title"),
            "description": info.get("description"),
            "upload_date": upload_date,
            "channel_name": info.get("channel"),
            "channel_id": info.get("channel_id"),
            "uploader_id": info.get("uploader_id"),
            "duration": info.get("duration"),
            "view_count": info.get("view_count"),
            "url": info.get("webpage_url"),
            "label": "medical_misinformation"
        })

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print("✅ DONE")
print("Total shorts:", len(dataset))
print("Saved to:", OUTPUT_FILE)
