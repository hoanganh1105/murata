import json

with open("yt_shorts_data/cam_kết_khỏi_bệnh/2d_m-lBQJLE.info.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("2d_m-lBQJLE.info_pretty.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)