import requests
from bs4 import BeautifulSoup
import csv
import json
import time

base_url = "https://fullfact.org/health/?page={}"
max_pages = 175   # change as needed
data = []

for page in range(1, max_pages + 1):
    url = base_url.format(page)
    print("Crawling:", url)

    r = requests.get(url)
    if r.status_code != 200:
        print("Stopped at page", page)
        break

    soup = BeautifulSoup(r.text, "html.parser")

    # Each article block
    cards = soup.select("div.card-text")

    for card in cards:

        # --------------------------
        # 1. Timestamp
        # --------------------------
        ts_el = card.select_one("div.timestamp")
        timestamp = ts_el.get_text(strip=True) if ts_el else ""

        # --------------------------
        # 2. Title (<h2>)
        # --------------------------
        title_el = card.select_one("h2")
        title = title_el.get_text(strip=True) if title_el else ""

        # --------------------------
        # 3. Excerpt (all <p>)
        # --------------------------
        paragraphs = card.select("p")
        excerpt = " ".join(p.get_text(strip=True) for p in paragraphs)

        # Save
        data.append({
            "timestamp": timestamp,
            "title": title,
            "excerpt": excerpt
        })

    time.sleep(0.5)

print("Total items:", len(data))



# -----------------------------------
# Save to JSON
# -----------------------------------
with open("fullfact_health.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Saved to fullfact_health.json")
