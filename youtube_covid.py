import os
import requests

BASE = "https://www.who.int/images/default-source/health-topics/coronavirus/myth-busters"
OUT = "who_mythbusters/images"
os.makedirs(OUT, exist_ok=True)

found = 0
for i in range(1, 200):
    url = f"{BASE}/mythbuster-{i}.png"
    r = requests.get(url, timeout=20)
    if r.status_code == 200:
        with open(f"{OUT}/myth_{i:03d}.png", "wb") as f:
            f.write(r.content)
        found += 1

print("Downloaded:", found)
