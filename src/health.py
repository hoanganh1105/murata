import requests
from bs4 import BeautifulSoup
import csv
import json
import time

base_url = "https://science.feedback.org/category/insights/"
param = "?_topic=health&_pagination={}"

max_pages = 5   # change if you want more
data = []

for page in range(1, max_pages + 1):
    url = base_url + param.format(page)
    print("Crawling:", url)

    r = requests.get(url)
    if r.status_code != 200:
        print("Error loading page:", r.status_code)
        break

    soup = BeautifulSoup(r.text, "html.parser")
    articles = soup.select("article.story")

    for art in articles:

        # ---------------------------
        # 1. TITLE
        # ---------------------------
        title_el = art.select_one("h2.story__title")
        title = title_el.get_text(strip=True) if title_el else ""

        # ---------------------------
        # 2. EXCERPT (all <p> inside story__excerpt)
        # ---------------------------
        excerpt_div = art.select_one("div.story__excerpt")
        if excerpt_div:
            excerpt = " ".join(
                p.get_text(strip=True) for p in excerpt_div.select("p")
            )
        else:
            excerpt = ""

        # ---------------------------
        # 3. POST TIME (text node after <span class="sr-only">)
        # ---------------------------
        post_span = art.select_one("span.story__posted-on")
        if post_span:
            # full text might look like: "Posted on: 2019-04-08"
            full_text = post_span.get_text(" ", strip=True)
            parts = full_text.split()

            # date is always the last word
            post_time = parts[-1] if parts else ""
        else:
            post_time = ""

        # ---------------------------
        # 4. Save this article
        # ---------------------------
        data.append({
            "title": title,
            "excerpt": excerpt,
            "post_time": post_time
        })

    time.sleep(0.5)   # be polite

print("Total articles:", len(data))


# -----------------------------------
# SAVE TO JSON
# -----------------------------------
with open("health_insights.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Saved: health_insights.json")
